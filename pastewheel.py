import threading
import time
import sys
import tkinter as tk

try:
    import keyboard
except ImportError:
    print("Missing: pip install keyboard"); sys.exit(1)
try:
    import mouse as mouse_lib
except ImportError:
    print("Missing: pip install mouse"); sys.exit(1)
try:
    import pyperclip
except ImportError:
    print("Missing: pip install pyperclip"); sys.exit(1)


#  CONFIGURATION

MESSAGES = [
    {"text": "pls beg",    "cooldown": 10},
    {"text": "pls hunt",   "cooldown": 10},
    {"text": "pls dig",    "cooldown":  10},
    {"text": "pls fish catch",   "cooldown":  6},
    {"text": "pls search", "cooldown":  2},
    {"text": "pls crime", "cooldown":  2},
]

REBIND_Z_TO_PASTE  = True   # Z alone  → paste next message
REBIND_X_TO_ENTER  = True   # X        → Enter
REBIND_C_TO_CLICK  = True   # C        → Left Click (suppresses c)


#  STATE
last_used: dict = {}
current_index   = 0
lock            = threading.Lock()

log_entries: list = []
MAX_LOG = 60
_gui = None

#  PASTE LOGIC
def get_next_message():
    global current_index
    now = time.time()
    with lock:
        for i in range(len(MESSAGES)):
            idx = (current_index + i) % len(MESSAGES)
            m   = MESSAGES[idx]
            if now - last_used.get(m["text"], 0) >= m["cooldown"]:
                last_used[m["text"]] = now
                current_index = (idx + 1) % len(MESSAGES)
                return m["text"]
    return None


def do_paste():
    """Runs in a background thread so we never block the keyboard hook."""
    msg = get_next_message()
    if msg:
        pyperclip.copy(msg)
        time.sleep(0.06)        # let clipboard settle before sending Ctrl+V
        keyboard.send("ctrl+v") # injected event → won't be caught by our hook
        _log(f"ok  {msg}")
    else:
        now  = time.time()
        info = ", ".join(
            f"{m['text']}({m['cooldown'] - (now - last_used.get(m['text'], 0)):.1f}s)"
            for m in MESSAGES
            if (now - last_used.get(m["text"], 0)) < m["cooldown"]
        )
        _log(f"cd  All on cooldown  [{info}]")
    _refresh_gui()


def _log(msg: str):
    t = time.strftime("%H:%M:%S")
    log_entries.insert(0, f"{t}  {msg}")
    if len(log_entries) > MAX_LOG:
        log_entries.pop()


def _refresh_gui():
    if _gui and _gui.root.winfo_exists():
        _gui.root.after(0, _gui.refresh)


# event.injected == True mark own events, pass through
# event.injected == False surpresses 

def on_key(event):
    # always pass injected (synthetic) events straight through
    if getattr(event, "injected", False):
        return True

    name  = (event.name or "").lower()
    is_dn = event.event_type == keyboard.KEY_DOWN

    # Z paste next
    if REBIND_Z_TO_PASTE and name == "z":
        if is_dn:
            threading.Thread(target=do_paste, daemon=True).start()
        return False

    # X Enter
    if REBIND_X_TO_ENTER and name == "x":
        if is_dn:
            keyboard.send("enter")
        return False

    # C Left Click
    if REBIND_C_TO_CLICK and name == "c":
        if is_dn:
            mouse_lib.click("left")
        return False

    # Everything else pass through otherwise its disabled
    return True

# unnecessary GUI
DARK   = "#0f0f17"
PANEL  = "#17171f"
CARD   = "#1e1e2e"
BORDER = "#2a2a3f"
ACCENT = "#7c6af7"
GREEN  = "#4ade80"
AMBER  = "#fbbf24"
FG     = "#e2e0ff"
MUTED  = "#6b6890"


class PasteWheelGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Paste Wheel")
        self.root.geometry("480x620")
        self.root.minsize(420, 500)
        self.root.configure(bg=DARK)
        self.root.resizable(True, True)
        self._build()
        self.refresh()

    def _build(self):
        # Header
        hdr = tk.Frame(self.root, bg=PANEL, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="◉ PASTE WHEEL", bg=PANEL, fg=ACCENT,
                 font=("Courier", 13, "bold")).pack(side="left", padx=18)
        tk.Label(hdr, text="●", bg=PANEL, fg=GREEN,
                 font=("Courier", 14)).pack(side="right", padx=6)
        tk.Label(hdr, text="ACTIVE", bg=PANEL, fg=GREEN,
                 font=("Courier", 9, "bold")).pack(side="right")
        tk.Frame(self.root, bg=ACCENT, height=1).pack(fill="x")

        # Bindings summary
        binds = tk.Frame(self.root, bg=CARD, pady=8, padx=18)
        binds.pack(fill="x")
        for (k, desc), flag in zip(
            [("Z", "→  paste next"), ("X", "→  Enter"), ("C", "→  Left Click")],
            [REBIND_Z_TO_PASTE, REBIND_X_TO_ENTER, REBIND_C_TO_CLICK]
        ):
            row = tk.Frame(binds, bg=CARD); row.pack(fill="x", pady=1)
            tk.Label(row, text=f"  {k:<8}", bg=CARD,
                     fg=ACCENT if flag else MUTED,
                     font=("Courier", 10, "bold"), anchor="w").pack(side="left")
            tk.Label(row, text=desc, bg=CARD,
                     fg=FG if flag else MUTED,
                     font=("Courier", 10), anchor="w").pack(side="left")
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # Queue
        tk.Label(self.root, text="  MESSAGE QUEUE", bg=DARK, fg=MUTED,
                 font=("Courier", 9, "bold"), anchor="w").pack(fill="x", padx=18, pady=(12, 4))
        qf = tk.Frame(self.root, bg=DARK); qf.pack(fill="x", padx=14)

        self.msg_rows = []
        for i, m in enumerate(MESSAGES):
            bg = CARD if i % 2 == 0 else PANEL
            row = tk.Frame(qf, bg=bg, pady=6, padx=12); row.pack(fill="x", pady=1)
            ptr = tk.Label(row, text="▶", bg=bg, fg=ACCENT,
                           font=("Courier", 10, "bold"), width=2); ptr.pack(side="left")
            txt = tk.Label(row, text=m["text"], bg=bg, fg=FG,
                           font=("Courier", 12, "bold"), anchor="w", width=12); txt.pack(side="left")
            tk.Label(row, text=f"cd {m['cooldown']}s", bg=bg, fg=MUTED,
                     font=("Courier", 9)).pack(side="left", padx=6)
            badge = tk.Label(row, text="READY", bg=GREEN, fg=DARK,
                             font=("Courier", 8, "bold"), padx=5, pady=1); badge.pack(side="right")
            bar = tk.Canvas(row, bg=bg, height=4, highlightthickness=0, width=80); bar.pack(side="right", padx=8)
            self.msg_rows.append({"ptr": ptr, "txt": txt, "badge": badge, "bar": bar, "bg": bg})

        # Log
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", pady=(12, 0))
        tk.Label(self.root, text="  LOG", bg=DARK, fg=MUTED,
                 font=("Courier", 9, "bold"), anchor="w").pack(fill="x", padx=18, pady=(6, 2))
        self.log_text = tk.Text(self.root, bg=PANEL, fg=MUTED, font=("Courier", 9),
                                relief="flat", state="disabled", wrap="word",
                                height=8, padx=12, pady=8)
        self.log_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log_text.tag_config("ok",   foreground=GREEN)
        self.log_text.tag_config("warn", foreground=AMBER)
        self.log_text.tag_config("time", foreground=MUTED)
        self._schedule_refresh()

    def refresh(self):
        now = time.time()
        for i, (m, row) in enumerate(zip(MESSAGES, self.msg_rows)):
            remaining = m["cooldown"] - (now - last_used.get(m["text"], 0))
            on_cd     = remaining > 0
            bg        = row["bg"]

            row["ptr"].config(text="▶" if i == current_index else " ",
                              fg=ACCENT if i == current_index else bg)
            if on_cd:
                pct = remaining / m["cooldown"]
                row["badge"].config(text=f"{remaining:.1f}s", bg=AMBER, fg=DARK)
                row["txt"].config(fg=MUTED)
                row["bar"].delete("all")
                row["bar"].create_rectangle(0, 0, 80, 4, fill=BORDER, outline="")
                row["bar"].create_rectangle(0, 0, int(80*pct), 4, fill=AMBER, outline="")
            else:
                row["badge"].config(text="READY", bg=GREEN, fg=DARK)
                row["txt"].config(fg=FG)
                row["bar"].delete("all")
                row["bar"].create_rectangle(0, 0, 80, 4, fill=GREEN, outline="")

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        for entry in log_entries[:20]:
            parts = entry.split("  ", 1)
            if len(parts) == 2:
                ts, body = parts
                self.log_text.insert("end", ts + "  ", "time")
                tag = "ok" if body.startswith("ok") else "warn"
                # strip the prefix before display
                display = body[4:] if body.startswith(("ok  ", "cd  ")) else body
                self.log_text.insert("end", ("✓  " if tag == "ok" else "⏳ ") + display + "\n", tag)
            else:
                self.log_text.insert("end", entry + "\n")
        self.log_text.config(state="disabled")

    def _schedule_refresh(self):
        self.refresh()
        self.root.after(100, self._schedule_refresh)

    def run(self):
        self.root.mainloop()
        
        
#  ENTRY POINT

def main():
    global _gui
    
    keyboard.hook(on_key, suppress=True)

    _gui = PasteWheelGUI()
    _gui.run()

    keyboard.unhook_all()
    

if __name__ == "__main__":
    main()
