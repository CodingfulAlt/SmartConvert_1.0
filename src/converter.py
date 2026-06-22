# converter.py - called from context menu as: converter.exe <file> <.ext>

import sys
import os
import subprocess
import datetime
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE = Path(sys.executable).parent.parent  # bin\ -> SmartConvert\
else:
    BASE = Path(__file__).parent

FFMPEG_EXE = BASE / "data" / "ffmpeg" / "ffmpeg.exe"
LIBS_DIR   = BASE / "data" / "libs"
LOG_FILE   = BASE / "logs" / "converter.log"

# Add local libs to path (in case Pillow was installed there)
if LIBS_DIR.exists():
    sys.path.insert(0, str(LIBS_DIR))


def _log(msg):
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def notify_error(msg: str):
    _log(f"ERROR: {msg}")
    m = msg.replace('"', "'").replace("\n", " ")
    ps = (
        f'Add-Type -AssemblyName System.Windows.Forms;'
        f'[System.Windows.Forms.MessageBox]::Show("{m}","SmartConvert ✗")'
    )
    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        _log(f"notify error: {e}")


def ensure_pillow():
    """Install Pillow into data/libs if not available."""
    try:
        import PIL
        return True
    except ImportError:
        pass
    try:
        _log("Pillow not found, installing to data/libs...")
        LIBS_DIR.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "Pillow", "pillow-heif",
             "--target", str(LIBS_DIR),
             "--quiet", "--disable-pip-version-check"],
            capture_output=True, text=True,
        )
        _log(f"pip rc={r.returncode} out={r.stdout[-200:]} err={r.stderr[-200:]}")
        if LIBS_DIR.exists():
            sys.path.insert(0, str(LIBS_DIR))
        return r.returncode == 0
    except Exception as e:
        _log(f"ensure_pillow error: {e}")
        return False


IMAGE_EXTS = {".heic", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
FMT_MAP = {
    ".jpg": "JPEG", ".jpeg": "JPEG",
    ".png": "PNG",  ".webp": "WEBP",
    ".bmp": "BMP",  ".tiff": "TIFF", ".tif": "TIFF",
}

def convert_image(src: Path, tgt: str):
    _log(f"image {src.name} -> {tgt}")
    if not ensure_pillow():
        notify_error("Pillow не може да се инсталира. Провери интернет връзката.")
        return
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        from PIL import Image
        img = Image.open(src)
        dst = src.with_suffix(tgt)
        fmt = FMT_MAP.get(tgt.lower(), tgt.lstrip(".").upper())
        if fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(dst, fmt)
        _log(f"OK -> {dst.name}")
    except Exception as e:
        notify_error(str(e))
        _log(f"image error: {e}")


AUDIO_EXTS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}

def convert_audio(src: Path, tgt: str):
    _log(f"audio {src.name} -> {tgt}")
    if not FFMPEG_EXE.exists():
        notify_error("ffmpeg не е намерен. Стартирай smartconvert.exe.")
        return
    try:
        dst = src.with_suffix(tgt)
        r = subprocess.run(
            [str(FFMPEG_EXE), "-y", "-i", str(src), str(dst)],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if r.returncode == 0:
            _log(f"OK -> {dst.name}")
        else:
            notify_error(r.stderr.decode(errors="replace")[-200:])
    except Exception as e:
        notify_error(str(e))
        _log(f"audio error: {e}")


TEXT_EXTS = {".txt", ".bat", ".py", ".json", ".md"}

def convert_text(src: Path, tgt: str):
    _log(f"text {src.name} -> {tgt}")
    try:
        dst = src.with_suffix(tgt)
        dst.write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        _log(f"OK -> {dst.name}")
    except Exception as e:
        notify_error(str(e))
        _log(f"text error: {e}")


def dispatch(src_str: str, tgt: str):
    _log(f"--- dispatch src={src_str!r} tgt={tgt!r}")
    src = Path(src_str)
    if not src.exists():
        notify_error(f"Файлът не съществува: {src}")
        return
    ext = src.suffix.lower()
    if   ext in IMAGE_EXTS: convert_image(src, tgt)
    elif ext in AUDIO_EXTS: convert_audio(src, tgt)
    elif ext in TEXT_EXTS:  convert_text(src, tgt)
    else:
        notify_error(f"Неподдържан формат: {ext}")


if __name__ == "__main__":
    _log(f"=== start args={sys.argv}")
    if len(sys.argv) == 3:
        dispatch(sys.argv[1], sys.argv[2])
    else:
        notify_error("Грешка: нужни са 2 аргумента")
