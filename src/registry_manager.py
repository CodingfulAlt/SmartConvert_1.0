"""
bin\registry_manager.exe
Needs admin (UAC). Usage: registry_manager.exe install|uninstall
"""

import sys
import winreg
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE = Path(sys.executable).parent.parent   # bin\ -> SmartConvert\
else:
    BASE = Path(__file__).parent

CONV_EXE = BASE / "bin" / "converter.exe"
ROOT     = winreg.HKEY_CLASSES_ROOT
APP      = "SmartConvert"

IMAGE_ALL = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]
AUDIO_MAP = {
    ".mp3":  [".wav", ".flac", ".aac", ".ogg"],
    ".wav":  [".mp3", ".flac", ".aac", ".ogg"],
    ".aac":  [".mp3", ".wav",  ".flac", ".ogg"],
    ".flac": [".mp3", ".wav",  ".aac",  ".ogg"],
    ".ogg":  [".mp3", ".wav",  ".flac", ".aac"],
    ".m4a":  [".mp3", ".wav",  ".flac", ".aac", ".ogg"],
}
TEXT_ALL = [".txt", ".bat", ".py", ".json", ".md"]


def build_entries():
    e = []
    e.append((".heic", [(f"Convert to {t.lstrip('.').upper()}", t) for t in IMAGE_ALL]))
    for ext in IMAGE_ALL:
        e.append((ext, [(f"Convert to {t.lstrip('.').upper()}", t)
                        for t in IMAGE_ALL if t != ext]))
    for ext, tgts in AUDIO_MAP.items():
        e.append((ext, [(f"Convert to {t.lstrip('.').upper()}", t) for t in tgts]))
    for ext in TEXT_ALL:
        e.append((ext, [(f"Convert to {t}", t) for t in TEXT_ALL if t != ext]))
    return e


def _create(path):
    return winreg.CreateKeyEx(ROOT, path, 0, winreg.KEY_ALL_ACCESS)

def _set(key, name, value):
    winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

def _del_tree(path):
    try:
        key = winreg.OpenKey(ROOT, path, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        return
    while True:
        try:
            child = winreg.EnumKey(key, 0)
            _del_tree(f"{path}\\{child}")
        except OSError:
            break
    winreg.CloseKey(key)
    parent, _, name = path.rpartition("\\")
    try:
        pk = winreg.OpenKey(ROOT, parent, 0, winreg.KEY_ALL_ACCESS)
        winreg.DeleteKey(pk, name)
        winreg.CloseKey(pk)
    except Exception:
        pass


def install():
    conv = str(CONV_EXE)
    for ext, opts in build_entries():
        # Parent "Convert" entry
        parent = f"SystemFileAssociations\\{ext}\\shell\\{APP}"
        with _create(parent) as pk:
            _set(pk, "MUIVerb",     "Convert")
            _set(pk, "SubCommands", "")
            _set(pk, "Icon",        conv)

        # Sub-items under parent\shell\
        shell = f"{parent}\\shell"
        for label, tgt in opts:
            item = f"{shell}\\{APP}_{tgt.lstrip('.')}"
            with _create(item) as ik:
                _set(ik, "MUIVerb", label)
            with _create(f"{item}\\command") as ck:
                _set(ck, "", f'"{conv}" "%1" "{tgt}"')


def uninstall():
    for ext, _ in build_entries():
        _del_tree(f"SystemFileAssociations\\{ext}\\shell\\{APP}")


if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "install"
    if action == "uninstall":
        uninstall()
    else:
        install()
