"""
INSTALLER.py - SmartConvert Installer
Place this file next to the src/ folder and run with: python INSTALLER.py
"""

import sys
import os
import subprocess
import threading
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog

if getattr(sys, 'frozen', False):
    BASE = Path(sys.executable).parent
else:
    BASE = Path(__file__).parent

SRC_DIR = BASE / "src"

FONT = "Segoe UI"
MONO = "Consolas"

BG      = "#0d0d14"
SURFACE = "#13131f"
CARD    = "#1a1a2e"
BORDER  = "#2a2a45"
GREEN   = "#22c55e"
GREEN_D = "#16a34a"
RED     = "#ef4444"
YELLOW  = "#eab308"
BLUE    = "#3b82f6"
BLUE_H  = "#2563eb"
FG      = "#f1f5f9"
MUTED   = "#64748b"
SUBTLE  = "#334155"

STEPS = [
    ("🐍", "Проверка на Python"),
    ("📦", "Инсталиране на PyInstaller + Pillow"),
    ("⚙️",  "Билдване на smartconvert.exe"),
    ("🔄", "Билдване на converter.exe"),
    ("🔑", "Билдване на registry_manager.exe"),
    ("🗑️",  "Билдване на uninstall.exe"),
    ("📁", "Организиране на файловете"),
    ("🎬", "Сваляне на ffmpeg"),
    ("✨", "Почистване"),
]


class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SmartConvert – Installer")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._done    = False
        self._icons   = []
        self._labels  = []
        self._dot_job = None
        self._out_dir = tk.StringVar(value=str(BASE / "SmartConvert"))
        self._build_ui()
        w, h = 600, 620
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.lift()
        self.focus_force()

    def _on_close(self):
        if not self._done:
            if messagebox.askyesno("Прекъсване", "Да се спре инсталацията?"):
                self.destroy()
        else:
            self.destroy()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=SURFACE, height=80)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        left = tk.Frame(hdr, bg=SURFACE)
        left.pack(side="left", padx=28, pady=16)
        tk.Label(left, text="SmartConvert",
                 font=(FONT, 24, "bold"), bg=SURFACE, fg=FG).pack(anchor="w")
        tk.Label(left, text="File Converter  ·  Installer v1.0",
                 font=(FONT, 9), bg=SURFACE, fg=MUTED).pack(anchor="w")

        # Install path picker
        pf = tk.Frame(self, bg=BG)
        pf.pack(fill="x", padx=24, pady=(16, 4))
        tk.Label(pf, text="ПАПКА ЗА ИНСТАЛАЦИЯ",
                 font=(FONT, 7, "bold"), bg=BG, fg=MUTED).pack(anchor="w")

        path_row = tk.Frame(pf, bg=CARD, highlightbackground=BORDER,
                            highlightthickness=1)
        path_row.pack(fill="x", pady=(4, 0))

        tk.Label(path_row, text="📁", font=(FONT, 11),
                 bg=CARD, fg=MUTED).pack(side="left", padx=(10, 4), pady=8)

        path_entry = tk.Entry(path_row, textvariable=self._out_dir,
                              font=(MONO, 9), bg=CARD, fg=FG,
                              insertbackground=FG, relief="flat",
                              highlightthickness=0)
        path_entry.pack(side="left", fill="x", expand=True, pady=8)

        browse_btn = tk.Button(path_row, text="Промени",
                               font=(FONT, 8), bg=BORDER, fg=FG,
                               activebackground=SUBTLE, activeforeground=FG,
                               relief="flat", cursor="hand2", padx=10, pady=4,
                               command=self._browse)
        browse_btn.pack(side="right", padx=8, pady=4)

        # Steps
        tk.Label(self, text="СТЪПКИ",
                 font=(FONT, 7, "bold"), bg=BG, fg=MUTED).pack(
                 anchor="w", padx=24, pady=(12, 4))

        steps_card = tk.Frame(self, bg=CARD, highlightbackground=BORDER,
                              highlightthickness=1)
        steps_card.pack(fill="x", padx=24)

        for i, (emoji, label) in enumerate(STEPS):
            row = tk.Frame(steps_card, bg=CARD)
            row.pack(fill="x", padx=12, pady=4)

            dot = tk.Label(row, text="●", font=(FONT, 10),
                           bg=CARD, fg=BORDER, width=2)
            dot.pack(side="left")

            tk.Label(row, text=emoji, font=(FONT, 11),
                     bg=CARD).pack(side="left", padx=(2, 6))

            lbl = tk.Label(row, text=label, font=(FONT, 10),
                           bg=CARD, fg=SUBTLE, anchor="w")
            lbl.pack(side="left", fill="x", expand=True)

            self._icons.append(dot)
            self._labels.append(lbl)

            if i < len(STEPS) - 1:
                tk.Frame(steps_card, bg=BORDER, height=1).pack(fill="x", padx=12)

        # Status
        self._status_var = tk.StringVar(value="Готов за инсталация")
        tk.Label(self, textvariable=self._status_var,
                 font=(FONT, 9), bg=BG, fg=MUTED,
                 wraplength=550, justify="left").pack(
                 padx=24, pady=(10, 0), anchor="w")

        # Progress bar
        prog_frame = tk.Frame(self, bg=BG)
        prog_frame.pack(fill="x", padx=24, pady=(6, 0))
        self._prog_bg = tk.Frame(prog_frame, bg=CARD, height=4)
        self._prog_bg.pack(fill="x")
        self._prog_fill = tk.Frame(self._prog_bg, bg=BLUE, height=4, width=0)
        self._prog_fill.place(x=0, y=0, height=4)

        # Bottom
        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=24, pady=16)

        # Checkbox (hidden until done)
        self._open_var  = tk.BooleanVar(value=True)
        self._chk_frame = tk.Frame(bottom, bg=BG)
        self._chk = tk.Checkbutton(
            self._chk_frame,
            text="Отвори SmartConvert след затваряне",
            variable=self._open_var,
            font=(FONT, 10), bg=BG, fg=FG,
            activebackground=BG, activeforeground=FG,
            selectcolor=CARD, relief="flat", cursor="hand2",
        )
        self._chk.pack(side="left")

        # Install button
        self._btn_frame = tk.Frame(bottom, bg=BG)
        self._btn_frame.pack(side="right")
        self._install_btn = tk.Button(
            self._btn_frame,
            text="  Инсталирай  ",
            font=(FONT, 11, "bold"),
            bg=BLUE, fg=FG,
            activebackground=BLUE_H, activeforeground=FG,
            relief="flat", cursor="hand2",
            padx=18, pady=9, bd=0,
            command=self._start,
        )
        self._install_btn.pack()

    def _browse(self):
        chosen = filedialog.askdirectory(
            title="Избери папка за инсталация",
            initialdir=str(Path(self._out_dir.get()).parent),
        )
        if chosen:
            self._out_dir.set(str(Path(chosen) / "SmartConvert"))

    def _set_step(self, i, state):
        dot = self._icons[i]
        lbl = self._labels[i]
        if state == "running":
            dot.configure(fg=YELLOW)
            lbl.configure(fg=FG, font=(FONT, 10))
        elif state == "done":
            dot.configure(fg=GREEN)
            lbl.configure(fg=GREEN, font=(FONT, 10))
        elif state == "error":
            dot.configure(fg=RED)
            lbl.configure(fg=RED, font=(FONT, 10))

    def _set_progress(self, fraction):
        self._prog_bg.update_idletasks()
        total_w = self._prog_bg.winfo_width()
        fill_w  = int(total_w * max(0.0, min(1.0, fraction)))
        self._prog_fill.place(x=0, y=0, height=4, width=fill_w)

    def _dots_start(self, base):
        self._dot_base = base
        self._dot_n    = 0
        self._dots_tick()

    def _dots_tick(self):
        dots = "·" * (self._dot_n % 4)
        self._status_var.set(self._dot_base + dots)
        self._dot_n  += 1
        self._dot_job = self.after(350, self._dots_tick)

    def _dots_stop(self):
        if self._dot_job:
            self.after_cancel(self._dot_job)
            self._dot_job = None

    def _start(self):
        out_dir = Path(self._out_dir.get())
        if not SRC_DIR.exists():
            messagebox.showerror("Грешка",
                f"Папката 'src' не е намерена до INSTALLER.py!\n"
                f"Очаква се: {SRC_DIR}")
            return
        self._install_btn.configure(state="disabled", bg=SUBTLE,
                                    text="  Работи...  ")
        threading.Thread(target=self._run, args=(out_dir,), daemon=True).start()

    def _run(self, out_dir: Path):
        dist  = BASE / "_dist"
        build = BASE / "_build"
        dist.mkdir(exist_ok=True)
        total = len(STEPS)

        def step_start(i, msg):
            self.after(0, lambda: self._set_step(i, "running"))
            self.after(0, lambda: self._set_progress(i / total))
            self._dots_start(msg)

        def step_done(i):
            self.after(0, lambda: self._set_step(i, "done"))
            self.after(0, lambda: self._set_progress((i + 1) / total))

        # 0: Python check
        step_start(0, "Проверка на Python")
        subprocess.run([sys.executable, "--version"], capture_output=True)
        step_done(0)

        # 1: pip install
        step_start(1, "Инсталиране на PyInstaller + Pillow")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "pyinstaller", "Pillow", "pillow-heif",
             "--quiet", "--disable-pip-version-check"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if r.returncode != 0:
            self.after(0, lambda: self._set_step(1, "error"))
            self._fail("pip install се провали:\n" + r.stderr[-300:])
            return
        step_done(1)

        # 2-5: build exes
        # Check if PIL is available for --collect-all
        pil_check = subprocess.run(
            [sys.executable, "-c", "import PIL"],
            capture_output=True
        )
        pil_available = pil_check.returncode == 0

        converter_extra = []
        if pil_available:
            converter_extra = ["--collect-all", "PIL", "--collect-all", "pillow_heif"]

        scripts = [
            ("smartconvert_app.py", "smartconvert",     [],                False, 2),
            ("converter.py",        "converter",         converter_extra,   False, 3),
            ("registry_manager.py", "registry_manager", [],                True,  4),
            ("uninstall.py",        "uninstall",         [],                False, 5),
        ]
        for script, name, extra, uac, si in scripts:
            step_start(si, f"Билдване на {name}.exe")
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onefile", "--noconsole",
                "--name", name,
                "--distpath", str(dist),
                "--workpath", str(build),
                "--specpath", str(build),
            ] + extra + [str(SRC_DIR / script)]
            if uac:
                cmd.insert(4, "--uac-admin")
            r = subprocess.run(cmd, capture_output=True, text=True,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            if r.returncode != 0:
                self.after(0, lambda s=si: self._set_step(s, "error"))
                err_detail = r.stdout[-500:] + r.stderr[-500:]
                self._fail(f"Build {name}.exe се провали:\n{err_detail[-400:]}")
                return
            step_done(si)

        # 6: organize
        step_start(6, "Организиране на файловете")
        try:
            for sub in ["bin", "data/ffmpeg", "config", "logs", "docs"]:
                (out_dir / sub).mkdir(parents=True, exist_ok=True)
            shutil.copy(dist / "smartconvert.exe",     out_dir / "smartconvert.exe")
            shutil.copy(dist / "uninstall.exe",        out_dir / "uninstall.exe")
            shutil.copy(dist / "converter.exe",        out_dir / "bin" / "converter.exe")
            shutil.copy(dist / "registry_manager.exe", out_dir / "bin" / "registry_manager.exe")
            if (SRC_DIR / "README.md").exists():
                shutil.copy(SRC_DIR / "README.md", out_dir / "docs" / "README.md")
            step_done(6)
        except Exception as e:
            self.after(0, lambda: self._set_step(6, "error"))
            self._fail(str(e))
            return

        # 7: download ffmpeg into output folder
        step_start(7, "Сваляне на ffmpeg")
        try:
            import urllib.request, zipfile, shutil as _sh
            ffmpeg_dir = out_dir / "data" / "ffmpeg"
            ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"
            ffmpeg_dir.mkdir(parents=True, exist_ok=True)
            if not ffmpeg_exe.exists():
                FFMPEG_URL = (
                    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
                    "ffmpeg-master-latest-win64-gpl.zip"
                )
                self.after(0, lambda: self._status_var.set("Сваляне на ffmpeg (~40 MB)..."))
                tmp = out_dir / "data" / "_ffmpeg.zip"
                req = urllib.request.Request(FFMPEG_URL,
                      headers={"User-Agent": "SmartConvert/installer"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    total = int(r.headers.get("Content-Length", 0))
                    done  = 0
                    with open(tmp, "wb") as f:
                        while True:
                            buf = r.read(65536)
                            if not buf: break
                            f.write(buf)
                            done += len(buf)
                            if total:
                                pct = done / total * 100
                                self.after(0, lambda p=pct: self._status_var.set(
                                    f"Сваляне на ffmpeg  {p:.0f}%"))
                with zipfile.ZipFile(tmp) as z:
                    for name in z.namelist():
                        if name.endswith("bin/ffmpeg.exe"):
                            with z.open(name) as src, open(ffmpeg_exe, "wb") as dst:
                                _sh.copyfileobj(src, dst)
                            break
                tmp.unlink(missing_ok=True)
            step_done(7)
        except Exception as e:
            # ffmpeg download failed - not critical, app will retry on first run
            self.after(0, lambda: self._set_step(7, "error"))
            self.after(0, lambda: self._status_var.set(
                f"ffmpeg не се свали ({e}) - ще се опита при стартиране на приложението"))
            import time; time.sleep(2)

        # 8: cleanup
        step_start(8, "Почистване")
        shutil.rmtree(dist,  ignore_errors=True)
        shutil.rmtree(build, ignore_errors=True)
        # Remove src\ and INSTALLER itself
        shutil.rmtree(SRC_DIR, ignore_errors=True)
        step_done(8)
        self._finish_ok(out_dir)

    def _finish_ok(self, out_dir):
        self._dots_stop()
        self._done = True
        def _ui():
            self._set_progress(1.0)
            self._prog_fill.configure(bg=GREEN)
            self._status_var.set("✓ Инсталацията завърши успешно!")
            self._chk_frame.pack(side="left")
            self._install_btn.configure(
                state="normal", bg=GREEN,
                activebackground=GREEN_D,
                text="  Затвори  ",
                command=lambda: self._close_action(out_dir),
            )
            self._self_delete()
        self.after(0, _ui)

    def _close_action(self, out_dir):
        if self._open_var.get():
            exe = out_dir / "smartconvert.exe"
            if exe.exists():
                subprocess.Popen([str(exe)])
        self.destroy()

    def _self_delete(self):
        me = Path(sys.executable) if getattr(sys, 'frozen', False) else Path(__file__)
        try:
            if getattr(sys, 'frozen', False) and me.exists():
                subprocess.Popen(
                    f'ping 127.0.0.1 -n 3 > nul & del /f /q "{me}"',
                    shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            elif me.exists():
                me.unlink(missing_ok=True)
        except Exception:
            pass

    def _fail(self, msg):
        self._dots_stop()
        def _ui():
            self._status_var.set(f"✗ Грешка: {msg}")
            self._install_btn.configure(
                state="normal", bg=RED,
                activebackground=RED,
                text="  Затвори  ",
                command=self.destroy,
            )
        self.after(0, _ui)


if __name__ == "__main__":
    try:
        app = Installer()
        app.mainloop()
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        try:
            open(BASE / "INSTALLER_ERROR.txt", "w").write(err)
        except Exception:
            pass
        try:
            import tkinter.messagebox as mb
            mb.showerror("Installer Error", err[:600])
        except Exception:
            pass
