from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import yt_dlp

from .util import fmt_eta, fmt_rate, human_bytes

if TYPE_CHECKING:  # avoid a runtime import cycle / hard dependency on the UI
    from .ui import UI


class QuietLogger:
    """Keeps yt-dlp from printing over the progress UI; remembers recent errors."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def debug(self, msg) -> None:
        pass

    def info(self, msg) -> None:
        pass

    def warning(self, msg) -> None:
        pass

    def error(self, msg) -> None:
        self.errors.append(str(msg))


def first_entry(info: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """If yt-dlp returned a playlist wrapper, use its first real entry."""
    if info and info.get("entries") and not info.get("formats"):
        entries = [entry for entry in info["entries"] if entry]
        if entries:
            return entries[0]
    return info


def extract(url, logger=None):
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "logger": logger or QuietLogger(),
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    info = first_entry(info)
    if not info:
        raise ValueError("yt-dlp returned no information for this URL.")
    return info


def build_options(destination: Path, profile: str, ffmpeg: bool = True) -> Dict[str, Any]:
    """yt-dlp options for a profile: '1' best, '2' MP3 audio, anything else = format string."""
    post = []
    if profile == "1":
        fmt = "bv*+ba/b" if ffmpeg else "b"
    elif profile == "2":
        fmt = "ba/b"
        if ffmpeg:
            post.append({"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"})
    else:
        fmt = profile
    options: Dict[str, Any] = {
        "format": fmt,
        "outtmpl": str(destination / "%(title).200B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
    }
    if ffmpeg:
        options["merge_output_format"] = "mkv"
        # API equivalent of the CLI's --embed-metadata
        post.append({"key": "FFmpegMetadata", "add_metadata": True})
    options["postprocessors"] = post
    return options


def make_hooks(ui: "UI"):
    def hook(data):
        if data.get("status") != "downloading":
            return
        total = data.get("total_bytes") or data.get("total_bytes_estimate")
        done = data.get("downloaded_bytes") or 0
        vcodec = (data.get("info_dict") or {}).get("vcodec")
        label = "AUDIO" if vcodec == "none" else "VIDEO" if vcodec else "DOWNLOADING"
        ui.update(
            label=label,
            pct=min(100.0, done * 100 / total) if total else None,
            speed=fmt_rate(data.get("speed")),
            eta=fmt_eta(data.get("eta")),
            done=human_bytes(done),
            total=human_bytes(total) if total else "?",
        )

    def postprocess_hook(data):
        if data.get("status") == "started":
            name = str(data.get("postprocessor", ""))
            if "Audio" in name or "Extract" in name:
                label = "CONVERTING AUDIO"
            elif "Merg" in name:
                label = "MERGING STREAMS"
            else:
                label = "FINALIZING"
            ui.update(label=label)

    return hook, postprocess_hook


def final_path(info: Optional[Dict[str, Any]]) -> Optional[Path]:
    """The file yt-dlp actually left on disk (after merging / conversion)."""
    if not info:
        return None
    candidates = [info] + [e for e in (info.get("entries") or []) if e]
    for item in candidates:
        for download in item.get("requested_downloads") or []:
            name = download.get("filepath") or download.get("_filename")
            if name and Path(name).exists():
                return Path(name)
        name = item.get("filepath")
        if name and Path(name).exists():
            return Path(name)
    return None


def run_download(url, destination: Path, profile: str, ui: "UI", ffmpeg: bool = True):
    started = time.monotonic()
    destination.mkdir(parents=True, exist_ok=True)
    hook, postprocess_hook = make_hooks(ui)
    options = build_options(destination, profile, ffmpeg)
    options["progress_hooks"] = [hook]
    options["postprocessor_hooks"] = [postprocess_hook]
    options["logger"] = QuietLogger()
    ui.start()
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    finally:
        ui.finish()
    return final_path(info), time.monotonic() - started