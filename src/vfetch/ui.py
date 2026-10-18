import atexit
import os
import sys
import threading
import time
from .util import terminal_size, unicode_ok

ORANGE, BLUE, GREEN, RED, MUTED, YELLOW = 208, 75, 114, 203, 245, 221

class UI:
    def __init__(self, no_color=False, ascii_mode=False):
        self.ascii = ascii_mode or not unicode_ok()
        self.tty = sys.stdout.isatty()
        self.color = bool(self.tty and not no_color and not os.environ.get("NO_COLOR"))
        self.reset = "\033[0m" if self.color else ""
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.thread = None
        self.frame = 0
        self.state = {"label": "CONNECTING", "pct": None, "speed": "--", "eta": "--:--", "done": "0.0 B", "total": "?"}
        self.spinner = "|/-\\" if self.ascii else "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.full = "#" if self.ascii else "█"
        self.empty = "-" if self.ascii else "░"
        self.partial = (">",) * 7 if self.ascii else ("▏", "▎", "▍", "▌", "▋", "▊", "▉")
        self.scan = ("=",) * 5 if self.ascii else ("▒", "▓", "█", "▓", "▒")
        atexit.register(self.restore_cursor)

    def paint(self, code, text, bold=False):
        if not self.color:
            return text
        prefix = "\033[1m" if bold else ""
        return f"{prefix}\033[38;5;{code}m{text}{self.reset}"

    def line(self):
        print(f"  {self.paint(MUTED, '-' * 56 if self.ascii else '─' * 56)}")

    def section(self, text):
        print(f"\n  {self.paint(ORANGE, text)}")
        self.line()

    def info(self, key, value):
        print(f"  {self.paint(MUTED, key.ljust(12))} {value}")

    def status(self, code, key, message):
        print(f"\n  {self.paint(code, '[' + key + ']', True)} {message}")

    def banner(self, engine, ffmpeg, output):
        rows = ("██╗   ██╗███████╗███████╗████████╗ ██████╗██╗  ██╗", "██║   ██║██╔════╝██╔════╝╚══██╔══╝██╔════╝██║  ██║", "██║   ██║█████╗  █████╗     ██║   ██║     ███████║", "╚██╗ ██╔╝██╔══╝  ██╔══╝     ██║   ██║     ██╔══██║", " ╚████╔╝ ██║     ███████╗   ██║   ╚██████╗██║  ██║", "  ╚═══╝  ╚═╝     ╚══════╝   ╚═╝    ╚═════╝╚═╝  ╚═╝") if not self.ascii else ("V F E T C H",)
        for index, row in enumerate(rows):
            print("  " + (self.paint((202, 208, 208, 214, 214, 220)[index], row) if self.color else row))
        print(f"\n  {self.paint(231, 'VIDEO DOWNLOADER', True)} {self.paint(MUTED, 'v3.0.0')}\n")
        self.line()
        self.info("ENGINE", f"yt-dlp {engine}")
        self.info("FFMPEG", self.paint(GREEN if ffmpeg else RED, "found" if ffmpeg else "missing") + ("" if ffmpeg else " " + self.paint(MUTED, "(merging and MP3 disabled)")))
        self.info("SYSTEM", f"Python {sys.version_info.major}.{sys.version_info.minor} / {sys.platform.title()}")
        self.info("OUTPUT", str(output))
        self.info("MODE", "Single video, no playlist")
        self.line()

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def _bar(self, width, frame, pct):
        if pct is None:
            span = max(1, width - len(self.scan))
            pos = frame % (span * 2)
            pos = pos if pos <= span else span * 2 - pos
            return "".join(self.paint(ORANGE if pos <= i < pos + len(self.scan) else MUTED, self.scan[i - pos] if pos <= i < pos + len(self.scan) else self.empty) for i in range(width))
        eighths = int(max(0, min(100, pct)) * width * 8 / 100)
        full, rem = eighths // 8, eighths % 8
        shimmer = frame % max(full + 10, 1) - 4
        result = []
        for index in range(width):
            if index < full:
                result.append(self.paint(231 if -1 <= index - shimmer <= 1 else ORANGE, self.full))
            elif index == full and rem:
                result.append(self.paint(ORANGE, self.partial[rem - 1]))
            else:
                result.append(self.paint(MUTED, self.empty))
        return "".join(result)

    def _draw(self):
        while not self.stop.is_set():
            with self.lock:
                state = dict(self.state)
            columns = terminal_size()
            width = max(8, min(40, columns - (80 if columns >= 104 else 58)))
            tail = f"{state['pct']:5.1f}%  {state['speed']:<11}  ETA {state['eta']}" if state["pct"] is not None else f"{state['done']}  {state['speed']}"
            if columns >= 104 and state["pct"] is not None:
                tail += f"  {state['done']} / {state['total']}"
            print(f"\r\033[2K  {self.paint(ORANGE, self.spinner[self.frame % len(self.spinner)])} {state['label']:<16} {self._bar(width, self.frame, state['pct'])} {tail}", end="", flush=True)
            self.frame += 1
            time.sleep(0.1)

    def start(self):
        if not self.color:
            return
        print("\033[?25l", end="", flush=True)
        self.thread = threading.Thread(target=self._draw, daemon=True)
        self.thread.start()

    def finish(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=1)
            print("\r\033[2K", end="", flush=True)
        self.restore_cursor()

    def restore_cursor(self):
        if self.color:
            print("\033[?25h", end="", flush=True)
