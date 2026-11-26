# M.I.T.R.A. AI

<p align="center">
  <strong>A modular, voice-enabled personal desktop assistant built with Python.</strong><br>
  Bringing AI conversations, voice interaction, desktop actions, and local conversation history together.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Google Gemini" src="https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white">
</p>

## Overview

**M.I.T.R.A. AI** is an ongoing personal assistant project that explores how AI can work alongside a desktop computer. It combines a Google Gemini-powered conversation engine with speech input and output, a graphical interface, selected computer actions, and SQLite-based interaction history.

The project is designed with separate modules for conversation, voice processing, desktop actions, interface handling, and data storage. This modular structure makes it easier to understand, test, and extend each part independently.

> This repository is under active development. Features and setup steps may change as the project evolves.

## Features

- **AI conversations** — Send questions to the Google Gemini API and receive responses.
- **Voice interaction** — Speech recognition, text-to-speech, and wake-word support.
- **Live audio mode** — Optional real-time, bidirectional audio conversation using the live audio component.
- **Desktop interface** — A visual assistant interface with listening, processing, and speaking states.
- **Computer actions** — Run supported desktop tasks and system checks through the action and automation modules.
- **Conversation history** — Store interactions locally with SQLite.
- **Conversation import** — Import supported conversation exports into local memory.
- **Multiple run modes** — Launch the graphical interface, text mode, voice mode, or live audio mode.

## Technology Stack

| Technology | Purpose |
| --- | --- |
| Python | Main programming language |
| Google Gemini API | AI conversation and live audio capabilities |
| SQLite | Local conversation storage |
| SpeechRecognition | Speech-to-text input |
| PyAudioWPatch | Audio input support |
| pyttsx3 / gTTS | Text-to-speech output |
| PyAutoGUI | Desktop automation support |
| psutil | System information and monitoring |
| Tkinter | Desktop graphical interface |

## Project Structure

The application source is currently inside the `mitra ai/` directory.

| File | Responsibility |
| --- | --- |
| `main.py` | Application entry point and run modes |
| `brain.py` | Gemini integration and AI response handling |
| `engine.py` | Voice input, speech output, and wake-word handling |
| `actions.py` | Command handling and supported desktop actions |
| `automation.py` | Computer automation and system checks |
| `database.py` | SQLite database setup and interaction history |
| `importer.py` | Importing conversation history |
| `live_stream.py` | Real-time audio session handling |
| `ui.py` | Graphical user interface |
| `requirements.txt` | Python dependencies |

## Getting Started

### 1. Requirements

- Windows (the current implementation uses Windows-specific components)
- Python installed and available from the terminal
- A Google Gemini API key
- A working microphone and speakers for voice features

### 2. Clone the repository

```bash
git clone https://github.com/totendrahiremath/mitra-ai.git
cd mitra-ai
```

### 3. Open the application folder

```bash
cd "mitra ai"
```

### 4. Install dependencies

It is recommended to use a virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure the Gemini API key

Get an API key from [Google AI Studio](https://aistudio.google.com/apikey), then configure it using:

```bash
python main.py --set-key YOUR_GEMINI_API_KEY
```

Keep your API key private. Do not commit API keys or your `.env` file to GitHub.

### 6. Run M.I.T.R.A. AI

Launch the graphical interface:

```bash
python main.py
```

Other available modes:

| Command | Mode |
| --- | --- |
| `python main.py --text` | Interactive text mode |
| `python main.py --cli` | Voice mode in the terminal |
| `python main.py --live` | Live audio mode in the terminal |
| `python main.py --test` | Run built-in diagnostics |

For command-line options, run:

```bash
python main.py --help
```

## Privacy & Security

- The application uses a Gemini API key to access Google's AI service.
- Conversation history is stored locally in SQLite by the application.
- Do not publish API keys, personal conversation history, or local database files.
- Review desktop actions before using them, especially actions that change files or system settings.

## Current Development Focus

M.I.T.R.A. AI is being developed step by step. Areas of ongoing improvement include:

- Improving reliability of voice interaction and wake-word detection.
- Strengthening conversation memory and data handling.
- Improving error handling and application stability.
- Making desktop actions safer and easier to extend.
- Improving setup documentation and cross-module testing.

## Contributing

Suggestions, bug reports, and constructive feedback are welcome. If you find an issue, please open a GitHub issue with steps to reproduce it.

## Project

Created and maintained by **[Totendra Hiremath](https://github.com/totendrahiremath)**.

---

<p align="center">
  <em>Built with curiosity, Python, and a passion for practical AI.</em>
</p>
