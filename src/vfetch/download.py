import time
from pathlib import Path
import yt_dlp
from .ui import UI

def extract(url, logger=None):
    options = {"quiet": True, "no_warnings": True, "skip_download": True, "logger": logger}
    with yt_dlp.YoutubeDL(options) as ydl: return ydl.extract_info(url, download=False)

def run_download(url, destination: Path, profile: str, ui: UI, ffmpeg=True):
    started = time.time(); destination.mkdir(parents=True, exist_ok=True)
    if profile == "1": fmt, post = ("bv*+ba/b" if ffmpeg else "b"), []
    elif profile == "2": fmt, post = (("bestaudio/best"), ([{"key":"FFmpegExtractAudio", "preferredcodec":"mp3"}] if ffmpeg else []))
    else: fmt, post = profile, []
    def hook(data):
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate"); done = data.get("downloaded_bytes", 0)
            ui.update(label="AUDIO" if data.get("info_dict", {}).get("vcodec") == "none" else "VIDEO", pct=(done * 100 / total if total else None), speed=("%s/s" % data.get("speed") if data.get("speed") else "--"), eta=(__import__('vfetch.util', fromlist=['fmt_eta']).fmt_eta(data.get("eta"))), done=__import__('vfetch.util', fromlist=['human_bytes']).human_bytes(done), total=__import__('vfetch.util', fromlist=['human_bytes']).human_bytes(total) if total else "?")
        elif status == "finished": ui.update(label="FINALIZING", pct=100.0)
    options = {"format": fmt, "outtmpl": str(destination / "%(title)s [%(id)s].%(ext)s"), "progress_hooks": [hook], "postprocessor_hooks": lambda d: ui.update(label="CONVERTING AUDIO" if "Audio" in str(d.get("postprocessor", "")) else "MERGING STREAMS"), "postprocessors": post, "logger": yt_dlp.utils.Logger()}
    ui.start()
    try:
        with yt_dlp.YoutubeDL(options) as ydl: ydl.download([url])
    finally: ui.finish()
    files = sorted(destination.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None, time.time() - started
