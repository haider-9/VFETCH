import atexit
import os
import sys
import threading
import time

from .util import terminal_size, unicode_ok

ORANGE, BLUE, GREEN, RED, MUTED, YELLOW = 208, 75, 114, 203, 245, 221

BANNER_ROWS = (
    "██╗   ██╗███████╗███████╗████████╗ ██████╗██╗  ██╗",
    "██║   ██║██╔════╝██╔════╝╚══██╔══╝██╔════╝██║  ██║",
    "██║   ██║█████╗  █████╗     ██║   ██║     ███████║",
    "╚██╗ ██╔╝██╔══╝  ██╔══╝     ██║   ██║     ██╔══██║",
    " ╚████╔╝ ██║     ███████╗   ██║   ╚██████╗██║  ██║",
    "  ╚═══╝  ╚═╝     ╚══════╝   ╚═╝    ╚═════╝╚═╝  ╚═╝",
)
BANNER_GRADIENT = (202, 208, 208, 214, 214, 220)


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
        self.processing = False
        self.last_label = None
        self.state = self._fresh_state()
        self.spinner = "|/-\\" if self.ascii else "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.full = "#" if self.ascii else "█"
        self.empty = "-" if self.ascii else "░"
        self.partial = (">",) * 7 if self.ascii else ("▏", "▎", "▍", "▌", "▋", "▊", "▉")
        self.scan = ("=",) * 5 if self.ascii else ("▒", "▓", "█", "▓", "▒")
        atexit.register(self.restore_cursor)

    @staticmethod
    def _fresh_state():
        return {"label": "CONNECTING", "pct": None, "speed": "--", "eta": "--:--",
                "done": "0.0 B", "total": "?"}

    # ── static output ──────────────────────────────────────
    def paint(self, code, text, bold=False):
        if not self.color:
            return text
        prefix = "\033[1m" if bold else ""
        return f"{prefix}\033[38;5;{code}m{text}{self.reset}"

    def line(self):
        print(f"  {self.paint(MUTED, ('-' if self.ascii else '─') * 56)}")

    def section(self, text):
        print(f"\n  {self.paint(ORANGE, text)}")
        self.line()

    def info(self, key, value):
        print(f"  {self.paint(MUTED, key.ljust(12))} {value}")

    def status(self, code, key, message):
        print(f"\n  {self.paint(code, '[' + key + ']', True)} {message}")

    def banner(self, engine, ffmpeg, output, version):
        rows = ("V F E T C H",) if self.ascii else BANNER_ROWS
        print()
        for index, row in enumerate(rows):
            print("  " + self.paint(BANNER_GRADIENT[min(index, 5)], row))
        print(f"\n  {self.paint(231, 'VIDEO DOWNLOADER', True)} {self.paint(MUTED, 'v' + version)}\n")
        self.line()
        self.info("ENGINE", f"yt-dlp {engine}")
        self.info("FFMPEG", self.paint(GREEN if ffmpeg else RED, "found" if ffmpeg else "missing")
                  + ("" if ffmpeg else " " + self.paint(MUTED, "(merging and MP3 disabled)")))
        self.info("SYSTEM", f"Python {sys.version_info.major}.{sys.version_info.minor} / {sys.platform.title()}")
        self.info("OUTPUT", str(output))
        self.info("MODE", "Single video, no playlist")
        self.line()

    # ── progress ───────────────────────────────────────────
    def update(self, **values):
        with self.lock:
            if "pct" in values:
                self.processing = False        # a download tick
            elif "label" in values:
                self.processing = True         # merge / convert / finalize step
            self.state.update(values)
            label = values.get("label")
            if not self.tty and label and label != self.last_label:
                # Piped output: no animation, just announce each stage once.
                print(f"  [{label}]", flush=True)
            if label:
                self.last_label = label

    def _bar(self, width, frame, pct):
        if pct is None:
            span = max(1, width - len(self.scan))
            pos = frame % (span * 2)
            pos = pos if pos <= span else span * 2 - pos
            cells = []
            for i in range(width):
                if pos <= i < pos + len(self.scan):
                    cells.append(self.paint(ORANGE, self.scan[i - pos]))
                else:
                    cells.append(self.paint(MUTED, self.empty))
            return "".join(cells)
        eighths = int(max(0, min(100, pct)) * width * 8 / 100)
        full, rem = eighths // 8, eighths % 8
        shimmer = frame % max(full + 10, 1) - 4
        cells = []
        for index in range(width):
            if index < full:
                cells.append(self.paint(231 if -1 <= index - shimmer <= 1 else ORANGE, self.full))
            elif index == full and rem:
                cells.append(self.paint(ORANGE, self.partial[rem - 1]))
            else:
                cells.append(self.paint(MUTED, self.empty))
        return "".join(cells)

    def _tail(self, state, processing, columns):
        pct = state["pct"]
        if processing:
            return self.paint(MUTED, "almost done...")
        if state["label"] == "CONNECTING":
            return self.paint(MUTED, "contacting server...")
        if pct is None:
            return f"{state['done']}  {state['speed']}"
        tail = f"{pct:5.1f}%  {state['speed']:<11}  ETA {state['eta']}"
        if columns >= 104:
            tail += f"  {state['done']} / {state['total']}"
        return tail

    def _draw(self):
        try:
            while not self.stop.is_set():
                with self.lock:
                    state = dict(self.state)
                    processing = self.processing
                columns = terminal_size()
                width = max(8, min(40, columns - (80 if columns >= 104 else 58)))
                bar = self._bar(width, self.frame, None if processing else state["pct"])
                spin = self.spinner[self.frame % len(self.spinner)]
                print(f"\r\033[2K  {self.paint(ORANGE, spin)} {state['label']:<16} {bar} "
                      f"{self._tail(state, processing, columns)}", end="", flush=True)
                self.frame += 1
                time.sleep(0.1)
        except Exception:
            pass  # never let a drawing glitch kill the download

    def start(self):
        with self.lock:
            self.state = self._fresh_state()
            self.processing = False
            self.last_label = "CONNECTING"
        self.frame = 0
        self.stop.clear()          # without this, a second download never animates
        if not self.tty:
            print("  Downloading...", flush=True)
            return
        print("\033[?25l", end="", flush=True)
        self.thread = threading.Thread(target=self._draw, daemon=True)
        self.thread.start()

    def finish(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
            print("\r\033[2K", end="", flush=True)
        self.restore_cursor()

    def restore_cursor(self):
        if self.tty:
            print("\033[?25h", end="", flush=True)