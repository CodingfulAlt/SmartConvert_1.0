# smartconvert_app.py - main settings window

import sys
import os
import subprocess
import json
import ctypes
import ctypes.wintypes
import threading
import urllib.request
import zipfile
import shutil
import logging
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

if getattr(sys, 'frozen', False):
    BASE = Path(sys.executable).parent
else:
    BASE = Path(__file__).parent

BIN_DIR    = BASE / "bin"
DATA_DIR   = BASE / "data"
FFMPEG_DIR = DATA_DIR / "ffmpeg"
FFMPEG_EXE = FFMPEG_DIR / "ffmpeg.exe"
CONFIG_DIR = BASE / "config"
STATE_FILE = CONFIG_DIR / "state.json"
LOG_DIR    = BASE / "logs"
LOG_FILE   = LOG_DIR / "app.log"
REG_EXE    = BIN_DIR / "registry_manager.exe"

for d in [BIN_DIR, DATA_DIR, FFMPEG_DIR, CONFIG_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(filename=str(LOG_FILE), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sc")

def load_state():
    try: return json.loads(STATE_FILE.read_text())
    except: return {"installed": False, "enabled": True}

def save_state(s):
    try: STATE_FILE.write_text(json.dumps(s, indent=2))
    except Exception as e: log.error("save_state: %s", e)

MUTEX_NAME = "Global\\SmartConvert_v4"
WM_SHOW    = 0x8000 + 1

def try_mutex():
    h = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
    return h, ctypes.windll.kernel32.GetLastError() != 183

def signal_existing():
    ctypes.windll.user32.PostMessageW(0xFFFF, WM_SHOW, 0, 0)

FFMPEG_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)

def download_ffmpeg(cb=None):
    if FFMPEG_EXE.exists():
        log.info("ffmpeg OK")
        return True
    try:
        if cb: cb("Сваляне на ffmpeg (~40 MB)...")
        tmp = DATA_DIR / "_ffmpeg.zip"
        req = urllib.request.Request(FFMPEG_URL, headers={"User-Agent": "SmartConvert/4"})
        with urllib.request.urlopen(req, timeout=120) as r:
            total = int(r.headers.get("Content-Length", 0))
            done  = 0
            with open(tmp, "wb") as f:
                while True:
                    buf = r.read(65536)
                    if not buf: break
                    f.write(buf)
                    done += len(buf)
                    if cb and total: cb(f"ffmpeg  {done/total*100:.0f}%")
        with zipfile.ZipFile(tmp) as z:
            for name in z.namelist():
                if name.endswith("bin/ffmpeg.exe"):
                    with z.open(name) as src, open(FFMPEG_EXE, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    break
        tmp.unlink(missing_ok=True)
        log.info("ffmpeg OK")
        return True
    except Exception as e:
        log.error("ffmpeg failed: %s", e)
        return False

def run_registry(action):
    if not REG_EXE.exists():
        messagebox.showerror("Грешка", f"registry_manager.exe не е намерен в:\n{BIN_DIR}")
        return
    ctypes.windll.shell32.ShellExecuteW(None, "runas", str(REG_EXE), action, None, 1)

# Colors
BG      = "#0d0d14"
SURFACE = "#13131f"
CARD    = "#1a1a2e"
BORDER  = "#2a2a45"
GREEN   = "#22c55e"
RED     = "#ef4444"
YELLOW  = "#eab308"
BLUE    = "#3b82f6"
FG      = "#f1f5f9"
MUTED   = "#64748b"
SUBTLE  = "#334155"
FONT    = "Segoe UI"


class ToggleSwitch(tk.Canvas):
    """Modern iOS-style toggle switch."""
    def __init__(self, parent, variable, command=None, **kw):
        super().__init__(parent, width=52, height=28,
                         bg=parent["bg"], highlightthickness=0, **kw)
        self._var = variable
        self._cmd = command
        self._draw()
        self.bind("<Button-1>", self._click)
        variable.trace_add("write", lambda *a: self._draw())

    def _draw(self):
        self.delete("all")
        on = self._var.get()
        w, h, r = 52, 28, 14
        # Track
        color = GREEN if on else SUBTLE
        self.create_arc(0, 0, 2*r, 2*r, start=90,  extent=180, fill=color, outline=color)
        self.create_arc(w-2*r, 0, w, 2*r, start=270, extent=180, fill=color, outline=color)
        self.create_rectangle(r, 0, w-r, h, fill=color, outline=color)
        # Thumb
        pad = 3
        cx = w - r - pad if on else r + pad
        self.create_oval(cx-r+pad, pad, cx+r-pad, h-pad, fill="white", outline="white")

    def _click(self, e):
        self._var.set(not self._var.get())
        if self._cmd: self._cmd()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self._mutex, is_first = try_mutex()
        if not is_first:
            signal_existing()
            self.destroy()
            sys.exit(0)

        self.state = load_state()
        self._build_ui()
        self._poll_wm()

        if not FFMPEG_EXE.exists():
            self.after(300, self._first_run)
        else:
            # ffmpeg already here (installed by installer)
            if not self.state.get("installed"):
                self.after(300, self._install_registry)
            else:
                self.after(300, lambda: self._set_status("Готов", GREEN))

    def _build_ui(self):
        self.title("SmartConvert")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        w, h = 420, 440
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Header
        hdr = tk.Frame(self, bg=SURFACE, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        left = tk.Frame(hdr, bg=SURFACE)
        left.pack(side="left", padx=22, pady=12)
        tk.Label(left, text="SmartConvert",
                 font=(FONT, 18, "bold"), bg=SURFACE, fg=FG).pack(anchor="w")
        tk.Label(left, text="File Converter  ·  v1.0",
                 font=(FONT, 8), bg=SURFACE, fg=MUTED).pack(anchor="w")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=14)

        # Status
        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(body, textvariable=self._status_var,
                 font=(FONT, 9), bg=BG, fg=YELLOW, wraplength=380, justify="left")
        self._status_lbl.pack(anchor="w", pady=(0, 6))

        # Progress bar
        self._pbar_frame = tk.Frame(body, bg=BG)
        self._pbar_bg    = tk.Frame(self._pbar_frame, bg=CARD, height=4)
        self._pbar_fill  = tk.Frame(self._pbar_bg, bg=BLUE, height=4, width=0)
        self._pbar_fill.place(x=0, y=0, height=4)
        self._pbar_animating = False

        # Toggle card
        card = tk.Frame(body, bg=CARD, highlightbackground=BORDER,
                        highlightthickness=1)
        card.pack(fill="x", pady=8)
        inner = tk.Frame(card, bg=CARD)
        inner.pack(padx=18, pady=16, fill="x")

        tk.Label(inner, text="Контекстно меню",
                 font=(FONT, 12), bg=CARD, fg=FG).pack(side="left")

        self._enabled = tk.BooleanVar(value=self.state.get("enabled", True))
        toggle = ToggleSwitch(inner, self._enabled, command=self._toggle)
        toggle.pack(side="right")

        # Status text under toggle
        self._toggle_lbl = tk.Label(card,
                 text="Активно" if self._enabled.get() else "Изключено",
                 font=(FONT, 8), bg=CARD, fg=GREEN if self._enabled.get() else MUTED)
        self._toggle_lbl.pack(pady=(0, 10))

        # Folder path
        path_card = tk.Frame(body, bg=CARD, highlightbackground=BORDER,
                             highlightthickness=1)
        path_card.pack(fill="x", pady=(4, 0))
        tk.Label(path_card, text=f"📁  {BASE}",
                 font=(FONT, 8), bg=CARD, fg=MUTED,
                 wraplength=370).pack(padx=12, pady=8, anchor="w")

        # Supported formats info
        formats_card = tk.Frame(body, bg=CARD, highlightbackground=BORDER,
                                highlightthickness=1)
        formats_card.pack(fill="x", pady=(4, 0))

        formats_hdr = tk.Frame(formats_card, bg=CARD)
        formats_hdr.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(formats_hdr, text="Поддържани формати",
                 font=(FONT, 8, "bold"), bg=CARD, fg=MUTED).pack(side="left")

        formats_body = tk.Frame(formats_card, bg=CARD)
        formats_body.pack(fill="x", padx=12, pady=(0, 8))

        FORMATS = [
            ("🖼", "Изображения",  "HEIC  PNG  JPG  JPEG  WebP  BMP  TIFF"),
            ("🎵", "Аудио",        "MP3  WAV  FLAC  AAC  OGG  M4A"),
            ("📄", "Текст / Код",  "TXT  PY  BAT  JSON  MD"),
        ]
        for icon, label, exts in FORMATS:
            row = tk.Frame(formats_body, bg=CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=icon, font=(FONT, 11), bg=CARD).pack(side="left")
            tk.Label(row, text=label,
                     font=(FONT, 9, "bold"), bg=CARD, fg=FG,
                     width=14, anchor="w").pack(side="left", padx=(4, 0))
            tk.Label(row, text=exts,
                     font=(FONT, 8), bg=CARD, fg=MUTED).pack(side="left")

        # Uninstall
        lnk = tk.Label(body, text="Деинсталирай SmartConvert",
                       font=(FONT, 8, "underline"), bg=BG, fg=RED, cursor="hand2")
        lnk.pack(pady=(10, 0))
        lnk.bind("<Button-1>", lambda e: self._open_uninstaller())

    def _poll_wm(self):
        msg = ctypes.wintypes.MSG()
        if ctypes.windll.user32.PeekMessageW(
                ctypes.byref(msg), None, WM_SHOW, WM_SHOW, 1):
            self.deiconify(); self.lift(); self.focus_force()
        self.after(500, self._poll_wm)

    def _animate_pbar(self):
        if not self._pbar_animating: return
        self._pbar_bg.update_idletasks()
        w = self._pbar_bg.winfo_width()
        cur = getattr(self, "_pbar_pos", 0)
        seg = w // 3
        self._pbar_fill.place(x=cur % w, y=0, height=4, width=seg)
        self._pbar_pos = (cur + 8) % w
        self.after(30, self._animate_pbar)

    def _start_pbar(self):
        self._pbar_frame.pack(fill="x", pady=(0, 6))
        self._pbar_bg.pack(fill="x")
        self._pbar_animating = True
        self._animate_pbar()

    def _stop_pbar(self):
        self._pbar_animating = False
        self._pbar_frame.pack_forget()

    def _toggle(self):
        on = self._enabled.get()
        self.state["enabled"] = on
        save_state(self.state)
        run_registry("install" if on else "uninstall")
        self._toggle_lbl.configure(
            text="Активно" if on else "Изключено",
            fg=GREEN if on else MUTED)
        self._set_status(
            "Контекстното меню е " + ("включено ✓" if on else "изключено"),
            GREEN if on else MUTED)

    def _first_run(self):
        self._set_status("Сваляне на ffmpeg...", YELLOW)
        self._start_pbar()

        def _cb(txt): self.after(0, lambda: self._set_status(txt, YELLOW))
        def _done(ok):
            def _ui():
                self._stop_pbar()
                if ok: self._install_registry()
                else: self._set_status("Грешка при сваляне. Виж logs/app.log", RED)
            self.after(0, _ui)

        threading.Thread(target=lambda: _done(download_ffmpeg(_cb)), daemon=True).start()

    def _install_registry(self):
        run_registry("install")
        self.state["installed"] = True
        save_state(self.state)
        self._set_status("Готово! Десен клик на файл → Convert", GREEN)

    def _set_status(self, txt, color=YELLOW):
        self._status_var.set(txt)
        self._status_lbl.configure(fg=color)

    def _open_uninstaller(self):
        exe = BASE / "uninstall.exe"
        if exe.exists(): subprocess.Popen([str(exe)])
        else: messagebox.showerror("Грешка", f"uninstall.exe не е намерен в:\n{BASE}")


if __name__ == "__main__":
    try:
        app = App()
        if app.winfo_exists():
            app.mainloop()
    except SystemExit:
        pass
    except Exception as e:
        log.exception("CRASH: %s", e)
        try:
            import tkinter.messagebox as mb
            mb.showerror("SmartConvert", str(e))
        except: pass
