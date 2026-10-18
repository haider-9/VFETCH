import time
from pathlib import Path
import yt_dlp
from .ui import UI

def extract(url, logger=None):
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "logger": logger,
    }
    with yt_dlp.YoutubeDL(options) as ydl: return ydl.extract_info(url, download=False)

def run_download(url, destination: Path, profile: str, ui: UI, ffmpeg=True):
    started = time.time(); destination.mkdir(parents=True, exist_ok=True)
    if profile == "1": fmt, post = ("bv*+ba/b" if ffmpeg else "b"), []
    elif profile == "2": fmt, post = ("ba/b", ([{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"}] if ffmpeg else []))
    else: fmt, post = profile, []
    output_template = str(destination / "%(title).200B [%(id)s].%(ext)s")
    completed = []

    def hook(data):
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate"); done = data.get("downloaded_bytes", 0)
            ui.update(label="AUDIO" if data.get("info_dict", {}).get("vcodec") == "none" else "VIDEO", pct=(done * 100 / total if total else None), speed=("%s/s" % data.get("speed") if data.get("speed") else "--"), eta=(__import__('vfetch.util', fromlist=['fmt_eta']).fmt_eta(data.get("eta"))), done=__import__('vfetch.util', fromlist=['human_bytes']).human_bytes(done), total=__import__('vfetch.util', fromlist=['human_bytes']).human_bytes(total) if total else "?")
        elif status == "finished":
            filename = data.get("filename")
            if filename:
                completed.append(Path(filename))
            ui.update(label="FINALIZING", pct=100.0)

    def postprocess_hook(data):
        if data.get("status") == "started":
            name = str(data.get("postprocessor", ""))
            ui.update(label="CONVERTING AUDIO" if "Audio" in name or "Extract" in name else "MERGING STREAMS")

    options = {
        "format": fmt,
        "outtmpl": output_template,
        "noplaylist": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
        "progress_hooks": [hook],
        "postprocessor_hooks": [postprocess_hook],
        "postprocessors": post,
        "logger": yt_dlp.utils.Logger(),
    }
    if ffmpeg:
        options.update({"merge_output_format": "mkv", "embed_metadata": True})
    ui.start()
    try:
        with yt_dlp.YoutubeDL(options) as ydl: ydl.download([url])
    finally: ui.finish()
    files = [path for path in completed if path.exists()]
    if not files:
        files = sorted(destination.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return (files[-1] if files else None), time.time() - started
