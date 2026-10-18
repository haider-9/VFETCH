import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from prompt_toolkit import prompt
from yt_dlp.utils import YoutubeDLError
from yt_dlp.version import __version__ as YTDLP_VERSION

from . import __version__
from .download import extract, run_download
from .formats import render_table
from .ui import UI
from .util import (
    clean_url,
    default_dir,
    enable_windows_console,
    ffmpeg_hint,
    ffmpeg_path,
    fmt_elapsed,
    human_bytes,
    valid_url,
)

QUIT_WORDS = ("q", "quit", "exit")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="vfetch", description="Friendly cross-platform yt-dlp terminal downloader"
    )
    parser.add_argument("url", nargs="?")
    parser.add_argument("-d", "--dir", dest="directory")
    parser.add_argument("-V", "--version", action="version", version=f"vfetch {__version__}")
    parser.add_argument("--update", action="store_true", help="update yt-dlp")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--ascii", action="store_true")
    return parser.parse_args(argv)


def update_ytdlp() -> int:
    import yt_dlp

    spec = "yt-dlp[default]"
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    cmd = [sys.executable, "-m", "pip", "install", "-U", spec]
    if not in_venv:
        # Windows installer layout: packages live in a --target folder that the
        # launcher puts first on sys.path, so update that exact folder.
        site = Path(yt_dlp.__file__).resolve().parent.parent
        if (site / "vfetch").is_dir():
            cmd += ["--target", str(site)]
    has_pip = subprocess.run(
        [sys.executable, "-m", "pip", "--version"], capture_output=True
    ).returncode == 0
    if not has_pip:
        import shutil

        uv = shutil.which("uv")
        if not uv:
            print("  [ERROR] pip is not available in this environment and uv was not found.")
            return 1
        cmd = [uv, "pip", "install", "--python", sys.executable, "-U", spec]
    return subprocess.run(cmd).returncode


def read_line(text: str) -> str:
    return input(text)


def read_url(ui: UI) -> str:
    arrow = ">" if ui.ascii else "❯"
    text = f"  {arrow} "
    if sys.stdin.isatty():
        return prompt(text)
    return input(text)


def ask_url(ui: UI, preset):
    """Return a valid URL, or None if the user wants to quit."""
    ui.section("01 / SOURCE")
    while True:
        if preset:
            url, preset = clean_url(preset), None
            print(f"\n  {url}")
        else:
            print("  Paste a video URL below " + ui.paint(245, "(q to quit)") + ".\n")
            url = clean_url(read_url(ui))
        if url.lower() in QUIT_WORDS:
            return None
        if not url:
            ui.status(203, "ERROR", "No URL provided.")
            print()
            continue
        if not valid_url(url):
            ui.status(203, "ERROR", "That doesn't look like an http(s) URL.")
            print()
            continue
        return url


def choose_profile(ui: UI, have_ffmpeg: bool):
    """Return (profile, mode_label, container_label) or None if nothing was chosen."""
    ui.section("03 / DOWNLOAD PROFILE")
    print("  " + ui.paint(208, "[1]") + " Best quality video + audio")
    print("  " + ui.paint(208, "[2]") + (" Audio only (MP3)" if have_ffmpeg else " Audio only (best available, no conversion)"))
    print("  " + ui.paint(208, "[3]") + " Custom format ID or expression\n")
    choice = read_line("  Selection " + ui.paint(245, "[1]") + ": ").strip() or "1"
    choice = {"best": "1", "audio": "2", "custom": "3"}.get(choice.lower(), choice)
    custom_container = "MKV when merging is needed" if have_ffmpeg else "Original"

    if choice == "1":
        if have_ffmpeg:
            return "1", "Best quality video + audio", "MKV (streams merged)"
        return "1", "Best single-file quality (ffmpeg not found)", "Original, no merging"
    if choice == "2":
        if have_ffmpeg:
            return "2", "Audio only (MP3)", "MP3"
        return "2", "Best available audio (no conversion)", "Original"
    if choice == "3":
        print("\n  Enter a format ID or yt-dlp format expression.")
        print("  Examples: 137+ba/b, 140, bestvideo+bestaudio")
        arrow = ">" if ui.ascii else "❯"
        choice = read_line("  " + ui.paint(208, arrow) + " ").strip()
        if not choice:
            ui.status(203, "ERROR", "No format entered.")
            return None
    # Anything else is treated as a format expression typed directly.
    return choice, f"Custom format: {choice}", custom_container


def confirm(ui: UI, mode: str, container: str, output: Path) -> bool:
    ui.section("04 / READY TO DOWNLOAD")
    ui.info("PROFILE", mode)
    ui.info("CONTAINER", container)
    ui.info("DESTINATION", str(output))
    answer = read_line("\n  Start download? " + ui.paint(245, "[Y/n]") + ": ").strip().lower()
    if answer in ("", "y", "yes"):
        return True
    ui.status(245, "CANCELLED", "Download cancelled.")
    return False


def explain_error(ui: UI, error: Exception, have_ffmpeg: bool) -> None:
    message = ANSI_RE.sub("", str(error)).strip()
    message = re.sub(r"^ERROR:\s*", "", message)
    ui.status(203, "FAILED", message or error.__class__.__name__)
    if re.search(r"unable to extract|http error 403|nsig|signature", message, re.I):
        print("\n  Tip: the site may have changed. Run: vfetch --update")
    if "ffmpeg" in message.lower() and not have_ffmpeg:
        print("\n  Tip: ffmpeg is required for this format. Install it with: " + ffmpeg_hint())


def download_one(ui: UI, url: str, output: Path, color: bool) -> int:
    """Run one full extract -> choose -> confirm -> download cycle. Returns exit code."""
    have_ffmpeg = bool(ffmpeg_path())
    try:
        ui.section("02 / AVAILABLE FORMATS")
        print("  Retrieving formats from the source...\n", flush=True)
        info = extract(url)
        print(render_table(info, ascii_mode=ui.ascii, color=color))

        choice = choose_profile(ui, have_ffmpeg)
        if choice is None:
            return 0
        profile, mode, container = choice
        if not confirm(ui, mode, container, output):
            return 0

        ui.section("05 / DOWNLOAD")
        path, elapsed = run_download(url, output, profile, ui, have_ffmpeg)
        if not path:
            ui.status(203, "FAILED", "yt-dlp did not produce a file.")
            return 1
        ui.status(114, "SUCCESS", "Download completed.")
        ui.info("FILE", path.name[:70])
        ui.info("SIZE", human_bytes(path.stat().st_size))
        ui.info("TIME", fmt_elapsed(elapsed))
        ui.info("SAVED TO", str(output))
        return 0
    except (YoutubeDLError, OSError, ValueError) as error:
        explain_error(ui, error, have_ffmpeg)
        return 1


def main(argv=None) -> int:
    enable_windows_console()
    args = parse_args(argv)
    if args.update:
        return update_ytdlp()

    output = Path(args.directory or os.environ.get("VFETCH_DIR") or default_dir()).expanduser()
    try:
        output.mkdir(parents=True, exist_ok=True)
        if not os.access(output, os.W_OK):
            raise OSError("directory is not writable")
    except OSError as error:
        print(f"[ERROR] Cannot write to {output}: {error}")
        return 1

    no_color = args.no_color or bool(os.environ.get("NO_COLOR"))
    ui = UI(no_color, args.ascii)
    color = ui.color
    ui.banner(YTDLP_VERSION, ffmpeg_path(), output, __version__)

    preset = args.url
    last_status = 0
    try:
        while True:
            url = ask_url(ui, preset)
            preset = None
            if url is None:
                return last_status
            last_status = download_one(ui, url, output, color)
            answer = read_line("\n  Download another? [y/N] ").strip().lower()
            if not answer.startswith("y"):
                return last_status
    except (EOFError, KeyboardInterrupt):
        print("\n\n  [CANCELLED] Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())