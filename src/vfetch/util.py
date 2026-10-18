import os
import platform
import re
import shutil
import sys
from pathlib import Path

def clean_url(value: str) -> str:
    return value.strip().strip("'\"").strip()

def valid_url(value: str) -> bool:
    return bool(re.match(r"^https?://[^\s]+$", clean_url(value), re.I))

def human_bytes(value):
    if value is None: return "—"
    value = float(value)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    index = 0
    while abs(value) >= 1024 and index < len(units) - 1:
        value /= 1024.0; index += 1
    return f"{value:.1f} {units[index]}"

def fmt_eta(seconds):
    if seconds is None: return "--:--"
    seconds = max(0, int(seconds))
    if seconds >= 3600: return f"{seconds // 3600}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
    return f"{seconds // 60:02d}:{seconds % 60:02d}"

def default_dir() -> Path:
    return Path.home() / ("Movies" if sys.platform == "darwin" else "Videos") / "Downloads"

def ffmpeg_path():
    return shutil.which("ffmpeg")

def ffmpeg_hint() -> str:
    if sys.platform == "win32": return "winget install Gyan.FFmpeg"
    if sys.platform == "darwin": return "brew install ffmpeg"
    for manager in ("pacman", "apt", "dnf", "zypper", "apk"):
        if shutil.which(manager): return f"sudo {manager} {'-S' if manager == 'pacman' else 'install'} ffmpeg"
    return "install ffmpeg with your distribution's package manager"

def terminal_size():
    return shutil.get_terminal_size((80, 24)).columns

def enable_windows_console():
    if sys.platform != "win32": return
    try:
        import ctypes
        kernel = ctypes.windll.kernel32
        for handle in (-11, -12):
            h = kernel.GetStdHandle(handle); mode = ctypes.c_uint32()
            if kernel.GetConsoleMode(h, ctypes.byref(mode)): kernel.SetConsoleMode(h, mode.value | 0x0004)
        os.system("chcp 65001 > nul")
    except Exception:
        pass

def unicode_ok() -> bool:
    if os.environ.get("VFETCH_ASCII"): return False
    if sys.platform == "win32": return bool(os.environ.get("WT_SESSION") or os.environ.get("TERM_PROGRAM"))
    return "UTF-8" in (sys.stdout.encoding or "").upper() or "UTF8" in (os.environ.get("LANG", "").upper())
