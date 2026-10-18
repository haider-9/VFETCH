import os
import sys
import threading
import time
from .util import fmt_eta, human_bytes, terminal_size, unicode_ok

class UI:
    def __init__(self, no_color=False, ascii_mode=False):
        self.ascii = ascii_mode or not unicode_ok()
        self.color = not no_color and not os.environ.get("NO_COLOR") and sys.stdout.isatty()
        self.stop = threading.Event(); self.lock = threading.Lock(); self.state = {"label":"CONNECTING", "pct":None, "speed":"--", "eta":"--:--", "done":"0 B", "total":"?"}
        self.spinner = "|/-\\" if self.ascii else "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    def c(self, code, text): return f"\033[38;5;{code}m{text}\033[0m" if self.color else text
    def banner(self, engine, ffmpeg, output):
        print("\n  V F E T C H\n\n  VIDEO DOWNLOADER  v3.0.0\n")
        print("  ENGINE       yt-dlp", engine); print("  FFMPEG      ", "found" if ffmpeg else "missing")
        print(f"  SYSTEM       Python {sys.version_info.major}.{sys.version_info.minor} / {sys.platform}")
        print(f"  OUTPUT       {output}\n  MODE         Single video, no playlist\n")
    def section(self, text): print(f"\n  {text}\n  {'-' * 54}")
    def update(self, **values):
        with self.lock: self.state.update(values)
    def _draw(self):
        frame = 0
        while not self.stop.is_set():
            with self.lock: state = dict(self.state)
            width = max(8, min(40, terminal_size() - 58)); pct = state["pct"]
            if pct is None: bar = ("-" if self.ascii else "░") * width
            else:
                filled = int(width * max(0, min(100, pct)) / 100); bar = ("#" if self.ascii else "█") * filled + ("-" if self.ascii else "░") * (width-filled)
            line = f"\r\033[2K  {self.spinner[frame % len(self.spinner)]} {state['label']:<16} {bar}"
            if pct is not None: line += f" {pct:5.1f}%"
            line += f"  {state['speed']}  ETA {state['eta']}"
            if terminal_size() >= 104: line += f"  {state['done']} / {state['total']}"
            print(line, end="", flush=True); frame += 1; time.sleep(.1)
    def start(self):
        if self.color: print("\033[?25l", end="")
        if self.color and sys.stdout.isatty(): self.thread = threading.Thread(target=self._draw, daemon=True); self.thread.start()
    def finish(self):
        self.stop.set()
        if getattr(self, "thread", None): self.thread.join(timeout=1); print()
        if self.color: print("\033[?25h", end="", flush=True)
