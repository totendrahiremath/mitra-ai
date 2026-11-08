import sys
import os
import re
import time
import tempfile
import threading
import warnings

# Suppress pyttsx3 comtypes FutureWarning on Python 3.15+
warnings.filterwarnings("ignore", category=FutureWarning, module="pyttsx3.*")

try:
    import pyaudio
except ModuleNotFoundError:
    import pyaudiowpatch as pyaudio
    sys.modules["pyaudio"] = pyaudio

import speech_recognition as sr

# Use Windows native SAPI.SpVoice for flawless, consecutive voice playback without skipping
_sapi_voice = None
_pyttsx3_engine = None
_speak_lock = threading.Lock()

def _ensure_com():
    """Ensures COM library is initialized on the calling thread for Windows."""
    if sys.platform == "win32":
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

def _get_sapi_voice():
    """Lazily retrieves or initializes SAPI.SpVoice with COM thread support."""
    global _sapi_voice
    if sys.platform != "win32":
        return None
    _ensure_com()
    if _sapi_voice is None:
        try:
            import win32com.client
            _sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
            _sapi_voice.Rate = 0     # Natural speaking pace (-10 to +10)
            _sapi_voice.Volume = 100 # Full volume (0 to 100)
        except Exception as e:
            print(f"[Voice Init Warning]: SAPI.SpVoice initialization failed: {e}")
    return _sapi_voice

def _init_tts():
    global _pyttsx3_engine
    if sys.platform == "win32":
        voice = _get_sapi_voice()
        if voice is not None:
            return

    try:
        import pyttsx3
        _pyttsx3_engine = pyttsx3.init()
        _pyttsx3_engine.setProperty('rate', 175)
        _pyttsx3_engine.setProperty('volume', 1.0)
    except Exception as e:
        print(f"[Voice Init Warning]: pyttsx3 initialization failed: {e}")

_init_tts()

# Language mode configuration: 'auto' (bilingual), 'kn' (Kannada), 'en' (English)
_language_mode = "auto"
_is_speaking = False
_stop_speech_flag = False

WAKE_WORDS = [
    # Aurvyn
    "hey aurvyn", "aurvyn", "ok aurvyn", "hello aurvyn", "hi aurvyn",
    "hey arvin", "arvin", "ok arvin", "hello arvin", "hi arvin",
    "hey orvin", "orvin", "ok orvin",
    # Mitra
    "hey mitra", "mitra", "ok mitra", "hello mitra", "hi mitra",
    "hey mithra", "mithra", "ok mithra", "hello mithra", "hi mithra",
    "hey meetra", "meetra", "ok meetra",
    # Kannada
    "ಹೇ ಮಿತ್ರ", "ಮಿತ್ರ", "ಹೇ ಆರ್ವಿನ್", "ಆರ್ವಿನ್"
]

# Shared speech recognition instances
_recognizer = sr.Recognizer()
# Configure recognizer so it does NOT cut off speech mid-sentence
_recognizer.pause_threshold = 2.0         # Seconds of silence before assuming speaker is done (prevents cutting off)
_recognizer.phrase_threshold = 0.3        # Minimum seconds of speaking audio to consider a phrase
_recognizer.non_speaking_duration = 0.8   # Audio padding retained before and after speech
_recognizer.dynamic_energy_threshold = True

_microphone = None
_ui_state_callback = None

def set_ui_callback(callback_fn):
    """Registers a callback function to update Siri UI animation state."""
    global _ui_state_callback
    _ui_state_callback = callback_fn

def _notify_ui(state: str):
    if _ui_state_callback:
        try:
            _ui_state_callback(state)
        except Exception:
            pass

def get_language_mode() -> str:
    """Returns current active language mode ('auto', 'kn', 'en')."""
    return _language_mode

def set_language_mode(mode: str):
    """Sets active language mode ('auto', 'kn', 'en')."""
    global _language_mode
    m = (mode or "").strip().lower()
    if m in ("auto", "kn", "en"):
        _language_mode = m
    else:
        _language_mode = "auto"
    print(f"[Engine]: Language mode switched to '{_language_mode}'")

def is_speaking() -> bool:
    """Returns True if speech output is currently active."""
    return _is_speaking

def interrupt_speech():
    """Immediately halts ongoing speech output and purges speech buffers."""
    global _stop_speech_flag, _is_speaking
    _stop_speech_flag = True
    _is_speaking = False

    _ensure_com()
    voice = _get_sapi_voice()
    if voice is not None:
        try:
            # SVSFPurgeBeforeSpeak (2) | SVSFlagsAsync (1) = 3
            voice.Speak("", 3)
        except Exception:
            pass

    if _pyttsx3_engine is not None:
        try:
            _pyttsx3_engine.stop()
        except Exception:
            pass

    _notify_ui("IDLE")

def get_microphone():
    """Returns or lazily creates a shared Microphone instance."""
    global _microphone
    if _microphone is None:
        try:
            _microphone = sr.Microphone()
        except Exception as e:
            print(f"[Mic Error]: Could not initialize microphone: {e}")
    return _microphone

def calibrate_mic():
    """Calibrates microphone for ambient room noise."""
    mic = get_microphone()
    if mic:
        try:
            with mic as source:
                print("[Aurvyn]: Calibrating microphone for ambient room noise...")
                _recognizer.adjust_for_ambient_noise(source, duration=1.0)
                print(f"[Aurvyn]: Microphone calibrated (Energy threshold: {int(_recognizer.energy_threshold)})")
        except Exception as e:
            print(f"[Mic Warning]: Ambient noise calibration skipped: {e}")

def _speak_kannada_gtts(text: str) -> bool:
    """Synthesizes and vocalizes Kannada text using gTTS and Windows Media Player."""
    global _stop_speech_flag
    try:
        from gtts import gTTS
        import win32com.client

        temp_path = os.path.join(tempfile.gettempdir(), f"aurvyn_tts_{os.getpid()}.mp3")
        tts = gTTS(text=text, lang="kn")
        tts.save(temp_path)

        if _stop_speech_flag:
            return True

        _ensure_com()
        player = win32com.client.Dispatch("WMPlayer.OCX")
        player.URL = temp_path
        player.controls.play()

        # Wait until playback finishes or interrupted
        while True:
            if _stop_speech_flag:
                try:
                    player.controls.stop()
                except Exception:
                    pass
                break
            state = player.playState
            # 1 = Stopped, 8 = MediaEnded
            if state in (1, 8):
                break
            time.sleep(0.05)

        try:
            player.close()
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[Kannada TTS Warning]: {e}")
        return False

def speak(text: str):
    """Prints response to the terminal and vocalizes aloud through speakers."""
    global _is_speaking, _stop_speech_flag
    if not text:
        return

    print(f"\n[Aurvyn]: {text}")
    _is_speaking = True
    _stop_speech_flag = False
    _notify_ui("SPEAKING")

    # Strip markdown symbols so speech engine pronounces words cleanly
    tts_text = re.sub(r'[*_~`#]', '', text)
    tts_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', tts_text).strip()
    if not tts_text:
        _is_speaking = False
        _notify_ui("IDLE")
        return

    _ensure_com()

    with _speak_lock:
        if _stop_speech_flag:
            _is_speaking = False
            _notify_ui("IDLE")
            return

        try:
            # Check if text contains Kannada Unicode characters
            if any('\u0c80' <= c <= '\u0cff' for c in tts_text):
                if _speak_kannada_gtts(tts_text):
                    return

            # 1. Native Windows SAPI voice (primary - guaranteed consecutive speech)
            voice = _get_sapi_voice()
            if voice is not None and not _stop_speech_flag:
                try:
                    voice.Speak(tts_text)
                    return
                except Exception as e:
                    # Retry with freshly initialized COM dispatch on this thread
                    try:
                        _ensure_com()
                        import win32com.client
                        retry_voice = win32com.client.Dispatch("SAPI.SpVoice")
                        retry_voice.Rate = 0
                        retry_voice.Volume = 100
                        if not _stop_speech_flag:
                            retry_voice.Speak(tts_text)
                            return
                    except Exception:
                        print(f"[SAPI Voice Error]: {e}")

            # 2. Pyttsx3 fallback
            if _pyttsx3_engine is not None and not _stop_speech_flag:
                try:
                    _pyttsx3_engine.say(tts_text)
                    _pyttsx3_engine.runAndWait()
                except Exception as e:
                    print(f"[pyttsx3 Error]: {e}")
        finally:
            _is_speaking = False
            _notify_ui("IDLE")

def clean_command(text: str) -> str:
    """Strips leading wake words and polite conversational filler."""
    if not text:
        return ""
    text_clean = text.strip()
    for w in WAKE_WORDS:
        text_clean = re.sub(rf"^\s*{re.escape(w)}[\s,.:;]*", "", text_clean, flags=re.IGNORECASE)
    text_clean = re.sub(r"^(?:please|can you|could you|would you|mitra|aurvyn|arvin|ದಯವಿಟ್ಟು)\s+", "", text_clean, flags=re.IGNORECASE)
    return text_clean.strip(" ,.?!:;\"\t\n\r")

def _get_recognition_languages() -> list[str]:
    """Returns prioritized speech recognition languages based on active mode."""
    if _language_mode == "kn":
        return ["kn-IN", "en-IN"]
    elif _language_mode == "en":
        return ["en-IN", "en-US"]
    else:
        return ["en-IN", "kn-IN", "en-US"]

def listen_voice_input() -> tuple[str, str]:
    """
    Listens for speech input from the microphone with generous pause tolerance
    so user commands are heard in full without mid-sentence cutoff.
    Returns:
        ("WAKE_WORD", "") if the user only said the trigger wake word ("Hey Mitra" / "Hey Aurvyn").
        ("COMMAND", query) if a command was spoken (standalone or after wake word).
        (None, "") if no speech was detected or audio timed out.
    """
    mic = get_microphone()
    if not mic:
        return None, ""

    try:
        with mic as source:
            _notify_ui("LISTENING")
            # timeout=5s waiting for speech to begin; phrase_time_limit=15s recording duration for full commands
            audio = _recognizer.listen(source, timeout=5, phrase_time_limit=15)

            _notify_ui("PROCESSING")

            # Recognize multi-accent according to language mode
            detected_text = ""
            for lang in _get_recognition_languages():
                try:
                    detected_text = _recognizer.recognize_google(audio, language=lang).lower().strip()
                    if detected_text:
                        break
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    break

            if not detected_text:
                _notify_ui("IDLE")
                return None, ""

            # Filter trivial noise / filler syllables
            if detected_text in {"a", "um", "uh", "the", "an", "oh"}:
                _notify_ui("IDLE")
                return None, ""

            print(f"\n[Heard]: '{detected_text}'")

            # 1. Check for wake words
            for word in WAKE_WORDS:
                if word in detected_text:
                    parts = re.split(rf"\b{re.escape(word)}\b", detected_text, maxsplit=1)
                    if len(parts) > 1 and parts[1].strip():
                        command = clean_command(parts[1])
                        if command:
                            return "COMMAND", command
                    return "WAKE_WORD", ""

            # 2. Direct spoken command without wake word (e.g. "open youtube", "can you hear me")
            cleaned = clean_command(detected_text)
            if cleaned:
                return "COMMAND", cleaned

    except (sr.WaitTimeoutError, sr.UnknownValueError):
        pass
    except sr.RequestError:
        pass
    except Exception:
        pass

    _notify_ui("IDLE")
    return None, ""

def listen_command() -> str:
    """Actively records speech after wake word activation and returns full text."""
    mic = get_microphone()
    if not mic:
        return ""

    with mic as source:
        print("\n[Aurvyn]: Listening for your command...")
        _notify_ui("LISTENING")
        try:
            # pause_threshold 2.0s and phrase_time_limit 15s to capture full query
            audio = _recognizer.listen(source, timeout=6, phrase_time_limit=15)
            print("[Aurvyn]: Processing audio...")
            _notify_ui("PROCESSING")

            query = ""
            for lang in _get_recognition_languages():
                try:
                    query = _recognizer.recognize_google(audio, language=lang)
                    if query:
                        break
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    break

            if not query:
                speak("Sorry, I could not understand the audio. Please try again.")
                return ""

            cleaned_query = clean_command(query)
            print(f"[User]: {cleaned_query}")
            return cleaned_query

        except sr.WaitTimeoutError:
            speak("I didn't catch anything. Going back to standby.")
            return ""
        except sr.RequestError:
            speak("Network error while connecting to speech recognition service.")
            return ""
        except Exception as e:
            print(f"[Speech Error]: {e}")
            return ""
        finally:
            _notify_ui("IDLE")

def listen_for_wake_word() -> bool:
    """Legacy compatibility helper."""
    mode, _ = listen_voice_input()
    return mode is not None

__all__ = [
    "speak",
    "listen_voice_input",
    "listen_command",
    "calibrate_mic",
    "set_ui_callback",
    "get_language_mode",
    "set_language_mode",
    "interrupt_speech",
    "is_speaking",
    "listen_for_wake_word",
    "clean_command",
    "WAKE_WORDS",
]
