import os
import re
import urllib.parse
import webbrowser
from google import genai
from google.genai import types

_client = None

SYSTEM_INSTRUCTION = """
You are Aurvyn AI (also known as Mitra AI), a fast, friendly, helpful, and concise personal AI assistant.
Provide conversational, direct answers suitable for text-to-speech.
Keep standard answers within 2 to 4 sentences. Avoid Markdown bullet points, asterisks,
or symbols that sound awkward when vocalized by a speech synthesizer.
"""

def _load_env_file():
    """Loads environment variables from .env file if present in the project directory."""
    candidate_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    for env_path in candidate_paths:
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip("'\"")
                            if key and key not in os.environ:
                                os.environ[key] = val
                break
            except Exception as e:
                print(f"[Brain Env Warning]: Failed to read {env_path}: {e}")

_load_env_file()

def clean_for_speech(text: str) -> str:
    """Removes markdown symbols like asterisks, hashes, and bullets for clean TTS vocalization."""
    if not text:
        return ""
    # Remove markdown bold/italic asterisks and underscores
    text = re.sub(r'[*_~`#]', '', text)
    # Remove markdown bullet list prefixes
    text = re.sub(r'^\s*[-+]\s+', '', text, flags=re.MULTILINE)
    # Collapse multiple spaces and linebreaks into clean conversational speech
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _get_generation_model() -> str:
    """Returns a model compatible with generate_content for standard queries."""
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-native-audio-latest")
    # Native audio dialog models are dedicated to WebSocket live streaming (Gemini Live)
    if any(k in model_name.lower() for k in ["native-audio", "live"]):
        return os.getenv("GEMINI_CONTENT_MODEL", "gemini-3.5-flash")
    return model_name

def get_api_status() -> dict:
    """Returns the current status of the Gemini API configuration."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-native-audio-latest")
    if api_key:
        masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) >= 8 else "****"
        return {
            "configured": True,
            "masked_key": masked,
            "model": model_name
        }
    return {
        "configured": False,
        "masked_key": "None",
        "model": model_name
    }

def save_api_key(api_key: str) -> tuple[bool, str]:
    """Tests the provided Gemini API key and persists it to .env if valid."""
    global _client
    api_key = api_key.strip()
    if not api_key:
        return False, "API key cannot be empty."

    test_client = genai.Client(api_key=api_key)
    test_model = _get_generation_model()
    try:
        test_client.models.generate_content(
            model=test_model,
            contents="ping",
            config=types.GenerateContentConfig(max_output_tokens=5)
        )
    except Exception as e:
        # Fallback test with gemini-3.5-flash
        try:
            test_client.models.generate_content(
                model="gemini-3.5-flash",
                contents="ping",
                config=types.GenerateContentConfig(max_output_tokens=5)
            )
        except Exception as e2:
            return False, f"Verification failed: {e2}"

    # Persist to .env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    lines = []
    key_written = False
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        lines.append(f"GEMINI_API_KEY={api_key}\n")
                        key_written = True
                    else:
                        lines.append(line)
        except Exception:
            pass

    if not key_written:
        lines.append(f"GEMINI_API_KEY={api_key}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        return False, f"Key verified but failed to write .env: {e}"

    os.environ["GEMINI_API_KEY"] = api_key
    _client = test_client
    return True, "Gemini API key verified and saved successfully."

def ask_mitra(prompt: str) -> str:
    """Sends prompt to Gemini, or provides an active Google search fallback if API key is not configured."""
    global _client
    api_key = os.getenv("GEMINI_API_KEY")

    # If Gemini API key is not configured
    if not api_key:
        prompt_lower = prompt.lower()
        # Prevent operational computer commands from accidentally triggering a web search
        operational_words = ["volume", "sound", "mute", "unmute", "brightness", "window", "screenshot", "battery", "cpu", "ram"]
        if any(w in prompt_lower for w in operational_words):
            return "I couldn't execute that system command. You can say 'set volume to 50%', 'volume up', 'take a screenshot', or 'help'."

        # For informational questions, provide an active browser search fallback so the user gets their answer
        encoded = urllib.parse.quote_plus(prompt)
        webbrowser.open(f"https://www.google.com/search?q={encoded}")
        return f"I opened a Google search for '{prompt}' in your browser. To enable direct voice answers, add your Gemini API key to the .env file."

    model_name = _get_generation_model()

    try:
        if _client is None:
            _client = genai.Client(api_key=api_key)

        max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", "400"))

        response = _client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
                max_output_tokens=max_tokens
            )
        )
        if response and response.text:
            return clean_for_speech(response.text)
        return "I received an empty response from my intelligence engine."

    except Exception as e:
        err_str = str(e)
        print(f"[Brain Error]: {err_str}")

        # Fallback to secondary flash model if model is unavailable or not found
        if "not found" in err_str.lower() and model_name != "gemini-3.5-flash":
            try:
                print("[Brain]: Retrying with fallback model gemini-3.5-flash...")
                max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", "400"))
                fallback_response = _client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.7,
                        max_output_tokens=max_tokens
                    )
                )
                if fallback_response and fallback_response.text:
                    return clean_for_speech(fallback_response.text)
            except Exception as fb_err:
                print(f"[Brain Fallback Error]: {fb_err}")

        # If network error or model issue, search Google as fallback for general queries
        encoded = urllib.parse.quote_plus(prompt)
        webbrowser.open(f"https://www.google.com/search?q={encoded}")
        return f"I had trouble contacting the Gemini API, so I opened a Google search for '{prompt}' instead."

def ask_aurvyn(prompt: str) -> str:
    """Primary query function for Aurvyn AI (alias for ask_mitra)."""
    return ask_mitra(prompt)

def analyze_screen(prompt: str = "") -> dict:
    """Captures desktop screen and analyzes it with Gemini Multimodal Vision."""
    global _client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "spoken_response": "Gemini API key is required for screen analysis. Please configure your API key first.",
            "debugging_advice": "No Gemini API key found. Please set your key using the 'API KEY' button or in your .env file.",
            "extracted_text": ""
        }

    try:
        import pyautogui
        screen_img = pyautogui.screenshot()
    except Exception as e:
        return {
            "spoken_response": f"I couldn't capture the screen: {e}",
            "debugging_advice": "",
            "extracted_text": ""
        }

    user_query = prompt.strip() if prompt else "Analyze the active screen, identify any visible errors or code, and explain what you see."
    vision_prompt = f"""
You are analyzing a screenshot taken directly from the user's active screen.
User command / question: "{user_query}"

Provide your answer in this exact structured format:
SPOKEN_SUMMARY: A short, clear 1 to 3 sentence conversational summary suitable to be spoken aloud.
DETAILS: Detailed technical debugging steps, code explanations, or error resolution if relevant.
EXTRACTED_TEXT: Any key code snippet or error text shown on the screen.
"""
    model_name = _get_generation_model()
    try:
        if _client is None:
            _client = genai.Client(api_key=api_key)

        response = _client.models.generate_content(
            model=model_name,
            contents=[screen_img, vision_prompt],
        )
        raw_text = response.text if response and response.text else ""

        spoken = ""
        details = ""
        extracted = ""

        if "SPOKEN_SUMMARY:" in raw_text:
            parts = raw_text.split("SPOKEN_SUMMARY:")
            rest = parts[1]
            if "DETAILS:" in rest:
                s_part, d_part = rest.split("DETAILS:", 1)
                spoken = clean_for_speech(s_part)
                if "EXTRACTED_TEXT:" in d_part:
                    details, extracted = d_part.split("EXTRACTED_TEXT:", 1)
                else:
                    details = d_part
            else:
                spoken = clean_for_speech(rest)
        else:
            spoken = clean_for_speech(raw_text)
            details = raw_text

        return {
            "spoken_response": spoken.strip() or "I analyzed your screen.",
            "debugging_advice": details.strip(),
            "extracted_text": extracted.strip()
        }
    except Exception as e:
        err = str(e)
        print(f"[Screen Analysis Error]: {err}")
        return {
            "spoken_response": f"I encountered an error analyzing your screen: {err}",
            "debugging_advice": f"Screen analysis failed with error: {err}",
            "extracted_text": ""
        }

__all__ = [
    "ask_mitra",
    "ask_aurvyn",
    "clean_for_speech",
    "get_api_status",
    "save_api_key",
    "analyze_screen",
    "_load_env_file",
]
