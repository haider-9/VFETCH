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
from .formats import codec_name, group_formats, render_table
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
BACK = object()          # sentinel: user asked to return to the previous tab
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


def build_tabs(groups):
    """Tabs for this source: VIDEO and/or AUDIO, always ending with CONFIRM."""
    tabs = []
    if groups["VIDEO ONLY"] or groups["VIDEO + AUDIO"]:
        if groups["VIDEO ONLY"] and groups["AUDIO ONLY"]:
            names = ("VIDEO ONLY",)                 # split source: video tab = the video stream
        else:
            names = tuple(n for n in ("VIDEO + AUDIO", "VIDEO ONLY") if groups[n])
        tabs.append(("VIDEO", names))
    if groups["AUDIO ONLY"]:
        tabs.append(("AUDIO", ("AUDIO ONLY",)))
    tabs.append(("CONFIRM", None))
    return tabs


def flow_text(tabs):
    names = [name for name, _ in tabs]
    if "VIDEO" in names and "AUDIO" in names:
        return "choose a VIDEO format, then an AUDIO format, then merge both streams into a single file"
    if "VIDEO" in names:
        return "choose a VIDEO format, then confirm the download"
    return "choose an AUDIO format, then confirm the download"


def draw_tabs(ui: UI, tabs, active):
    cells = []
    for number, (name, _) in enumerate(tabs, 1):
        label = f"{number} {name}"
        cells.append(ui.paint(208, f"< {label} >", True) if name == active
                     else ui.paint(245, f"  {label}  "))
    print("  " + " ".join(cells))


def ask_format(ui: UI, items, label):
    """Return a chosen format item, a custom-expression pseudo-item, BACK, or None to quit."""
    listed = {str(item.get("format_id")) for item in items}
    while True:
        raw = read_line(f"  Choose {label} format "
                        + ui.paint(245, "[Enter=best, b=back, q=quit]") + ": ").strip()
        low = raw.lower()
        if low in QUIT_WORDS:
            return None
        if low in ("b", "back"):
            return BACK
        if not raw:
            return items[0]
        if raw in listed:
            return next(item for item in items if str(item.get("format_id")) == raw)
        if re.search(r"[+/,]", raw) or low.startswith("best"):
            return {"format_id": raw, "custom": True, "vcodec": None, "acodec": None}
        ui.status(203, "ERROR", f"'{raw}' is not one of the format IDs listed above.")


def choose_formats(ui: UI, info, groups, tabs, color):
    """Walk the tabs in order; return {"video": item|None, "audio": item|None} or None to quit."""
    picks = {"video": None, "audio": None}
    steps = len(tabs) - 1
    index = 0
    while index < steps:
        name, names = tabs[index]
        print()
        draw_tabs(ui, tabs, name)
        print(f"  {ui.paint(231, 'STEP ' + str(index + 1) + '/' + str(steps))}"
              f"  Pick a {name} format from the list below.")
        items = [item for group_name in names for item in groups[group_name]]
        print()
        print(render_table(info, ascii_mode=ui.ascii, color=color, only=names))
        answer = ask_format(ui, items, name)
        if answer is None:
            return None
        if answer is BACK:
            index = max(0, index - 1)
            continue
        picks[name.lower()] = answer
        index += 1
    return picks


def fmt_id(item) -> str:
    return str(item.get("format_id"))


def describe_selection(video, audio, mp3, have_ffmpeg):
    """Return (profile, mode, container, note) for the chosen VIDEO/AUDIO formats."""
    custom_container = "MKV when merging is needed" if have_ffmpeg else "Original"
    if video is None and audio is None:
        if have_ffmpeg:
            return "1", "Best quality video + audio", "MKV (streams merged)", None
        return "1", "Best single-file quality (ffmpeg not found)", "Original, no merging", None
    if video is not None and audio is not None:
        if have_ffmpeg:
            return (f"{fmt_id(video)}+{fmt_id(audio)}",
                    f"Video {fmt_id(video)} + audio {fmt_id(audio)}",
                    "MKV (streams merged)", None)
        return ("1", "Best single-file quality (ffmpeg not found)", "Original, no merging",
                "ffmpeg is missing, so the streams cannot be merged - using the best single file instead.")
    if video is not None:
        vid = fmt_id(video)
        if video.get("custom"):
            return vid, f"Custom format: {vid}", custom_container, None
        has_audio = video.get("acodec") not in (None, "none")
        if has_audio:
            return vid, f"Video {vid}", "Original, no merging", None
        if have_ffmpeg:
            return f"{vid}+ba/b", f"Video {vid} + best audio", "MKV (streams merged)", None
        return (vid, f"Video {vid}", "Original, no merging",
                "ffmpeg is missing - this video stream has no audio track of its own.")
    aid = fmt_id(audio)
    if audio.get("custom"):
        return aid, f"Custom format: {aid}", custom_container, None
    if mp3:
        return f"{aid}|mp3", "Audio only (MP3)", "MP3", None
    return aid, f"Audio only ({aid})", "Original", None


def confirm(ui: UI, output: Path, tabs, video, audio, have_ffmpeg):
    """Show the CONFIRM tab; return the yt-dlp format expression, or None if cancelled."""
    ui.section("03 / CONFIRM")
    draw_tabs(ui, tabs, "CONFIRM")
    dash = "-" if ui.ascii else "—"

    def summary(item, kind):
        if item.get("custom"):
            return ui.paint(245, "custom format expression")
        if kind == "video":
            detail = codec_name(item.get("vcodec"), dash) + "/" + codec_name(item.get("acodec"), dash)
            height = item.get("height")
            if height:
                detail = f"{int(height)}p {detail}"
        else:
            detail = codec_name(item.get("acodec"), dash)
            br = item.get("abr") or item.get("tbr")
            if br:
                detail += f" {round(br)}k"
        return f"{fmt_id(item)}  {ui.paint(245, detail)}"

    if video is not None:
        ui.info("VIDEO", summary(video, "video"))
    if audio is not None:
        ui.info("AUDIO", summary(audio, "audio"))

    mp3 = False
    if audio is not None and video is None and have_ffmpeg:
        answer = read_line("\n  Convert to MP3? " + ui.paint(245, "[Y/n]") + ": ").strip().lower()
        mp3 = answer in ("", "y", "yes")

    profile, mode, container, note = describe_selection(video, audio, mp3, have_ffmpeg)
    arrow = "->" if ui.ascii else "→"
    shown = profile[:-4] + f"  {arrow}  MP3" if profile.endswith("|mp3") else profile
    ui.info("PROFILE", mode)
    ui.info("FORMAT", shown)
    ui.info("CONTAINER", container)
    ui.info("DESTINATION", str(output))
    if note:
        ui.status(221, "NOTE", note)
    answer = read_line("\n  Start download? " + ui.paint(245, "[Y/n]") + ": ").strip().lower()
    if answer in ("", "y", "yes"):
        return profile
    ui.status(245, "CANCELLED", "Download cancelled.")
    return None


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
        groups = group_formats(info)
        tabs = build_tabs(groups)
        print(f"  {ui.paint(231, 'PLAN')}  This source is chosen in steps: {flow_text(tabs)}.\n")
        print(render_table(info, ascii_mode=ui.ascii, color=color))
        if "VIDEO" not in [name for name, _ in tabs] or "AUDIO" not in [name for name, _ in tabs]:
            ui.status(221, "NOTE", "One part is missing here, so only the available tab is offered.")

        picks = choose_formats(ui, info, groups, tabs, color)
        if picks is None:
            return 0
        profile = confirm(ui, output, tabs, picks["video"], picks["audio"], have_ffmpeg)
        if profile is None:
            return 0
        final_profile = profile[:-4] if profile.endswith("|mp3") else profile

        ui.section("04 / DOWNLOAD")
        path, elapsed = run_download(url, output, final_profile, ui, have_ffmpeg)
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