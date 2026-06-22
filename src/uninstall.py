"""
uninstall.exe  -  SmartConvert Uninstaller
1. Маха context menu (registry)
2. Изтрива цялата папка на програмата
3. Самоизтрива се
"""

import sys
import ctypes
import subprocess
import shutil
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

if getattr(sys, 'frozen', False):
    BASE = Path(sys.executable).parent
else:
    BASE = Path(__file__).parent

REG_EXE = BASE / "bin" / "registry_manager.exe"

BG      = "#0f0f1a"
SURFACE = "#1e1f2e"
CARD    = "#2a2b3d"
GREEN   = "#4ade80"
RED     = "#f87171"
YELLOW  = "#fbbf24"
FG      = "#e2e8f0"
MUTED   = "#94a3b8"
FONT    = "Segoe UI"


class Uninstaller(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SmartConvert - Деинсталация")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._build_ui()
        w, h = 480, 320
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg="#2a0a0a", height=68)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="SmartConvert - Деинсталация",
                 font=(FONT, 15, "bold"), bg="#2a0a0a", fg=RED).pack(
                 padx=22, pady=18, anchor="w")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=22, pady=16)

        tk.Label(body,
                 text="Следното ще бъде премахнато напълно:\n"
                      "  • Контекстното меню от Windows\n"
                      "  • Цялата папка на програмата и всички файлове в нея",
                 font=(FONT, 10), bg=BG, fg=FG, justify="left").pack(anchor="w")

        # Path card
        pc = tk.Frame(body, bg=CARD)
        pc.pack(fill="x", pady=(12, 0))
        tk.Label(pc, text="Папка за изтриване:",
                 font=(FONT, 9), bg=CARD, fg=MUTED).pack(
                 anchor="w", padx=12, pady=(8, 0))
        tk.Label(pc, text=str(BASE),
                 font=(FONT, 9, "bold"), bg=CARD, fg=FG).pack(
                 anchor="w", padx=12, pady=(0, 8))

        self._status = tk.StringVar(value="")
        tk.Label(body, textvariable=self._status,
                 font=(FONT, 9), bg=BG, fg=YELLOW).pack(pady=(10, 0))

        # Buttons
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(pady=(0, 18))

        tk.Button(btn_row, text="  Откажи  ",
                  font=(FONT, 11), bg=CARD, fg=FG,
                  relief="flat", cursor="hand2",
                  padx=14, pady=7,
                  command=self.destroy).pack(side="left", padx=10)

        tk.Button(btn_row, text="  Деинсталирай напълно  ",
                  font=(FONT, 11, "bold"), bg=RED, fg=BG,
                  relief="flat", cursor="hand2",
                  padx=14, pady=7,
                  command=self._confirm).pack(side="left", padx=10)

    def _confirm(self):
        if not messagebox.askyesno(
            "Потвърждение",
            f"Сигурен ли си?\n\nЩе бъде изтрита цялата папка:\n{BASE}\n\n"
            "Това не може да се отмени!"
        ):
            return
        self._do_uninstall()

    def _do_uninstall(self):
        self._status.set("Премахване на контекстното меню...")
        self.update()

        # Step 1: Remove registry entries (needs admin)
        if REG_EXE.exists():
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", str(REG_EXE), "uninstall", None, 1
            )
            import time
            time.sleep(2)  # wait for UAC + registry write

        self._status.set("Изтриване на файловете...")
        self.update()

        # Step 2: Delete entire folder via cmd after we exit
        # Use a bat script that waits for our process to exit then deletes
        bat = Path(os.environ.get("TEMP", "C:\\Windows\\Temp")) / "_sc_uninstall.bat"
        folder = str(BASE)
        bat_content = f"""@echo off
ping 127.0.0.1 -n 4 > nul
rd /s /q "{folder}"
del /f /q "%~f0"
"""
        bat.write_text(bat_content, encoding="ascii")

        # Launch the bat hidden
        subprocess.Popen(
            ["cmd", "/c", str(bat)],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )

        # Step 3: Close and exit - bat will delete everything after we close
        self.destroy()
        sys.exit(0)


if __name__ == "__main__":
    app = Uninstaller()
    app.mainloop()
