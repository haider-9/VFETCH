import os
import re
import shutil
import sys
from pathlib import Path

_URL_RE = re.compile(r"^https?://[^\s]+$", re.I)


def clean_url(value) -> str:
    return (value or "").strip().strip("'\"").strip()


def valid_url(value) -> bool:
    return bool(_URL_RE.match(clean_url(value)))


def human_bytes(value) -> str:
    if value is None:
        return "—"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    index = 0
    while abs(value) >= 1024 and index < len(units) - 1:
        value /= 1024.0
        index += 1
    return f"{value:.1f} {units[index]}"


def fmt_rate(speed) -> str:
    """Bytes/second -> '1.8 MiB/s', or '--' when unknown."""
    if not speed:
        return "--"
    return human_bytes(speed) + "/s"


def fmt_eta(seconds) -> str:
    if seconds is None:
        return "--:--"
    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        return "--:--"
    if seconds >= 3600:
        return f"{seconds // 3600}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def fmt_elapsed(seconds) -> str:
    return fmt_eta(int(seconds))


def default_dir() -> Path:
    return Path.home() / ("Movies" if sys.platform == "darwin" else "Videos") / "Downloads"


def ffmpeg_path():
    return shutil.which("ffmpeg")


def ffmpeg_hint() -> str:
    if sys.platform == "win32":
        return "winget install Gyan.FFmpeg"
    if sys.platform == "darwin":
        return "brew install ffmpeg"
    commands = {
        "pacman": "sudo pacman -S ffmpeg",
        "apt": "sudo apt install ffmpeg",
        "dnf": "sudo dnf install ffmpeg-free",
        "zypper": "sudo zypper install ffmpeg",
        "apk": "sudo apk add ffmpeg",
    }
    for manager, command in commands.items():
        if shutil.which(manager):
            return command
    return "install ffmpeg with your distribution's package manager"


def terminal_size() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def enable_windows_console() -> None:
    """Turn on ANSI escapes and UTF-8 output in the Windows console."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel = ctypes.windll.kernel32
        for handle in (-11, -12):  # stdout, stderr
            h = kernel.GetStdHandle(handle)
            mode = ctypes.c_uint32()
            if kernel.GetConsoleMode(h, ctypes.byref(mode)):
                kernel.SetConsoleMode(h, mode.value | 0x0004)
        kernel.SetConsoleOutputCP(65001)
    except Exception:
        pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def unicode_ok() -> bool:
    if os.environ.get("VFETCH_ASCII"):
        return False
    if sys.platform == "win32":
        return bool(os.environ.get("WT_SESSION") or os.environ.get("TERM_PROGRAM"))
    locale = (
        os.environ.get("LC_ALL") or os.environ.get("LC_CTYPE") or os.environ.get("LANG") or ""
    ).upper()
    encoding = (getattr(sys.stdout, "encoding", None) or "").upper()
    return "UTF-8" in encoding or "UTF8" in encoding or "UTF-8" in locale or "UTF8" in locale