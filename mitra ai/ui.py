import math
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Siri Color Palette
COLOR_BG = "#0B0E17"          # Deep space dark
COLOR_CARD = "#141926"        # Glassmorphic card
COLOR_CARD_BORDER = "#252D42" # Border accent
COLOR_TEXT_MAIN = "#FFFFFF"   # Bright white text
COLOR_TEXT_MUTED = "#8E99B0"  # Subtle slate
COLOR_ACCENT_CYAN = "#00F2FE" # Electric cyan
COLOR_ACCENT_PURPLE = "#9B51E0" # Neon violet
COLOR_ACCENT_PINK = "#FF007F" # Hot magenta
COLOR_ACCENT_BLUE = "#4FACFE" # Radiant sky blue

class SiriOrbCanvas(tk.Canvas):
    """
    Animated Canvas rendering a multi-layered, glowing Siri / Apple Intelligence orb
    with fluid breathing, ripple waves, orbital spin, and equalizer soundwaves.
    """
    def __init__(self, master, width=280, height=200, **kwargs):
        super().__init__(master, width=width, height=height, bg=COLOR_BG, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.cx = width // 2
        self.cy = height // 2
        self.state = "IDLE"  # IDLE, LISTENING, PROCESSING, SPEAKING
        self.frame = 0
        self.running = True
        self._animate()

    def set_state(self, state: str):
        self.state = state

    def _animate(self):
        if not self.running:
            return

        self.delete("all")
        self.frame += 1
        f = self.frame

        cx, cy = self.cx, self.cy

        if self.state == "LISTENING":
            # Expanding radiant ripple waves
            for i in range(3):
                wave_phase = (f * 3 + i * 35) % 100
                r = 45 + wave_phase * 0.75
                color = COLOR_ACCENT_CYAN if i % 2 == 0 else COLOR_ACCENT_PINK
                self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=2)

            # Central pulsating listening core
            base_r = 40 + math.sin(f * 0.2) * 8
            self.create_oval(cx - base_r, cy - base_r, cx + base_r, cy + base_r, fill="#1B243B", outline=COLOR_ACCENT_CYAN, width=3)
            core_r = base_r * 0.65
            self.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r, fill=COLOR_ACCENT_CYAN, outline=COLOR_ACCENT_BLUE, width=2)

        elif self.state == "PROCESSING":
            # Planetary orbital rings spinning rapidly
            base_r = 42
            self.create_oval(cx - base_r, cy - base_r, cx + base_r, cy + base_r, fill="#1A1830", outline=COLOR_ACCENT_PURPLE, width=2)

            for i in range(4):
                angle = math.radians((f * 8 + i * 90) % 360)
                orbit_r = 55 + math.sin(f * 0.1 + i) * 6
                ox = cx + math.cos(angle) * orbit_r
                oy = cy + math.sin(angle) * (orbit_r * 0.45)
                dot_color = COLOR_ACCENT_CYAN if i % 2 == 0 else COLOR_ACCENT_PINK
                self.create_oval(ox - 5, oy - 5, ox + 5, oy + 5, fill=dot_color, outline="")

            # Center core
            self.create_oval(cx - 25, cy - 25, cx + 25, cy + 25, fill=COLOR_ACCENT_PURPLE, outline=COLOR_ACCENT_PINK, width=2)

        elif self.state == "SPEAKING":
            # Audio-reactive Equalizer waves pulsating
            base_r = 42 + math.sin(f * 0.25) * 6
            self.create_oval(cx - base_r, cy - base_r, cx + base_r, cy + base_r, fill="#231733", outline=COLOR_ACCENT_PINK, width=2)
            self.create_oval(cx - base_r*0.6, cy - base_r*0.6, cx + base_r*0.6, cy + base_r*0.6, fill=COLOR_ACCENT_PURPLE, outline="")

            # Vertical sound wave bars
            num_bars = 9
            bar_spacing = 14
            start_x = cx - ((num_bars - 1) * bar_spacing) // 2

            for i in range(num_bars):
                bx = start_x + i * bar_spacing
                height_factor = math.sin(f * 0.35 + i * 0.8) * 0.5 + 0.5
                bar_h = 10 + height_factor * 35
                b_color = COLOR_ACCENT_CYAN if i % 2 == 0 else COLOR_ACCENT_PINK
                self.create_line(bx, cy - bar_h, bx, cy + bar_h, fill=b_color, width=3, capstyle=tk.ROUND)

        else:
            # IDLE / STANDBY: Smooth breathing orb with soft concentric glows
            breath = math.sin(f * 0.05)
            r3 = 58 + breath * 4
            self.create_oval(cx - r3, cy - r3, cx + r3, cy + r3, outline="#1C233D", width=2)

            r2 = 46 + breath * 3
            self.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, fill="#121829", outline=COLOR_ACCENT_BLUE, width=2)

            r1 = 34 + breath * 2
            self.create_oval(cx - r1, cy - r1, cx + r1, cy + r1, fill=COLOR_ACCENT_PURPLE, outline=COLOR_ACCENT_CYAN, width=2)

            r0 = 20 + breath * 1
            self.create_oval(cx - r0, cy - r0, cx + r0, cy + r0, fill=COLOR_ACCENT_CYAN, outline="")

        self.after(35, self._animate)

    def stop(self):
        self.running = False


class AurvynSiriUI:
    """
    Siri-style Desktop Interface for Aurvyn AI.
    Features dark glassmorphism, animated Siri glowing visualizer, subtitle transcript,
    one-click computer automation shortcuts, and voice/text interaction.
    """
    def __init__(self, command_handler_fn=None):
        self.command_handler = command_handler_fn
        self.root = tk.Tk()
        self.root.title("Aurvyn AI — Computer Automation Assistant")
        self.root.geometry("520x740")
        self.root.minsize(460, 650)
        self.root.configure(bg=COLOR_BG)

        # Style configurations
        self._setup_styles()
        self._build_layout()
        self._refresh_api_button()

        # State binding
        self.is_listening = True

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=COLOR_BG)
        style.configure("Card.TFrame", background=COLOR_CARD)

    def _build_layout(self):
        # 1. Header Bar
        header = tk.Frame(self.root, bg=COLOR_BG)
        header.pack(fill=tk.X, padx=20, pady=(15, 5))

        title_lbl = tk.Label(header, text="AURVYN AI", font=("Segoe UI", 16, "bold"), fg=COLOR_TEXT_MAIN, bg=COLOR_BG)
        title_lbl.pack(side=tk.LEFT)

        self.status_badge = tk.Label(
            header,
            text="● STANDBY",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_ACCENT_CYAN,
            bg=COLOR_CARD,
            padx=10,
            pady=4
        )
        self.status_badge.pack(side=tk.RIGHT)

        self.live_btn = tk.Button(
            header,
            text="🎙️ LIVE",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD_BORDER,
            activeforeground=COLOR_ACCENT_PINK,
            relief=tk.FLAT,
            bd=0,
            padx=7,
            pady=4,
            cursor="hand2",
            command=self._on_toggle_live
        )
        self.live_btn.pack(side=tk.RIGHT, padx=(0, 6))

        self.key_btn = tk.Button(
            header,
            text="🔑 API KEY",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD_BORDER,
            activeforeground=COLOR_ACCENT_CYAN,
            relief=tk.FLAT,
            bd=0,
            padx=7,
            pady=4,
            cursor="hand2",
            command=self._open_api_key_dialog
        )
        self.key_btn.pack(side=tk.RIGHT, padx=(0, 6))

        self.import_btn = tk.Button(
            header,
            text="📥 IMPORT",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD_BORDER,
            activeforeground=COLOR_ACCENT_CYAN,
            relief=tk.FLAT,
            bd=0,
            padx=7,
            pady=4,
            cursor="hand2",
            command=self._open_import_dialog
        )
        self.import_btn.pack(side=tk.RIGHT, padx=(0, 6))

        self.history_btn = tk.Button(
            header,
            text="📜 MEMORY",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD_BORDER,
            activeforeground=COLOR_ACCENT_CYAN,
            relief=tk.FLAT,
            bd=0,
            padx=7,
            pady=4,
            cursor="hand2",
            command=self._open_history_dialog
        )
        self.history_btn.pack(side=tk.RIGHT, padx=(0, 6))

        self.lang_btn = tk.Button(
            header,
            text="🌐 AUTO",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_ACCENT_CYAN,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD_BORDER,
            activeforeground=COLOR_ACCENT_CYAN,
            relief=tk.FLAT,
            bd=0,
            padx=7,
            pady=4,
            cursor="hand2",
            command=self._toggle_language
        )
        self.lang_btn.pack(side=tk.RIGHT, padx=(0, 6))


        # 2. Siri Animated Orb
        self.orb = SiriOrbCanvas(self.root, width=280, height=190)
        self.orb.pack(pady=(5, 5))
        self.orb.bind("<Button-1>", lambda e: self._on_interrupt())

        # Interruption Hotkey (Escape cuts off speech immediately)
        self.root.bind("<Escape>", lambda e: self._on_interrupt())

        # 3. Subtitle / Dialogue Card
        self.dialogue_card = tk.Frame(self.root, bg=COLOR_CARD, highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)
        self.dialogue_card.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        # User Speech Bubble
        self.user_label = tk.Label(
            self.dialogue_card,
            text='Speak freely: "how are you", "what is the time", "analyze this error on my screen", "take a screenshot"...',
            font=("Segoe UI", 10, "italic"),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            wraplength=440,
            justify=tk.LEFT,
            anchor="w"
        )
        self.user_label.pack(fill=tk.X, padx=15, pady=(10, 5))

        # Divider
        sep = tk.Frame(self.dialogue_card, bg=COLOR_CARD_BORDER, height=1)
        sep.pack(fill=tk.X, padx=15, pady=3)

        # Aurvyn Response Bubble
        self.aurvyn_label = tk.Label(
            self.dialogue_card,
            text="Hello! Aurvyn AI is ready to assist you. Speak freely or click any shortcut below to begin.",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD,
            wraplength=440,
            justify=tk.LEFT,
            anchor="w"
        )
        self.aurvyn_label.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 10))
        self.mitra_label = self.aurvyn_label  # Backward compatibility alias

        # Vision / Screen Context Card (dynamically displayed when multimodal OCR/analysis arrives)
        self.vision_frame = tk.Frame(self.dialogue_card, bg="#0D1117", highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)

        v_head = tk.Frame(self.vision_frame, bg="#0D1117")
        v_head.pack(fill=tk.X, padx=10, pady=(6, 4))

        self.v_title_lbl = tk.Label(v_head, text="🔍 SCREEN CONTEXT & DEBUGGING", font=("Segoe UI", 8, "bold"), fg=COLOR_ACCENT_CYAN, bg="#0D1117")
        self.v_title_lbl.pack(side=tk.LEFT)

        self.v_copy_btn = tk.Button(
            v_head,
            text="📋 COPY ADVICE",
            font=("Segoe UI", 7, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD_BORDER,
            activebackground=COLOR_ACCENT_CYAN,
            activeforeground=COLOR_BG,
            relief=tk.FLAT,
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._copy_vision_details
        )
        self.v_copy_btn.pack(side=tk.RIGHT)

        v_box = tk.Frame(self.vision_frame, bg="#0D1117")
        v_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self.v_scroll = tk.Scrollbar(v_box)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.v_text = tk.Text(
            v_box,
            font=("Consolas", 9),
            bg="#0D1117",
            fg="#E6EDF3",
            wrap=tk.WORD,
            yscrollcommand=self.v_scroll.set,
            relief=tk.FLAT,
            height=5,
            padx=6,
            pady=4
        )
        self.v_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.v_scroll.config(command=self.v_text.yview)

        # 4. Quick Automation Chips (Siri Suggestions)
        chips_frame = tk.Frame(self.root, bg=COLOR_BG)
        chips_frame.pack(fill=tk.X, padx=15, pady=(0, 8))

        shortcuts = [
            ("🔍 Vision OCR", "analyze what is on my screen"),
            ("🐛 Debug Error", "analyze this error on my screen"),
            ("📸 Screenshot", "take a screenshot"),
            ("🔋 Battery", "battery status"),
            ("💻 System", "system status"),
            ("🕒 Time", "what is the time"),
            ("🔊 Volume 50%", "set volume to 50%"),
            ("☀️ Brightness", "set brightness to 50%"),
            ("🌐 YouTube", "open youtube"),
            ("📝 Notepad", "open notepad"),
            ("📂 Downloads", "open downloads"),
            ("🌐 ಕನ್ನಡ / EN", "switch to kannada")
        ]


        # Render chips in 3 rows of 4
        for idx, (label, cmd) in enumerate(shortcuts):
            row = idx // 4
            col = idx % 4
            btn = tk.Button(
                chips_frame,
                text=label,
                font=("Segoe UI", 8),
                fg=COLOR_TEXT_MAIN,
                bg=COLOR_CARD,
                activebackground=COLOR_CARD_BORDER,
                activeforeground=COLOR_ACCENT_CYAN,
                relief=tk.FLAT,
                bd=0,
                padx=6,
                pady=4,
                cursor="hand2",
                command=lambda c=cmd: self._trigger_command(c)
            )
            btn.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            chips_frame.columnconfigure(col, weight=1)

        # 5. Bottom Interactive Input Dock
        dock = tk.Frame(self.root, bg=COLOR_CARD, highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)
        dock.pack(fill=tk.X, padx=20, pady=(0, 15))

        self.input_entry = tk.Entry(
            dock,
            font=("Segoe UI", 11),
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_ACCENT_CYAN,
            relief=tk.FLAT,
            bd=0
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 6), pady=10)
        self.input_entry.bind("<Return>", lambda e: self._on_send_click())
        self.input_entry.insert(0, "")

        send_btn = tk.Button(
            dock,
            text="SEND",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_BG,
            bg=COLOR_ACCENT_CYAN,
            activebackground=COLOR_ACCENT_BLUE,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._on_send_click
        )
        send_btn.pack(side=tk.RIGHT, padx=(0, 8), pady=8)

    def set_live_session_controller(self, controller_fn):
        """Registers a callable from main.py to toggle the live audio session."""
        self._live_session_controller = controller_fn

    def _on_toggle_live(self):
        """Toggles real-time bidirectional live streaming mode."""
        if hasattr(self, "_live_session_controller") and self._live_session_controller:
            try:
                is_active = self._live_session_controller()
                if is_active:
                    self.live_btn.config(text="🔴 LIVE ON", fg=COLOR_ACCENT_PINK)
                    self.status_badge.config(text="● LIVE SESSION", fg=COLOR_ACCENT_PINK)
                else:
                    self.live_btn.config(text="🎙️ LIVE", fg=COLOR_TEXT_MAIN)
                    self.status_badge.config(text="● STANDBY", fg=COLOR_ACCENT_CYAN)
            except Exception as e:
                print(f"[UI Live Toggle Error]: {e}")

    def _on_interrupt(self):
        """Triggered by Escape key or orb click to cut off assistant speech immediately."""
        try:
            from engine import interrupt_speech
            interrupt_speech()
        except Exception:
            pass
        if hasattr(self, "_live_session_ref") and self._live_session_ref:
            try:
                self._live_session_ref.interrupt()
            except Exception:
                pass

    def set_state(self, state: str):
        """Thread-safe state update for Siri Orb and status pill."""
        self.root.after(0, self._apply_state, state)

    def _apply_state(self, state: str):
        self.orb.set_state(state)
        badges = {
            "IDLE": ("● STANDBY", COLOR_ACCENT_CYAN),
            "LISTENING": ("● LISTENING...", COLOR_ACCENT_PINK),
            "PROCESSING": ("● THINKING...", COLOR_ACCENT_PURPLE),
            "SPEAKING": ("● SPEAKING...", COLOR_ACCENT_BLUE),
        }
        text, color = badges.get(state, ("● ACTIVE", COLOR_ACCENT_CYAN))
        self.status_badge.config(text=text, fg=color)

    def set_user_speech(self, text: str):
        """Thread-safe update of user speech bubble."""
        self.root.after(0, lambda: self.user_label.config(text=f'You: "{text}"', fg=COLOR_TEXT_MAIN))

    def set_aurvyn_response(self, text: str):
        """Thread-safe update of Aurvyn's vocal response bubble."""
        def _update():
            self.aurvyn_label.config(text=f"Aurvyn: {text}", fg=COLOR_TEXT_MAIN)
        self.root.after(0, _update)

    def set_mitra_response(self, text: str):
        """Legacy alias for set_aurvyn_response."""
        self.set_aurvyn_response(text)

    def set_visual_analysis(self, title: str, spoken_summary: str, details_text: str):
        """
        Thread-safe update to display multimodal screen analysis inside the Tkinter card.
        Shows the spoken summary in the main label and extracted code / debugging advice in the vision card.
        """
        def _update():
            self.aurvyn_label.config(text=f"Aurvyn: {spoken_summary}", fg=COLOR_TEXT_MAIN)
            self._last_vision_details = details_text
            self.v_title_lbl.config(text=f"🔍 {title.upper()[:35]}")
            self.v_text.config(state=tk.NORMAL)
            self.v_text.delete("1.0", tk.END)
            self.v_text.insert(tk.END, details_text)
            self.v_text.config(state=tk.DISABLED)
            if not self.vision_frame.winfo_ismapped():
                self.vision_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        self.root.after(0, _update)

    def _copy_vision_details(self):
        """Copies the extracted code or debugging advice to the Windows clipboard."""
        if hasattr(self, "_last_vision_details") and self._last_vision_details:
            try:
                import pyperclip
                pyperclip.copy(self._last_vision_details)
                self.v_copy_btn.config(text="✅ COPIED!")
                self.root.after(1500, lambda: self.v_copy_btn.config(text="📋 COPY ADVICE"))
            except Exception:
                pass

    def _on_send_click(self):
        query = self.input_entry.get().strip()
        if query:
            self.input_entry.delete(0, tk.END)
            self._trigger_command(query)

    def _trigger_command(self, query: str):
        self.set_user_speech(query)
        if self.command_handler:
            threading.Thread(target=self.command_handler, args=(query,), daemon=True).start()

    def _refresh_api_button(self):
        """Updates the header API button text and style according to Gemini status."""
        try:
            from brain import get_api_status
            status = get_api_status()
            if status["configured"]:
                self.key_btn.config(
                    text="⚡ GEMINI",
                    fg=COLOR_ACCENT_CYAN,
                    bg=COLOR_CARD
                )
            else:
                self.key_btn.config(
                    text="🔑 API KEY",
                    fg=COLOR_TEXT_MAIN,
                    bg=COLOR_CARD
                )
        except Exception:
            pass

    def _open_api_key_dialog(self):
        """Opens a modern dark dialog to configure and test the Gemini API Key."""
        import webbrowser
        from brain import get_api_status, save_api_key

        dialog = tk.Toplevel(self.root)
        dialog.title("Aurvyn AI — Gemini API Settings")
        dialog.geometry("450x390")
        dialog.resizable(False, False)
        dialog.configure(bg=COLOR_BG)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog relative to main window
        try:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 195
            dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass

        # Container card
        card = tk.Frame(dialog, bg=COLOR_CARD, highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)
        card.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # Title
        tk.Label(
            card,
            text="⚡ Google Gemini API Configuration",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD
        ).pack(anchor="w", padx=15, pady=(15, 4))

        tk.Label(
            card,
            text="Add your Gemini API key to enable direct voice reasoning and question answering.",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            wraplength=380,
            justify=tk.LEFT
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # Status row
        status = get_api_status()
        status_text = f"Status: Connected ({status['masked_key']})" if status["configured"] else "Status: Not configured (Web search fallback active)"
        status_color = COLOR_ACCENT_CYAN if status["configured"] else COLOR_ACCENT_PINK
        status_lbl = tk.Label(card, text=status_text, font=("Segoe UI", 9, "bold"), fg=status_color, bg=COLOR_CARD)
        status_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        # Link button to Google AI Studio
        link_btn = tk.Button(
            card,
            text="🌐 Get a free API key at Google AI Studio ↗",
            font=("Segoe UI", 9, "underline"),
            fg=COLOR_ACCENT_BLUE,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_ACCENT_CYAN,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey")
        )
        link_btn.pack(anchor="w", padx=15, pady=(0, 10))

        # Input label
        tk.Label(card, text="Gemini API Key:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_MAIN, bg=COLOR_CARD).pack(anchor="w", padx=15, pady=(0, 4))

        # Entry container
        entry_frame = tk.Frame(card, bg=COLOR_CARD_BORDER, padx=1, pady=1)
        entry_frame.pack(fill=tk.X, padx=15, pady=(0, 6))

        key_entry = tk.Entry(
            entry_frame,
            font=("Consolas", 10),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_ACCENT_CYAN,
            relief=tk.FLAT,
            bd=5,
            show="*"
        )
        key_entry.pack(fill=tk.X)

        # Show / Hide toggle
        show_var = tk.BooleanVar(value=False)
        def toggle_show():
            key_entry.config(show="" if show_var.get() else "*")

        cb = tk.Checkbutton(
            card,
            text="Show API Key",
            variable=show_var,
            command=toggle_show,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_TEXT_MAIN,
            selectcolor=COLOR_BG
        )
        cb.pack(anchor="w", padx=15, pady=(0, 6))

        # Result / Feedback label
        feedback_lbl = tk.Label(card, text="", font=("Segoe UI", 9), fg=COLOR_ACCENT_PINK, bg=COLOR_CARD, wraplength=380)
        feedback_lbl.pack(fill=tk.X, padx=15, pady=(0, 8))

        # Action Buttons frame
        btn_frame = tk.Frame(card, bg=COLOR_CARD)
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        def on_save():
            entered_key = key_entry.get().strip()
            if not entered_key:
                feedback_lbl.config(text="Please enter an API key.", fg=COLOR_ACCENT_PINK)
                return

            feedback_lbl.config(text="⏳ Verifying key with Gemini API...", fg=COLOR_ACCENT_CYAN)
            save_btn.config(state=tk.DISABLED)

            def test_and_save_worker():
                success, msg = save_api_key(entered_key)
                def update_ui():
                    save_btn.config(state=tk.NORMAL)
                    if success:
                        feedback_lbl.config(text="✅ " + msg, fg=COLOR_ACCENT_CYAN)
                        status_lbl.config(text=f"Status: Connected ({entered_key[:6]}...{entered_key[-4:]})", fg=COLOR_ACCENT_CYAN)
                        self.set_aurvyn_response("Gemini API connected successfully! It's a pleasure to assist you. How can I help you today?")
                        self._refresh_api_button()
                        dialog.after(1500, dialog.destroy)
                    else:
                        feedback_lbl.config(text="❌ " + msg, fg=COLOR_ACCENT_PINK)
                dialog.after(0, update_ui)

            threading.Thread(target=test_and_save_worker, daemon=True).start()

        save_btn = tk.Button(
            btn_frame,
            text="SAVE & VERIFY",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_BG,
            bg=COLOR_ACCENT_CYAN,
            activebackground=COLOR_ACCENT_BLUE,
            relief=tk.FLAT,
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=on_save
        )
        save_btn.pack(side=tk.RIGHT, padx=(8, 0))

        cancel_btn = tk.Button(
            btn_frame,
            text="CLOSE",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD_BORDER,
            activeforeground=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=dialog.destroy
        )
        cancel_btn.pack(side=tk.RIGHT)

    def _open_import_dialog(self):
        """Opens a dark-themed dialog allowing users to upload and import Gemini conversation exports."""
        import os
        import webbrowser
        from database import get_total_interactions_count
        from importer import import_gemini_path

        dialog = tk.Toplevel(self.root)
        dialog.title("Import Gemini Conversations — Aurvyn AI")
        dialog.geometry("490x530")
        dialog.resizable(False, False)
        dialog.configure(bg=COLOR_BG)
        dialog.transient(self.root)
        dialog.grab_set()

        try:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 245
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 265
            dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass

        card = tk.Frame(dialog, bg=COLOR_CARD, highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)
        card.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # Title
        tk.Label(
            card,
            text="📥 Import Gemini Conversations",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD
        ).pack(anchor="w", padx=15, pady=(15, 4))

        tk.Label(
            card,
            text="Collect your previous Gemini / Bard chats from Google Takeout or custom export files and upload them into Aurvyn AI's memory.",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            wraplength=420,
            justify=tk.LEFT
        ).pack(anchor="w", padx=15, pady=(0, 8))

        # Memory count indicator
        count = get_total_interactions_count()
        count_lbl = tk.Label(
            card,
            text=f"🧠 Current Stored Interactions: {count}",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_ACCENT_CYAN,
            bg=COLOR_CARD
        )
        count_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        # Supported formats frame
        fmt_frame = tk.Frame(card, bg=COLOR_BG, padx=10, pady=8, highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)
        fmt_frame.pack(fill=tk.X, padx=15, pady=(0, 12))

        tk.Label(
            fmt_frame,
            text="Supported Export Formats:",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_ACCENT_BLUE,
            bg=COLOR_BG
        ).pack(anchor="w")

        tk.Label(
            fmt_frame,
            text="• Google Takeout Archive (.zip or folder)\n• JSON chat exports (.json)\n• CSV spreadsheets (.csv)\n• HTML activity logs (.html)\n• Plain text & Markdown transcripts (.txt, .md)",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG,
            justify=tk.LEFT
        ).pack(anchor="w", pady=(2, 0))

        # Link to Google Takeout
        tk.Button(
            card,
            text="🌐 How to export chats from Google Takeout ↗",
            font=("Segoe UI", 8, "underline"),
            fg=COLOR_ACCENT_BLUE,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_ACCENT_CYAN,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=lambda: webbrowser.open("https://takeout.google.com")
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # File Selection Input Frame
        tk.Label(card, text="Select Export File or Folder:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_MAIN, bg=COLOR_CARD).pack(anchor="w", padx=15, pady=(0, 4))

        sel_frame = tk.Frame(card, bg=COLOR_CARD)
        sel_frame.pack(fill=tk.X, padx=15, pady=(0, 8))

        path_entry = tk.Entry(
            sel_frame,
            font=("Segoe UI", 9),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_ACCENT_CYAN,
            relief=tk.FLAT,
            bd=5
        )
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        def browse_file():
            f = filedialog.askopenfilename(
                title="Select Gemini Export File",
                filetypes=[
                    ("All Supported Exports", "*.json;*.zip;*.csv;*.html;*.htm;*.txt;*.md"),
                    ("Google Takeout ZIP", "*.zip"),
                    ("JSON Chat Export", "*.json"),
                    ("CSV Spreadsheet", "*.csv"),
                    ("HTML Activity Export", "*.html;*.htm"),
                    ("Text / Markdown Transcript", "*.txt;*.md"),
                    ("All Files", "*.*")
                ]
            )
            if f:
                path_entry.delete(0, tk.END)
                path_entry.insert(0, f)

        def browse_folder():
            d = filedialog.askdirectory(title="Select Extracted Takeout Folder")
            if d:
                path_entry.delete(0, tk.END)
                path_entry.insert(0, d)

        file_btn = tk.Button(
            sel_frame,
            text="📂 FILE",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD_BORDER,
            activebackground=COLOR_ACCENT_CYAN,
            activeforeground=COLOR_BG,
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=browse_file
        )
        file_btn.pack(side=tk.LEFT, padx=(0, 4))

        folder_btn = tk.Button(
            sel_frame,
            text="📁 FOLDER",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD_BORDER,
            activebackground=COLOR_ACCENT_CYAN,
            activeforeground=COLOR_BG,
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=browse_folder
        )
        folder_btn.pack(side=tk.LEFT)

        # Status / Feedback label
        feedback_lbl = tk.Label(card, text="", font=("Segoe UI", 9), fg=COLOR_ACCENT_PINK, bg=COLOR_CARD, wraplength=420)
        feedback_lbl.pack(fill=tk.X, padx=15, pady=(4, 10))

        # Bottom Buttons
        btn_frame = tk.Frame(card, bg=COLOR_CARD)
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        def start_import():
            target_path = path_entry.get().strip().strip("'\"")
            if not target_path:
                feedback_lbl.config(text="Please select a file or folder to import.", fg=COLOR_ACCENT_PINK)
                return

            if not os.path.exists(target_path):
                feedback_lbl.config(text=f"Selected path does not exist: {target_path}", fg=COLOR_ACCENT_PINK)
                return

            feedback_lbl.config(text="⏳ Parsing and importing conversations...", fg=COLOR_ACCENT_CYAN)
            import_action_btn.config(state=tk.DISABLED)

            def worker():
                res = import_gemini_path(target_path)
                def done():
                    import_action_btn.config(state=tk.NORMAL)
                    if res["success"]:
                        feedback_lbl.config(text="✅ " + res["message"], fg=COLOR_ACCENT_CYAN)
                        new_count = get_total_interactions_count()
                        count_lbl.config(text=f"🧠 Current Stored Interactions: {new_count}")
                        self.set_aurvyn_response(f"I've imported {res['imported']} previous conversation exchanges into my memory!")
                    else:
                        feedback_lbl.config(text="❌ " + res["message"], fg=COLOR_ACCENT_PINK)
                dialog.after(0, done)

            threading.Thread(target=worker, daemon=True).start()

        import_action_btn = tk.Button(
            btn_frame,
            text="IMPORT NOW",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_BG,
            bg=COLOR_ACCENT_CYAN,
            activebackground=COLOR_ACCENT_BLUE,
            relief=tk.FLAT,
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=start_import
        )
        import_action_btn.pack(side=tk.RIGHT, padx=(8, 0))

        close_btn = tk.Button(
            btn_frame,
            text="CLOSE",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD_BORDER,
            activeforeground=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT)

    def _open_history_dialog(self):
        """Opens a modal to view recent conversations stored in Aurvyn AI memory."""
        from database import get_recent_interactions, get_total_interactions_count

        dialog = tk.Toplevel(self.root)
        dialog.title("Aurvyn AI — Conversation Memory")
        dialog.geometry("520x560")
        dialog.minsize(450, 400)
        dialog.configure(bg=COLOR_BG)
        dialog.transient(self.root)

        try:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 260
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 280
            dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass

        card = tk.Frame(dialog, bg=COLOR_CARD, highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)
        card.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # Header
        top_bar = tk.Frame(card, bg=COLOR_CARD)
        top_bar.pack(fill=tk.X, padx=15, pady=(15, 8))

        tk.Label(
            top_bar,
            text="📜 Conversation Memory",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD
        ).pack(side=tk.LEFT)

        total_cnt = get_total_interactions_count()
        total_lbl = tk.Label(
            top_bar,
            text=f"Total: {total_cnt}",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_ACCENT_CYAN,
            bg=COLOR_BG,
            padx=8,
            pady=2
        )
        total_lbl.pack(side=tk.RIGHT)

        # Scrollable text widget for records
        txt_frame = tk.Frame(card, bg=COLOR_BG)
        txt_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        scrollbar = tk.Scrollbar(txt_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        txt = tk.Text(
            txt_frame,
            bg=COLOR_BG,
            fg=COLOR_TEXT_MAIN,
            font=("Segoe UI", 9),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=txt.yview)

        # Configure tags
        txt.tag_configure("time", foreground=COLOR_TEXT_MUTED, font=("Segoe UI", 8, "italic"))
        txt.tag_configure("user", foreground=COLOR_ACCENT_CYAN, font=("Segoe UI", 9, "bold"))
        txt.tag_configure("aurvyn", foreground=COLOR_TEXT_MAIN, font=("Segoe UI", 9))
        txt.tag_configure("divider", foreground=COLOR_CARD_BORDER)

        def populate_history():
            txt.config(state=tk.NORMAL)
            txt.delete("1.0", tk.END)
            records = get_recent_interactions(limit=60)
            if not records:
                txt.insert(tk.END, "No recorded interactions found in memory yet.\n", "user")
            else:
                for ts, u, r in records:
                    txt.insert(tk.END, f"[{ts}]\n", "time")
                    txt.insert(tk.END, f"You: {u}\n", "user")
                    txt.insert(tk.END, f"Aurvyn: {r}\n", "aurvyn")
                    txt.insert(tk.END, "-" * 55 + "\n\n", "divider")
            txt.config(state=tk.DISABLED)

        populate_history()

        # Bottom bar
        bot_bar = tk.Frame(card, bg=COLOR_CARD)
        bot_bar.pack(fill=tk.X, padx=15, pady=(0, 15))

        refresh_btn = tk.Button(
            bot_bar,
            text="🔄 REFRESH",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD_BORDER,
            activebackground=COLOR_ACCENT_CYAN,
            activeforeground=COLOR_BG,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=populate_history
        )
        refresh_btn.pack(side=tk.LEFT)

        close_btn = tk.Button(
            bot_bar,
            text="CLOSE",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            activebackground=COLOR_CARD_BORDER,
            activeforeground=COLOR_TEXT_MAIN,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT)

    def _toggle_language(self):
        """Cycles active speech recognition and conversational language mode."""
        from engine import get_language_mode, set_language_mode
        curr = get_language_mode()
        if curr == "auto":
            set_language_mode("kn")
            self.lang_btn.config(text="🌐 ಕನ್ನಡ", fg=COLOR_ACCENT_PINK)
            self.set_aurvyn_response("ಕನ್ನಡ ಮೋಡ್ ಸಕ್ರಿಯಗೊಂಡಿದೆ. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?")
        elif curr == "kn":
            set_language_mode("en")
            self.lang_btn.config(text="🌐 EN", fg=COLOR_ACCENT_BLUE)
            self.set_aurvyn_response("English language mode activated. How may I assist you?")
        else:
            set_language_mode("auto")
            self.lang_btn.config(text="🌐 AUTO", fg=COLOR_ACCENT_CYAN)
            self.set_aurvyn_response("Bilingual auto mode activated (English + ಕನ್ನಡ).")

    def run(self):

        self.root.mainloop()

    def close(self):
        self.orb.stop()
        try:
            self.root.destroy()
        except Exception:
            pass

# Backward compatibility alias
MitraSiriUI = AurvynSiriUI
