import sys
import webbrowser
from brain import get_api_status, save_api_key

def main():
    print("=" * 60)
    print("       Aurvyn AI — Gemini API Key Setup & Configuration      ")
    print("=" * 60)

    status = get_api_status()
    if status["configured"]:
        print(f"\n[Status]: Gemini API is currently CONFIGURED.")
        print(f"  • Masked Key: {status['masked_key']}")
        print(f"  • Model:      {status['model']}\n")
    else:
        print("\n[Status]: Gemini API is NOT configured yet.")
        print("Aurvyn AI falls back to browser search when answering general questions.")
        print("Configuring a key enables direct, vocal AI answers.\n")

    print("Options:")
    print("  1. Enter or update your Gemini API key")
    print("  2. Open Google AI Studio in browser to get a free API key")
    print("  3. Exit")

    choice = input("\nEnter choice (1, 2, or 3): ").strip()

    if choice == "2":
        print("\nOpening Google AI Studio in your default browser...")
        webbrowser.open("https://aistudio.google.com/app/apikey")
        choice = input("\nOnce you have copied your key, press 1 to enter it (or 3 to exit): ").strip()

    if choice == "1":
        key = input("\nPaste your Gemini API key: ").strip()
        if not key:
            print("No key entered. Exiting setup.")
            return

        print("\nVerifying key with Google Gemini API...")
        success, message = save_api_key(key)
        if success:
            print(f"\n✅ SUCCESS: {message}")
            print("Your key has been saved to .env and is ready for Aurvyn AI!\n")
        else:
            print(f"\n❌ ERROR: {message}\n")
    else:
        print("\nExiting setup.")

if __name__ == "__main__":
    main()
