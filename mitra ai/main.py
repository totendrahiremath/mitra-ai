import sys
import time
import argparse
import threading
import winsound
from database import init_db, log_interaction
from engine import (
    speak,
    listen_voice_input,
    listen_command,
    calibrate_mic,
    set_ui_callback,
    get_language_mode,
    interrupt_speech,
    is_speaking
)

from actions import handle_action, set_ui_visual_callback
from brain import ask_aurvyn, ask_mitra
from ui import AurvynSiriUI, MitraSiriUI
from live_stream import LiveAudioSession

_global_app = None

def play_activation_beep():
    """Emits an audio beep indicating Aurvyn detected the wake word."""
    try:
        winsound.Beep(1200, 150)
    except Exception:
        pass

def process_query(query: str, app=None) -> bool:
    """
    Processes a command query from the user (voice, text, or automation).
    Returns False if Aurvyn should exit, True to continue.
    """
    query = query.strip()
    if not query:
        return True

    active_app = app or _global_app
    if active_app:
        active_app.set_user_speech(query)
        if hasattr(active_app, "set_visual_analysis"):
            set_ui_visual_callback(active_app.set_visual_analysis)

    query_lower = query.lower()

    # 1. Shutdown / Exit triggers
    exit_words = ["shutdown", "terminate", "exit program", "exit", "quit", "goodbye", "bye", "ನಿರ್ಗಮಿಸು", "ಮುಕ್ತಾಯ", "ಬಂದ್ ಮಾಡು", "ವಿದಾಯ", "ಹೋಗಿ ಬರ್ತೀನಿ"]
    if any(query_lower == w or query_lower.startswith(w + " ") or f" {w} " in f" {query_lower} " or w in query for w in exit_words):
        farewell = "ಆರ್ವಿನ್ ಎಐ ಸ್ಥಗಿತಗೊಳ್ಳುತ್ತಿದೆ. ವಿದಾಯ! ನಿಮ್ಮೊಂದಿಗೆ ಮಾತನಾಡಲು ನನಗೆ ಸಂತೋಷವಾಯಿತು!" if any('\u0c80' <= c <= '\u0cff' for c in query) else "Shutting down Aurvyn AI. Goodbye! It was a true pleasure assisting you, and I hope to speak with you again soon!"
        if active_app:
            active_app.set_aurvyn_response(farewell)
        speak(farewell)
        log_interaction(query, "System completely terminated.")
        return False

    # 2. Standby / Sleep triggers
    sleep_words = ["sleep", "go to sleep", "rest", "standby", "ಮಲಗು", "ವಿಶ್ರಾಂತಿ", "ಸ್ಟ್ಯಾಂಡ್‌ಬೈ"]
    if any(w in query_lower or w in query for w in sleep_words):
        standby_msg = "ಸ್ಟ್ಯಾಂಡ್‌ಬೈ ಮೋಡ್‌ಗೆ ಹೋಗುತ್ತಿದ್ದೇನೆ. ನಿಮಗೆ ಸಹಾಯ ಬೇಕಾದಾಗ 'ಹೇ ಆರ್ವಿನ್' ಎಂದು ಹೇಳಿ." if any('\u0c80' <= c <= '\u0cff' for c in query) else "Going back to standby. Whenever you need me, just say 'Hey Aurvyn' and I'll be right here for you."
        if active_app:
            active_app.set_aurvyn_response(standby_msg)
        speak(standby_msg)
        log_interaction(query, "Returned to standby mode.")
        return True


    # 3. Check computer automations and local system actions first
    response = handle_action(query)

    # 4. Fallback to Gemini LLM for reasoning (with browser fallback if unconfigured)
    if not response:
        print("[Aurvyn]: Querying Intelligence Engine...")
        response = ask_aurvyn(query)

    # 5. Output through voice, update GUI subtitle, and log to database
    if active_app:
        active_app.set_aurvyn_response(response)
    speak(response)
    log_interaction(query, response)
    return True

def run_gui_mode():
    """Runs Aurvyn AI with the Siri-like animated interface, live streaming toggle, and voice listener."""
    global _global_app
    print("\n" + "=" * 55)
    print("      Launching Aurvyn AI — Siri-style Visual Interface    ")
    print("=" * 55)

    _global_app = AurvynSiriUI(command_handler_fn=lambda q: process_query(q, app=_global_app))
    set_ui_callback(_global_app.set_state)
    set_ui_visual_callback(_global_app.set_visual_analysis)

    # Initialize Bidirectional Live Audio Streaming Session
    live_session = LiveAudioSession(
        ui_state_callback=_global_app.set_state,
        ui_user_speech_callback=_global_app.set_user_speech,
        ui_response_callback=_global_app.set_aurvyn_response
    )
    _global_app._live_session_ref = live_session
    live_active_event = threading.Event()

    def toggle_live_mode():
        if live_session.is_running():
            print("[Main]: Stopping Live Audio Session...")
            live_session.stop()
            live_active_event.clear()
            return False
        else:
            print("[Main]: Starting Live Audio Session...")
            interrupt_speech()
            live_active_event.set()
            live_session.start()
            return True

    _global_app.set_live_session_controller(toggle_live_mode)

    def voice_loop():
        calibrate_mic()
        speak("Aurvyn AI is ready. It's wonderful to see you! How may I assist you today?")
        while True:
            try:
                # If Live Audio Streaming mode is running, yield microphone to it
                if live_active_event.is_set():
                    time.sleep(0.5)
                    continue

                mode, command = listen_voice_input()
                if not mode:
                    continue

                if mode == "WAKE_WORD":
                    play_activation_beep()
                    if get_language_mode() == "kn":
                        speak("ಹೌದು, ನಾನು ಇಲ್ಲಿದ್ದೇನೆ! ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?")
                    else:
                        speak("Yes, I'm here! How can I help you?")
                    command = listen_command()
                    if not command:
                        continue

                should_continue = process_query(command, app=_global_app)
                if not should_continue:
                    _global_app.close()
                    break

            except Exception as e:
                print(f"[Voice Loop Exception]: {e}")
                time.sleep(1)

    # Start voice thread
    voice_thread = threading.Thread(target=voice_loop, daemon=True)
    voice_thread.start()

    # Start GUI event loop on main thread
    _global_app.run()

def run_text_mode():
    """Interactive text/CLI mode for typing commands directly."""
    print("\n" + "=" * 50)
    print("      Aurvyn AI: Interactive Text / CLI Mode       ")
    print("=" * 50)
    print("Type your commands below. Type 'exit' to quit.\n")
    from brain import get_api_status
    api_st = get_api_status()
    if api_st["configured"]:
        print(f"[Gemini API]: Connected ({api_st['masked_key']}) | Model: {api_st['model']}\n")
    else:
        print("[Gemini API]: Not configured yet. (Type 'add gemini api' or run 'python main.py --set-key <KEY>')\n")
    speak("Aurvyn AI is initialized and ready in interactive mode. It's a pleasure to assist you! How can I help you today?")

    while True:
        try:
            user_input = input("\nYou: ")
            if not user_input.strip():
                continue
            should_continue = process_query(user_input)
            if not should_continue:
                break
        except (KeyboardInterrupt, EOFError):
            print("\n")
            speak("Shutting down Aurvyn AI. Thank you for your time, and have a wonderful day ahead!")
            break

def run_cli_voice_mode():
    """Terminal-only continuous voice-activated command loop."""
    print("\n" + "=" * 50)
    print("           Aurvyn AI: Voice Mode Activated         ")
    print("=" * 50)
    print("Speak your command directly (e.g. 'open youtube', 'battery status')")
    print("or say 'Hey Aurvyn'. Say 'shutdown' or press Ctrl+C to exit.\n")

    calibrate_mic()
    speak("Aurvyn AI is ready and listening. It's wonderful to assist you! Please go ahead with your command.")

    try:
        while True:
            mode, command = listen_voice_input()
            if not mode:
                continue

            if mode == "WAKE_WORD":
                play_activation_beep()
                if get_language_mode() == "kn":
                    speak("ಹೌದು, ನಾನು ಇಲ್ಲಿದ್ದೇನೆ! ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?")
                else:
                    speak("Yes, I'm here! How can I help you?")
                command = listen_command()
                if not command:
                    continue


            should_continue = process_query(command)
            if not should_continue:
                break

    except KeyboardInterrupt:
        print("\n")
        speak("Shutting down Aurvyn AI. Thank you for your time, and have a wonderful day!")

def run_live_cli_mode():
    """Continuous terminal-based bidirectional live audio streaming session."""
    print("\n" + "=" * 55)
    print("       Aurvyn AI: Live Audio Streaming Mode (CLI)    ")
    print("=" * 55)
    print("Real-time bidirectional conversational streaming active.")
    print("Speak freely into your microphone. Say anything or interrupt Aurvyn anytime.")
    print("Press Ctrl+C to exit.\n")

    session = LiveAudioSession(
        ui_state_callback=lambda s: print(f"[{s}]", end=" ", flush=True),
        ui_user_speech_callback=lambda u: print(f"\nYou: {u}"),
        ui_response_callback=lambda r: print(f"Aurvyn: {r}")
    )
    session.start()
    try:
        while session.is_running():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[Aurvyn AI]: Shutting down Live Audio Session...")
        session.stop()

def run_diagnostics():
    """Runs automated health checks across all Aurvyn AI components."""
    print("\n" + "=" * 55)
    print("            Aurvyn AI Diagnostics & Health Check    ")
    print("=" * 55)

    # 1. Database check
    print("\n[1/5] Checking SQLite Database...")
    try:
        init_db()
        log_interaction("diag_check", "diag_ok")
        print("  -> Database initialized and test log written successfully.")
    except Exception as e:
        print(f"  -> [FAIL] Database check failed: {e}")

    # 2. Automation check
    print("\n[2/5] Checking Computer Automation Modules...")
    try:
        from automation import handle_automation
        b_res = handle_automation("battery status")
        s_res = handle_automation("system status")
        d_res = handle_automation("disk space")
        assert len(b_res) > 0, "Battery automation failed"
        assert len(s_res) > 0, "System status automation failed"
        assert len(d_res) > 0, "Disk space automation failed"
        print(f"  -> Battery: '{b_res}'")
        print(f"  -> System:  '{s_res}'")
        print("  -> Computer automation module validated successfully.")
    except Exception as e:
        print(f"  -> [FAIL] Automation check failed: {e}")

    # 3. Actions check
    print("\n[3/5] Checking System Actions & Intent Routing...")
    try:
        t_res = handle_action("what is the time")
        d_res = handle_action("what is today's date")
        h_res = handle_action("can you hear me")
        w_res = handle_action("how i am doing")
        assert "time" in t_res.lower(), f"Time action failed: {t_res}"
        assert "today is" in d_res.lower(), f"Date action failed: {d_res}"
        assert "hear you" in h_res.lower(), f"Hearing action failed: {h_res}"
        assert "doing great" in w_res.lower(), f"State action failed: {w_res}"

        # False positive guards
        assert handle_action("please update my software") == "", "False positive on 'update'"
        assert handle_action("who is the candidate") == "", "False positive on 'candidate'"
        assert handle_action("sometimes it rains") == "", "False positive on 'sometimes'"
        print("  -> All actions and false-positive guards validated.")
    except Exception as e:
        print(f"  -> [FAIL] Actions check failed: {e}")

    # 4. Brain check
    print("\n[4/5] Checking Intelligence Engine & Web Fallback...")
    try:
        from brain import get_api_status
        status = get_api_status()
        status_desc = f"Configured ({status['masked_key']}) with {status['model']}" if status["configured"] else "Not Configured (Web search fallback active)"
        print(f"  -> Gemini API Status: {status_desc}")
    except Exception as e:
        print(f"  -> [FAIL] Brain check failed: {e}")

    # 5. Engine check
    print("\n[5/5] Checking Speech Engine & Audio Output...")
    try:
        speak("Aurvyn AI diagnostic check completed successfully.")
        print("  -> Speech synthesizer tested successfully.")
    except Exception as e:
        print(f"  -> [FAIL] Engine check failed: {e}")

    print("\n" + "=" * 55)
    print("          All Diagnostics Completed!             ")
    print("=" * 55 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Aurvyn AI - Personal Voice Assistant")
    parser.add_argument("--cli", action="store_true", help="Run in command-line voice mode (no GUI)")
    parser.add_argument("--live", action="store_true", help="Run in continuous real-time bidirectional live voice streaming mode (CLI)")
    parser.add_argument("--text", "-t", action="store_true", help="Run in interactive text mode instead of voice")
    parser.add_argument("--test", action="store_true", help="Run automated diagnostic self-test and exit")
    parser.add_argument("--set-key", type=str, help="Configure and verify Gemini API key, save to .env, and exit")
    parser.add_argument("--import", "-i", dest="import_path", type=str, help="Import Gemini conversations from file/folder into memory and exit")
    args = parser.parse_args()

    # Handle immediate key setup if specified
    if args.set_key:
        from brain import save_api_key
        print("[Aurvyn AI]: Verifying and configuring Gemini API key...")
        success, message = save_api_key(args.set_key)
        if success:
            print(f"[Aurvyn AI]: SUCCESS: {message}")
            sys.exit(0)
        else:
            print(f"[Aurvyn AI]: ERROR: {message}")
            sys.exit(1)

    # Handle conversation import if specified
    if args.import_path:
        from importer import import_gemini_path
        print(f"[Aurvyn AI]: Importing Gemini conversations from '{args.import_path}'...")
        res = import_gemini_path(args.import_path)
        if res["success"]:
            print(f"[Aurvyn AI]: SUCCESS: {res['message']}")
            sys.exit(0)
        else:
            print(f"[Aurvyn AI]: ERROR: {res['message']}")
            sys.exit(1)

    # Initialize SQLite Database
    init_db()

    if args.test:
        run_diagnostics()
    elif args.live:
        run_live_cli_mode()
    elif args.text:
        run_text_mode()
    elif args.cli:
        run_cli_voice_mode()
    else:
        # Default: Launch with Siri-style visual interface
        run_gui_mode()

if __name__ == "__main__":
    main()