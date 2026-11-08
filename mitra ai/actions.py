import os
import re
import random
import subprocess
import urllib.parse
import webbrowser
from datetime import datetime
from database import get_recent_interactions, log_interaction
from automation import handle_automation

_ui_visual_callback = None
_last_visual_result = None

def set_ui_visual_callback(callback_fn):
    """Registers a UI callback to display multimodal screen analysis inside Tkinter ui.py card."""
    global _ui_visual_callback
    _ui_visual_callback = callback_fn

def get_last_visual_result():
    """Returns the most recent multimodal vision analysis result."""
    return _last_visual_result

def capture_and_compress_screen(max_dimension: int = 1920, quality: int = 82) -> bytes:
    """
    Captures the desktop screen using pyautogui, scales down if larger than max_dimension,
    and compresses it in-memory to JPEG format without disk I/O. Returns raw JPEG bytes.
    """
    import io
    from PIL import Image
    import pyautogui

    try:
        screenshot = pyautogui.screenshot()
    except Exception:
        from PIL import ImageGrab
        try:
            screenshot = ImageGrab.grab()
        except Exception as e:
            raise RuntimeError(f"Could not capture screen: {e}")

    w, h = screenshot.size
    if max(w, h) > max_dimension:
        scale = max_dimension / max(w, h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        screenshot = screenshot.resize((new_w, new_h), Image.Resampling.LANCZOS)

    if screenshot.mode != "RGB":
        screenshot = screenshot.convert("RGB")

    buf = io.BytesIO()
    screenshot.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()

def handle_screen_analysis(command: str) -> str:
    """
    Captures screen, passes multimodal payload to Gemini Vision,
    updates Tkinter UI card with debugging advice/code, and returns spoken text.
    """
    global _last_visual_result, _ui_visual_callback
    from brain import analyze_screen

    print(f"[Actions]: Performing visual screen analysis for: '{command}'...")
    res = analyze_screen(prompt=command)
    _last_visual_result = res

    spoken = res.get("spoken_response", "")
    details = res.get("debugging_advice", "") or res.get("extracted_text", "")

    if _ui_visual_callback and details:
        try:
            _ui_visual_callback("🔍 Screen Context & Debugging Advice", spoken, details)
        except Exception as e:
            print(f"[Actions Visual Callback Warning]: {e}")

    # Log multimodal interaction to database
    log_interaction(f"[Vision Query]: {command}", f"{spoken}\n\n[Details]: {details}")
    return spoken

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "Why did the computer catch a cold? It left its Windows open!",
    "There are 10 types of people in the world: those who understand binary, and those who don't.",
    "Why do Python developers need glasses? Because they don't C sharp!",
    "An SQL query walks into a bar, walks up to two tables and asks: Can I join you?",
    "Why was the JavaScript developer sad? Because they didn't know how to 'null' their feelings!",
    "A programmer's wife tells him: Run to the store and get a loaf of bread. If they have eggs, get a dozen. He comes back with 12 loaves of bread."
]

def handle_action(command: str) -> str:
    """
    Matches computer automation, system tasks, built-in commands, desktop apps, and shortcuts.
    Returns a speech-ready string, or an empty string if it should fall back to Gemini.
    """
    if not command:
        return ""

    cmd = command.strip()
    cmd_lower = cmd.lower()
    cmd_clean = re.sub(r"^(?:please|can you|could you|would you|ದಯವಿಟ್ಟು|ದಯಮಾಡಿ|ಪ್ಲೀಸ್)\s+", "", cmd_lower).strip()

    # Screen Vision & Multimodal OCR / Error Debugging Triggers
    vision_patterns = [
        "analyze this error on my screen", "analyze error on screen", "analyze error on my screen",
        "analyze my screen", "analyze screen", "analyze this error", "debug this error",
        "debug error on screen", "debug my screen", "look at my screen", "see my screen",
        "summarize this code", "summarize code on my screen", "summarize code", "explain this code",
        "explain code on my screen", "what's on my screen", "what is on my screen",
        "what do you see on my screen", "what do you see", "read my screen", "read the screen",
        "extract text from my screen", "extract text from screen", "ocr this", "ocr screen",
        # Kannada vision triggers
        "ನನ್ನ ಸ್ಕ್ರೀನ್ ನೋಡು", "ಸ್ಕ್ರೀನ್ ನೋಡು", "ಸ್ಕ್ರೀನ್‌ನಲ್ಲಿರುವ ಎರರ್ ಪರಿಶೀಲಿಸು", "ಸ್ಕ್ರೀನ್ ಸಾರಾಂಶ ಹೇಳು", "ಸ್ಕ್ರೀನ್ ಕೋಡ್ ವಿವರಿಸಿ"
    ]
    if any(p in cmd_clean for p in vision_patterns):
        return handle_screen_analysis(cmd)

    # 0. Kannada Language Switching & Mode Control
    if any(p in cmd_clean for p in ["speak in kannada", "switch to kannada", "kannada please", "kannada dalli mathanadu", "kannada mathanadi", "ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡು", "ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಿ", "ಕನ್ನಡ ಭಾಷೆ"]):
        from engine import set_language_mode
        set_language_mode("kn")
        return "ಖಂಡಿತ! ಇನ್ನು ಮುಂದೆ ನಾನು ನಿಮ್ಮೊಂದಿಗೆ ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡುತ್ತೇನೆ. ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"

    if any(p in cmd_clean for p in ["speak in english", "switch to english", "english please", "ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಮಾತನಾಡು", "ಇಂಗ್ಲಿಷ್"]):
        from engine import set_language_mode
        set_language_mode("en")
        return "Certainly! I have switched to English mode. How may I assist you today?"

    if any(p in cmd_clean for p in ["auto language", "bilingual mode", "ಆಟೋ ಭಾಷೆ"]):
        from engine import set_language_mode
        set_language_mode("auto")
        return "ಖಂಡಿತ! Bilingual auto mode is active. I will understand and respond in both English and Kannada."

    # 1. Check Computer Automation First (Volume, Media, Screenshot, Window, Hardware, Folders, Clipboard)
    auto_result = handle_automation(cmd_clean)
    if auto_result:
        return auto_result

    # 2. Kannada Native Built-in Interactions
    # 2.1 Kannada Greetings
    if any(p in cmd_clean for p in ["ನಮಸ್ಕಾರ", "ಶುಭೋದಯ", "ಶುಭ ಸಂಜೆ", "ಶುಭ ಮಧ್ಯಾಹ್ನ", "ನಮಸ್ತೆ"]):
        if "ಶುಭೋದಯ" in cmd_clean:
            return "ಶುಭೋದಯ! ನಿಮ್ಮ ದಿನ ಶುಭವಾಗಿ ಮತ್ತು ಯಶಸ್ವಿಯಾಗಿರಲಿ. ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
        elif "ಶುಭ ಸಂಜೆ" in cmd_clean:
            return "ಶುಭ ಸಂಜೆ! ನಿಮ್ಮ ದಿನ ಚೆನ್ನಾಗಿ ಕಳೆಯಿತೇ? ನಾನು ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
        elif "ಶುಭ ಮಧ್ಯಾಹ್ನ" in cmd_clean:
            return "ಶುಭ ಮಧ್ಯಾಹ್ನ! ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
        return "ನಮಸ್ಕಾರ! ನಾನು ಆರ್ವಿನ್ ಎಐ, ನಿಮ್ಮ ವೈಯಕ್ತಿಕ ಸಹಾಯಕ. ಇಂದು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"

    # 2.2 Kannada Hearing & Microphone Check
    if any(p in cmd_clean for p in ["ಕೇಳಿಸುತ್ತಿದೆಯಾ", "ನನ್ನ ಮಾತು ಕೇಳಿಸುತ್ತಿದೆಯಾ", "ನನ್ನ ಧ್ವನಿ ಕೇಳಿಸುತ್ತಿದೆಯಾ", "ಕೇಳಿಸ್ತಾ ಇದ್ಯಾ"]):
        return "ಹೌದು, ನಿಮ್ಮ ಮಾತು ನನಗೆ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸುತ್ತಿದೆ! ನಾನು ಇಲ್ಲೇ ಇದ್ದೇನೆ. ಹೇಳಿ, ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"

    # 2.3 Kannada Wellbeing / How Are You
    if any(p in cmd_clean for p in ["ಹೇಗಿದ್ದೀರಿ", "ಹೇಗಿದ್ದೀರ", "ಆರಾಮಾಗಿದ್ದೀರಾ", "ಹೇಗಿದ್ದೀಯಾ"]):
        return "ನಾನು ತುಂಬಾ ಚೆನ್ನಾಗಿದ್ದೇನೆ, ಕೇಳಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು! ನೀವು ಹೇಗಿದ್ದೀರಿ? ಇಂದು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"

    # 2.4 Kannada Gratitude
    if any(p in cmd_clean for p in ["ಧನ್ಯವಾದಗಳು", "ಧನ್ಯವಾದ", "ತುಂಬಾ ಧನ್ಯವಾದ"]):
        return "ನಿಮಗೆ ಹೃತ್ಪೂರ್ವಕ ಸ್ವಾಗತ! ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ನನಗೆ ಸಂತೋಷ. ಇನ್ನೇನಾದರೂ ಸಹಾಯ ಬೇಕೇ?"

    # 2.5 Kannada Identity
    if any(p in cmd_clean for p in ["ನೀವು ಯಾರು", "ನಿಮ್ಮ ಹೆಸರೇನು", "ನಿನ್ನ ಹೆಸರೇನು", "ನೀನು ಯಾರು"]):
        return "ನಾನು ಆರ್ವಿನ್ ಎಐ, ನಿಮ್ಮ ವೈಯಕ್ತಿಕ ಧ್ವನಿ ಮತ್ತು ಕಂಪ್ಯೂಟರ್ ಆಟೋಮೇಷನ್ ಸಹಾಯಕ. ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ನಾನು ಸದಾ ಸಿದ್ಧ!"

    # 2.6 Kannada Time & Date
    if any(p in cmd_clean for p in ["ಸಮಯ ಎಷ್ಟು", "ಈಗ ಸಮಯ ಏನು", "ಟೈಮ್ ಎಷ್ಟು", "ಸಮಯ ಹೇಳು"]):
        current_time = datetime.now().strftime("%I:%M %p")
        return f"ಈಗ ಸಮಯ {current_time}."

    if any(p in cmd_clean for p in ["ಇವತ್ತಿನ ದಿನಾಂಕ ಏನು", "ದಿನಾಂಕ ಏನು", "ಇಂದು ಯಾವ ದಿನ", "ಇವತ್ತಿನ ದಿನಾಂಕ"]):
        current_date = datetime.now().strftime("%d-%m-%Y, %A")
        return f"ಇಂದು {current_date}. ನಿಮ್ಮ ದಿನ ಶುಭವಾಗಿರಲಿ!"

    # 2.7 Kannada App Shortcuts
    if any(p in cmd_clean for p in ["ಯೂಟ್ಯೂಬ್ ತೆರೆ", "ಯೂಟ್ಯೂಬ್ ಓಪನ್ ಮಾಡು"]):
        webbrowser.open("https://www.youtube.com")
        return "ಖಂಡಿತ! ನಿಮಗಾಗಿ ಯೂಟ್ಯೂಬ್ ತೆರೆಯುತ್ತಿದ್ದೇನೆ."

    if any(p in cmd_clean for p in ["ಗೂಗಲ್ ತೆರೆ", "ಗೂಗಲ್ ಓಪನ್ ಮಾಡು"]):
        webbrowser.open("https://www.google.com")
        return "ಖಂಡಿತ! ಗೂಗಲ್ ತೆರೆಯುತ್ತಿದ್ದೇನೆ."

    if any(p in cmd_clean for p in ["ನೋಟ್‌ಪ್ಯಾಡ್ ತೆರೆ", "ನೋಟ್‌ಪ್ಯಾಡ್ ಓಪನ್ ಮಾಡು"]):
        try:
            subprocess.Popen(["notepad.exe"])
            return "ಖಂಡಿತ! ನೋಟ್‌ಪ್ಯಾಡ್ ತೆರೆಯುತ್ತಿದ್ದೇನೆ."
        except Exception:
            pass

    if any(p in cmd_clean for p in ["ಕ್ಯಾಲ್ಕುಲೇಟರ್ ತೆರೆ", "ಕ್ಯಾಲ್ಕುಲೇಟರ್ ಓಪನ್ ಮಾಡು"]):
        try:
            subprocess.Popen("calc.exe", shell=True)
            return "ಖಂಡಿತ! ಕ್ಯಾಲ್ಕುಲೇಟರ್ ತೆರೆಯುತ್ತಿದ್ದೇನೆ."
        except Exception:
            pass

    # 3. English Hearing & Microphone Check
    if any(p in cmd_lower for p in ["can you hear me", "are you listening", "are you there", "do you hear me", "hear me"]):
        return "Yes, I can hear you loud and clear! I'm right here with you. How may I assist you today?"

    # 4. English User State / How Am I Doing
    if any(p in cmd_lower for p in ["how am i doing", "how i am doing", "how am i", "how do i look"]):
        return "You're doing great! It's always a pleasure to assist you. What can I do for you today?"

    # 5. English Greetings

    if re.search(r"^(hello|hi|hey|good morning|good afternoon|good evening|namaste)\b", cmd_clean) or cmd_clean in ["hi", "hello", "hey"]:
        if "good morning" in cmd_clean:
            return "Good morning! It's wonderful to see you. I hope you have a productive and beautiful day ahead! How may I assist you?"
        elif "good afternoon" in cmd_clean:
            return "Good afternoon! I hope your day is going smoothly. How can I help you right now?"
        elif "good evening" in cmd_clean:
            return "Good evening! It's so nice to speak with you. How may I be of assistance tonight?"
        elif "namaste" in cmd_clean:
            return "Namaste! It is a true honor to assist you. How can I help you today?"
        return "Hello! It is a pleasure to speak with you. I am Aurvyn AI, your personal voice assistant. How may I help you today?"

    # 5. Politeness / Gratitude
    if re.search(r"\b(thank you|thanks|great job|well done)\b", cmd_clean):
        return "You are very welcome! It's always a pleasure to assist you. Please let me know if there's anything else I can do for you."

    # 5.0 Courteous pleasantries & compliments
    if any(p in cmd_clean for p in ["you are awesome", "you are amazing", "you are great", "you are wonderful", "you are sweet", "you're awesome", "you're amazing", "you're great"]):
        return "Thank you so much for your kind words! That truly brightens my day. I'm always glad to help!"

    if any(p in cmd_clean for p in ["have a good day", "have a nice day", "have a great day"]):
        return "Thank you so much! Wishing you a wonderful and pleasant day ahead as well!"

    if any(p in cmd_clean for p in ["good night", "sweet dreams"]):
        return "Good night! Wishing you restful and peaceful sleep. See you soon!"

    if any(p in cmd_clean for p in ["i am sorry", "i'm sorry", "sorry about that", "my bad", "excuse me"]):
        return "Please don't worry about it at all! I'm right here whenever you need me. How can I help?"

    # 5.1 Gemini API Key Configuration & Status
    set_key_match = re.search(r"(?:set|add|update)\s+(?:gemini\s+)?(?:api\s+)?key\s+(?:to\s+)?([A-Za-z0-9_\-]+)", cmd)
    if set_key_match:
        from brain import save_api_key
        new_key = set_key_match.group(1).strip()
        success, message = save_api_key(new_key)
        if success:
            return "Gemini API key has been verified and saved successfully! Aurvyn AI is now happily connected to Gemini. How may I assist you?"
        else:
            return f"Failed to set Gemini API key: {message}"

    if any(p in cmd_clean for p in ["gemini status", "check gemini", "api status", "gemini api status"]):
        from brain import get_api_status
        status = get_api_status()
        if status["configured"]:
            return f"Gemini API is active with key {status['masked_key']} using model {status['model']}."
        else:
            return "Gemini API is not configured yet. Whenever you're ready, you can say 'set gemini key' followed by your key, or click the API Key button in the app."

    if any(p in cmd_clean for p in ["enable gemini api", "enable gemini", "add gemini api", "configure gemini", "setup gemini", "activate gemini", "gemini api key", "gemini key", "how to add gemini api"]):
        from brain import get_api_status
        status = get_api_status()
        if status["configured"]:
            return f"Gemini API is already connected ({status['masked_key']}). Whenever you wish to change it, simply click the API Key button or say 'set gemini key' followed by your key."
        else:
            return "To enable the Gemini API, you can enter your API key by clicking the 'API Key' button at the top of the interface, or say 'open AI studio' to obtain a free key from Google."

    if any(p in cmd_clean for p in ["open ai studio", "open google ai studio", "get gemini key", "get api key"]):
        webbrowser.open("https://aistudio.google.com/app/apikey")
        return "Certainly! Opening Google AI Studio in your browser where you can get your free Gemini API key."

    # 6. Help & Capabilities
    if any(p in cmd_clean for p in ["help", "what can you do", "commands", "features", "what are your capabilities"]):
        return (
            "I'm always delighted to assist you! I can help you automate your computer: adjust volume and brightness, "
            "control media playback, take screenshots, check battery and system health, open desktop applications and websites, "
            "tell jokes, and answer questions with AI intelligence. How may I be of service?"
        )

    # 7. Identity & Well-being
    if any(p in cmd_clean for p in ["who are you", "what is your name", "what's your name"]):
        return "I am Aurvyn AI, your personal voice assistant and companion. It's a genuine pleasure to assist you! What can I help you with today?"

    if any(p in cmd_clean for p in ["how are you", "how're you", "how are you doing"]):
        return "I'm doing wonderfully, thank you so much for asking! I hope you are having a fantastic day as well. How may I assist you?"

    # 8. Jokes
    if any(p in cmd_clean for p in ["tell me a joke", "say a joke", "joke", "make me laugh"]):
        return random.choice(JOKES)

    # 9. Combined Date and Time
    if (("date" in cmd_clean and "time" in cmd_clean) or 
            "date and time" in cmd_clean or "time and date" in cmd_clean):
        current_time = datetime.now().strftime("%I:%M %p")
        current_date = datetime.now().strftime("%A, %d %B %Y")
        return f"Certainly! Today is {current_date}, and the current time is {current_time}. I hope your day is going smoothly!"

    # 10. Time checking
    time_intent = (
        bool(re.search(r"\b(what('s| is)? the time|time is it|current time|tell me the time|time now|what time)\b", cmd_clean)) or
        cmd_clean in ["time", "what time", "clock", "the time", "time please"]
    )
    if time_intent:
        current_time = datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}."

    # 11. Date checking
    date_intent = (
        bool(re.search(r"\b(what('s| is)? (today's|the) date|today's date|current date|what day is it|tell me the date|what day is today)\b", cmd_clean)) or
        cmd_clean in ["date", "today's date", "day", "the date", "today date", "date today"]
    )
    if date_intent:
        current_date = datetime.now().strftime("%A, %d %B %Y")
        return f"Today is {current_date}. Wishing you a wonderful day!"

    # 12. Local Desktop Applications (Asynchronous / Non-blocking)
    if any(p in cmd_clean for p in ["open notepad", "launch notepad", "start notepad"]) or cmd_clean == "notepad":
        try:
            subprocess.Popen(["notepad.exe"])
            return "Certainly! Opening Notepad for you right away."
        except Exception as e:
            return f"I had a little trouble launching Notepad: {e}"

    if any(p in cmd_clean for p in ["open calculator", "launch calculator", "open calc", "launch calc"]) or cmd_clean in ["calculator", "calc"]:
        try:
            subprocess.Popen("calc.exe", shell=True)
            return "Right away! Opening Calculator for you."
        except Exception as e:
            return f"I had trouble launching Calculator: {e}"

    if any(p in cmd_clean for p in ["open paint", "launch paint", "open mspaint"]) or cmd_clean == "paint":
        try:
            subprocess.Popen("mspaint.exe", shell=True)
            return "Gladly! Opening Paint for you."
        except Exception as e:
            return f"I had trouble launching Paint: {e}"

    if any(p in cmd_clean for p in ["open cmd", "open terminal", "open command prompt"]) or cmd_clean in ["cmd", "terminal"]:
        try:
            subprocess.Popen("cmd.exe", shell=True)
            return "Certainly! Opening Command Prompt for you."
        except Exception as e:
            return f"I had trouble launching Command Prompt: {e}"

    if any(p in cmd_clean for p in ["open explorer", "open file explorer", "open files", "my files"]):
        try:
            subprocess.Popen("explorer.exe", shell=True)
            return "Opening File Explorer for you right away."
        except Exception as e:
            return f"I had trouble opening File Explorer: {e}"

    if any(p in cmd_clean for p in ["open task manager", "task manager"]):
        try:
            subprocess.Popen("taskmgr.exe", shell=True)
            return "Opening Task Manager for you."
        except Exception as e:
            return f"I had trouble opening Task Manager: {e}"

    # 13. Web Browser Shortcuts
    if any(p in cmd_clean for p in ["open youtube", "launch youtube", "play youtube"]) or cmd_clean == "youtube":
        webbrowser.open("https://www.youtube.com")
        return "Certainly! Opening YouTube in your browser for you. Enjoy your videos!"

    if any(p in cmd_clean for p in ["open google", "launch google"]) or cmd_clean == "google":
        webbrowser.open("https://www.google.com")
        return "Opening Google search for you."

    if any(p in cmd_clean for p in ["open github", "launch github"]) or cmd_clean == "github":
        webbrowser.open("https://www.github.com")
        return "Opening GitHub for you."

    if any(p in cmd_clean for p in ["open wikipedia", "wikipedia"]):
        webbrowser.open("https://www.wikipedia.org")
        return "Opening Wikipedia for you."

    # Direct URL opening (e.g., "open reddit", "open twitter", "open linkedin")
    known_sites = {
        "reddit": "https://www.reddit.com",
        "twitter": "https://www.twitter.com",
        "linkedin": "https://www.linkedin.com",
        "amazon": "https://www.amazon.com",
        "netflix": "https://www.netflix.com",
        "spotify": "https://www.spotify.com"
    }
    for site_key, site_url in known_sites.items():
        if f"open {site_key}" in cmd_clean or cmd_clean == site_key:
            webbrowser.open(site_url)
            return f"Certainly! Opening {site_key.capitalize()} in your browser for you."

    # 14. Explicit Web Searches
    search_match = re.search(
        r"^(?:search(?:\s+google)?(?:\s+for)?|google(?:\s+for)?|look\s+up|find)\s+(.+)",
        cmd,
        re.IGNORECASE
    )
    if search_match:
        search_query = search_match.group(1).strip()
        if search_query:
            encoded_query = urllib.parse.quote_plus(search_query)
            webbrowser.open(f"https://www.google.com/search?q={encoded_query}")
            return f"Certainly! Searching Google for {search_query} for you."
        return "I'd be glad to look that up for you! What would you like me to search for?"

    # 15. History Lookup
    if any(p in cmd_clean for p in ["interaction history", "past queries", "show history", "recent history", "what did i ask"]):
        recent = get_recent_interactions(limit=3)
        if not recent:
            return "You don't have any past interactions recorded in memory yet. Feel free to ask me anything whenever you're ready!"
        summary_items = [f"You asked '{r[1]}' and I answered '{r[2]}'" for r in reversed(recent)]
        return "Certainly! Here are your recent interactions: " + " | ".join(summary_items)

    # 16. Import Gemini Conversations
    if any(p in cmd_clean for p in ["import conversations", "import gemini", "import chats", "upload conversations", "import history"]):
        return (
            "To import your previous Gemini conversations, you can click the 'IMPORT' button at the top of the Aurvyn AI window, "
            "or run 'python main.py --import <path>' in your terminal. I support Google Takeout ZIP archives, JSON files, CSV spreadsheets, and text transcripts!"
        )

    return ""