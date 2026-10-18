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
    ui = UI(args.no_color, args.ascii); ui.banner(yt_dlp.version.__version__, ffmpeg_path(), output)
    url = clean_url(args.url) if args.url else None
    while True:
        ui.section("01 / SOURCE")
        if not url:
            try: url = clean_url(input("  Paste a video URL below (q to quit): "))
            except (EOFError, KeyboardInterrupt): print("\n\n  [CANCELLED] Interrupted."); return 130
        if url.lower() in ("q", "quit", "exit"): return 0
        if not valid_url(url): print("\n  [ERROR] That doesn't look like an http(s) URL."); url = None; continue
        try:
            ui.section("02 / AVAILABLE FORMATS"); info = extract(url); print(render_table(info, ascii_mode=ui.ascii))
            ui.section("03 / DOWNLOAD PROFILE"); print("  [1] Best video + audio\n  [2] Audio only\n  [3] Custom format expression")
            profile = input("  Select profile [1]: ").strip() or "1"; profile = profile if profile in ("1", "2", "3") else profile
            if profile == "3": profile = input("  Format expression: ").strip()
            elif profile not in ("1", "2"): profile = profile
            ui.section("04 / READY TO DOWNLOAD"); print(f"  PROFILE      {profile}\n  CONTAINER    {'MKV' if profile == '1' else 'MP3' if profile == '2' and ffmpeg_path() else 'source'}\n  DESTINATION  {output}")
            if input("  Start download? [Y/n] ").strip().lower() == "n": url = None; continue
            ui.section("05 / DOWNLOAD"); path, elapsed = run_download(url, output, profile, ui, bool(ffmpeg_path()))
            print(f"\n  [SUCCESS] Download complete.\n  FILE         {path}\n  TIME         {elapsed:.1f}s\n  SAVED TO     {output}" if path else "\n  [FAILED] Download did not produce a file.")
        except KeyboardInterrupt: print("\n\n  [CANCELLED] Interrupted."); return 130
        except Exception as error: print(f"\n  [FAILED] {error}\n  Tip: run vfetch --update\n  ffmpeg: {ffmpeg_hint()}")
        try: again = input("\n  Download another? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt): print("\n  [CANCELLED] Interrupted."); return 130
        if again != "y": return 0
        url = None
