import argparse
import os
import subprocess
import sys
from pathlib import Path
import yt_dlp
from . import __version__
from .download import extract, run_download
from .formats import render_table
from .ui import UI
from .util import clean_url, default_dir, enable_windows_console, ffmpeg_hint, ffmpeg_path, valid_url

def main(argv=None):
    enable_windows_console()
    parser = argparse.ArgumentParser(prog="vfetch", description="Friendly cross-platform yt-dlp terminal downloader")
    parser.add_argument("url", nargs="?"); parser.add_argument("-d", "--dir", dest="directory"); parser.add_argument("-V", "--version", action="version", version=f"vfetch {__version__}"); parser.add_argument("--update", action="store_true"); parser.add_argument("--no-color", action="store_true"); parser.add_argument("--ascii", action="store_true")
    args = parser.parse_args(argv)
    if args.update:
        subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp[default]"]); return 0
    output = Path(args.directory or os.environ.get("VFETCH_DIR") or default_dir()).expanduser()
    try: output.mkdir(parents=True, exist_ok=True)
    except OSError as error: print(f"[ERROR] Cannot write to {output}: {error}"); return 1
    ui = UI(args.no_color, args.ascii)
    ui.banner(yt_dlp.version.__version__, ffmpeg_path(), output)
    url = clean_url(args.url) if args.url else None
    while True:
        ui.section("01 / SOURCE")
        if not url:
            try:
                print("  Paste a video URL below " + ui.paint(245, "(q to quit)") + ".\n")
                url = clean_url(input("  " + ui.paint(208, "❯" if not ui.ascii else ">") + " "))
            except (EOFError, KeyboardInterrupt): print("\n\n  [CANCELLED] Interrupted."); return 130
        if url.lower() in ("q", "quit", "exit"): return 0
        if not valid_url(url):
            ui.status(203, "ERROR", "That doesn't look like an http(s) URL.")
            print()
            url = None
            continue
        try:
            ui.section("02 / AVAILABLE FORMATS")
            info = extract(url)
            print(render_table(info, ascii_mode=ui.ascii))
            ui.section("03 / DOWNLOAD PROFILE")
            print("  " + ui.paint(208, "[1]") + " Best quality video + audio")
            print("  " + ui.paint(208, "[2]") + (" Audio only (MP3)" if ffmpeg_path() else " Audio only (best available, no conversion)"))
            print("  " + ui.paint(208, "[3]") + " Custom format ID or expression\n")
            profile = input("  Selection " + ui.paint(245, "[1]") + ": ").strip() or "1"
            mode = profile
            if profile == "1":
                mode, container = ("Best quality video + audio", "MKV (streams merged)") if ffmpeg_path() else ("Best single-file quality (ffmpeg not found)", "Original, no merging")
            elif profile == "2":
                mode, container = (("Audio only (MP3)", "MP3") if ffmpeg_path() else ("Best available audio (no conversion)", "Original"))
            elif profile == "3":
                print("\n  Enter a format ID or yt-dlp format expression.\n  Examples: 137+ba/b, 140, bestvideo+bestaudio")
                mode = input("  " + ui.paint(208, "❯" if not ui.ascii else ">") + " ").strip()
                profile, container = mode, "MKV when merging is needed" if ffmpeg_path() else "Original"
            else:
                mode, container = f"Custom format: {profile}", "MKV when merging is needed" if ffmpeg_path() else "Original"
            ui.section("04 / READY TO DOWNLOAD")
            ui.info("PROFILE", mode); ui.info("CONTAINER", container); ui.info("DESTINATION", str(output))
            if input("\n  Start download? " + ui.paint(245, "[Y/n]") + ": ").strip().lower() not in ("", "y", "yes"):
                ui.status(245, "CANCELLED", "Download cancelled."); url = None; continue
            ui.section("05 / DOWNLOAD")
            path, elapsed = run_download(url, output, profile, ui, bool(ffmpeg_path()))
            if path:
                ui.status(114, "SUCCESS", "Download completed.")
                ui.info("FILE", path.name); ui.info("SIZE", f"{path.stat().st_size} bytes"); ui.info("TIME", f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"); ui.info("SAVED TO", str(output))
            else: ui.status(203, "FAILED", "yt-dlp did not produce a file.")
        except KeyboardInterrupt:
            print("\n\n  [CANCELLED] Interrupted."); return 130
        except Exception as error:
            ui.status(203, "FAILED", str(error)); print("\n  Tip: run vfetch --update\n  ffmpeg: " + ffmpeg_hint())
        try: again = input("\n  Download another? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt): print("\n  [CANCELLED] Interrupted."); return 130
        if again != "y": return 0
        url = None
