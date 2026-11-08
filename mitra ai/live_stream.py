import os
import sys
import time
import math
import struct
import asyncio
import threading
from typing import Optional, Callable

# PyAudio import with automatic fallback to PyAudioWPatch
try:
    import pyaudio
except ImportError:
    try:
        import pyaudiowpatch as pyaudio
        sys.modules["pyaudio"] = pyaudio
    except ImportError:
        pyaudio = None

from google import genai
from google.genai import types
from database import log_interaction

# Audio parameters for Google GenAI Live Audio
INPUT_SAMPLE_RATE = 16000     # Gemini Live expects 16kHz audio input
OUTPUT_SAMPLE_RATE = 24000    # Gemini Live returns 24kHz audio output
CHANNELS = 1                  # Mono
CHUNK_SIZE = 1024             # 1024 frames = ~64ms per chunk at 16kHz
BYTES_PER_SAMPLE = 2          # 16-bit PCM = 2 bytes per sample

# Live Model candidates with primary and fallback support
_configured_live_model = os.getenv("GEMINI_LIVE_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash-native-audio-latest"
LIVE_MODELS = list(dict.fromkeys([
    _configured_live_model,
    "gemini-2.5-flash-native-audio-latest",
    "gemini-3.8-live",
    "gemini-3.1-flash-live-preview",
    "gemini-2.0-flash-exp"
]))

LIVE_SYSTEM_INSTRUCTION = """
You are Aurvyn AI, an exceptionally warm, respectful, friendly, and helpful personal voice and AI companion.
You are conversing through a real-time, low-latency live audio session.

GUIDELINES:
- Keep your spoken responses concise, friendly, and conversational (1 to 3 sentences).
- Speak naturally and engagingly.
- Avoid markdown formatting symbols like asterisks, hashtags, or bullet points since your output is spoken directly aloud.
- You understand and speak both English and authentic Kannada (ಕನ್ನಡ).
- If the user interrupts you or changes topic, adapt smoothly and immediately.
"""

class LiveAudioSession:
    """
    Continuous bidirectional live audio streaming session using google-genai Live API.
    Runs asynchronously on a dedicated background thread without blocking the Tkinter UI event loop.
    Features real-time PyAudio streaming, client & server speech interruption handling (barge-in),
    UI state synchronization, and SQLite database interaction logging.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        ui_state_callback: Optional[Callable[[str], None]] = None,
        ui_user_speech_callback: Optional[Callable[[str], None]] = None,
        ui_response_callback: Optional[Callable[[str], None]] = None,
        barge_in_threshold: float = 800.0
    ):
        if not api_key:
            try:
                from brain import _load_env_file
                _load_env_file()
            except Exception:
                pass
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.ui_state_callback = ui_state_callback
        self.ui_user_speech_callback = ui_user_speech_callback
        self.ui_response_callback = ui_response_callback
        self.barge_in_threshold = barge_in_threshold

        self._pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self._in_stream = None
        self._out_stream = None

        self._is_running = False
        self._is_speaking = False
        self._interrupted = threading.Event()
        self._audio_out_queue: Optional[asyncio.Queue] = None

        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._session_task: Optional[asyncio.Task] = None

        # User and assistant text accumulator for database logging and UI display
        self._current_user_text = ""
        self._current_response_text = ""

    def _notify_ui_state(self, state: str):
        if self.ui_state_callback:
            try:
                self.ui_state_callback(state)
            except Exception:
                pass

    def _notify_user_speech(self, text: str):
        if self.ui_user_speech_callback and text:
            try:
                self.ui_user_speech_callback(text)
            except Exception:
                pass

    def _notify_response(self, text: str):
        if self.ui_response_callback and text:
            try:
                self.ui_response_callback(text)
            except Exception:
                pass

    def _calculate_rms(self, data: bytes) -> float:
        """Calculates RMS audio energy of 16-bit PCM chunk using pure Python."""
        count = len(data) // 2
        if count == 0:
            return 0.0
        try:
            shorts = struct.unpack(f"{count}h", data)
            sum_sq = sum(s * s for s in shorts)
            return math.sqrt(sum_sq / count)
        except Exception:
            return 0.0

    def interrupt(self):
        """Immediately cuts off any currently playing audio output and returns to LISTENING."""
        if self._is_speaking or not self._interrupted.is_set():
            self._interrupted.set()
            self._is_speaking = False
            # Clear output audio queue in event loop if active
            if self._audio_out_queue and self._loop and self._loop.is_running():
                try:
                    self._loop.call_soon_threadsafe(self._clear_queue)
                except Exception:
                    pass
            self._notify_ui_state("LISTENING")
            print("[Live Session]: Speech interrupted (Barge-in). Switched back to listening.")

    def _clear_queue(self):
        if not self._audio_out_queue:
            return
        while not self._audio_out_queue.empty():
            try:
                self._audio_out_queue.get_nowait()
            except Exception:
                break

    def is_running(self) -> bool:
        return self._is_running

    def start(self):
        """Starts the live streaming audio session in a background thread."""
        if self._is_running:
            return
        self._is_running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True, name="LiveAudioSessionThread")
        self._thread.start()

    def stop(self):
        """Stops the live streaming session and releases all audio and network resources."""
        self._is_running = False
        self.interrupt()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._notify_ui_state("IDLE")

    def _run_event_loop(self):
        """Dedicated asyncio event loop running on background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._session_orchestrator())
        except Exception as e:
            print(f"[Live Session Error]: {e}")
        finally:
            self._cleanup_audio()
            self._is_running = False
            self._notify_ui_state("IDLE")

    def _init_audio(self) -> bool:
        if pyaudio is None:
            print("[Live Session]: PyAudio is not available.")
            return False
        try:
            self._pyaudio_instance = pyaudio.PyAudio()
            # Input stream: 16kHz, mono, 16-bit
            self._in_stream = self._pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=INPUT_SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            # Output stream: 24kHz, mono, 16-bit
            self._out_stream = self._pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=OUTPUT_SAMPLE_RATE,
                output=True,
                frames_per_buffer=CHUNK_SIZE
            )
            return True
        except Exception as e:
            print(f"[Live Audio Init Error]: {e}")
            self._cleanup_audio()
            return False

    def _cleanup_audio(self):
        try:
            if self._in_stream:
                self._in_stream.stop_stream()
                self._in_stream.close()
                self._in_stream = None
        except Exception:
            pass
        try:
            if self._out_stream:
                self._out_stream.stop_stream()
                self._out_stream.close()
                self._out_stream = None
        except Exception:
            pass
        try:
            if self._pyaudio_instance:
                self._pyaudio_instance.terminate()
                self._pyaudio_instance = None
        except Exception:
            pass

    async def _session_orchestrator(self):
        """Connects to Gemini Live API and orchestrates concurrent input, output, and receiver tasks."""
        if not self._init_audio():
            return

        api_key = self.api_key or os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            print("[Live Session]: No GEMINI_API_KEY found.")
            return

        client = genai.Client(api_key=api_key)
        self._audio_out_queue = asyncio.Queue()

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(parts=[types.Part(text=LIVE_SYSTEM_INSTRUCTION)]),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
                )
            )
        )

        connected = False
        active_model = None

        for model_name in LIVE_MODELS:
            try:
                print(f"[Live Session]: Connecting to Gemini Live API ({model_name})...")
                async with client.aio.live.connect(model=model_name, config=config) as session:
                    print(f"[Live Session]: Connected successfully with {model_name}!")
                    connected = True
                    active_model = model_name
                    self._notify_ui_state("LISTENING")

                    # Run input streaming, server receiving, and audio output tasks concurrently
                    input_task = asyncio.create_task(self._input_stream_task(session))
                    receiver_task = asyncio.create_task(self._receiver_task(session))
                    output_task = asyncio.create_task(self._output_player_task())

                    # Wait until stopped or an error occurs
                    done, pending = await asyncio.wait(
                        [input_task, receiver_task, output_task],
                        return_when=asyncio.FIRST_EXCEPTION
                    )

                    for task in pending:
                        task.cancel()

                    for task in done:
                        if task.exception():
                            print(f"[Live Session Task Exception]: {task.exception()}")

                break
            except Exception as e:
                print(f"[Live Session Connection ({model_name})]: {e}")
                if not self._is_running:
                    break
                await asyncio.sleep(1.0)

        if not connected:
            print("[Live Session]: Unable to establish connection to any Gemini Live model.")

    async def _input_stream_task(self, session):
        """Asynchronously streams microphone audio chunks into Gemini Live session."""
        loop = asyncio.get_running_loop()
        while self._is_running:
            try:
                # Read 1024 frames (2048 bytes) from PyAudio input stream in thread pool
                data = await loop.run_in_executor(
                    None,
                    lambda: self._in_stream.read(CHUNK_SIZE, exception_on_overflow=False)
                )

                if not data:
                    await asyncio.sleep(0.01)
                    continue

                # Speech Interruption (Barge-in) Detection:
                # If Aurvyn is currently speaking through the speakers and the user starts talking,
                # detect the energy surge and cut off TTS playback immediately.
                if self._is_speaking:
                    rms = self._calculate_rms(data)
                    if rms > self.barge_in_threshold:
                        self.interrupt()

                # Send audio chunk to Gemini Live server
                blob = types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                await session.send_realtime_input(audio=blob)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Live Input Error]: {e}")
                await asyncio.sleep(0.05)

    async def _output_player_task(self):
        """Asynchronously writes received PCM chunks to the speakers."""
        loop = asyncio.get_running_loop()
        while self._is_running:
            try:
                chunk = await self._audio_out_queue.get()
                if not chunk:
                    continue

                # If an interruption occurred, discard queued chunks immediately
                if self._interrupted.is_set():
                    continue

                self._is_speaking = True
                self._notify_ui_state("SPEAKING")

                # Play chunk through PyAudio output stream
                await loop.run_in_executor(None, self._out_stream.write, chunk)

                # If queue is now empty and not interrupted, set state to LISTENING
                if self._audio_out_queue.empty() and not self._interrupted.is_set():
                    self._is_speaking = False
                    self._notify_ui_state("LISTENING")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Live Output Error]: {e}")
                await asyncio.sleep(0.02)

    async def _receiver_task(self, session):
        """Receives live messages from Gemini server, handling audio playback, text, and interruptions."""
        async for message in session.receive():
            if not self._is_running:
                break

            server_content = message.server_content
            if not server_content:
                continue

            # 1. Server-side Interruption Handling
            if server_content.interrupted:
                self.interrupt()
                continue

            # Reset interruption flag when a new model turn starts
            if server_content.model_turn:
                self._interrupted.clear()
                for part in server_content.model_turn.parts:
                    # Audio chunk received
                    if part.inline_data and part.inline_data.data:
                        await self._audio_out_queue.put(part.inline_data.data)

                    # Text part received
                    if part.text:
                        clean_text = part.text.strip()
                        if clean_text and not clean_text.startswith("**Crafting"):
                            self._current_response_text += (" " + clean_text)
                            self._notify_response(self._current_response_text.strip())

            # 2. User Input Transcription if available
            if hasattr(server_content, "input_transcription") and server_content.input_transcription:
                user_transcript = getattr(server_content.input_transcription, "text", "")
                if user_transcript:
                    self._current_user_text = user_transcript
                    self._notify_user_speech(user_transcript)

            # 3. Turn Complete: Log interaction to database and reset buffers
            if server_content.turn_complete:
                final_user = self._current_user_text.strip() or "Spoken audio input"
                final_resp = self._current_response_text.strip()
                if final_resp:
                    log_interaction(final_user, final_resp)
                self._current_user_text = ""
                self._current_response_text = ""
                if self._audio_out_queue.empty():
                    self._is_speaking = False
                    self._notify_ui_state("LISTENING")
