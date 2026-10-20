from __future__ import annotations

import shutil
from typing import Any, Dict, List

from .util import human_bytes

CODECS = (
    ("avc1", "H.264"), ("h264", "H.264"), ("hev1", "H.265"), ("hvc1", "H.265"),
    ("hevc", "H.265"), ("vp09", "VP9"), ("vp9", "VP9"), ("vp8", "VP8"),
    ("av01", "AV1"), ("mp4a", "AAC"), ("opus", "Opus"), ("vorbis", "Vorbis"),
    ("mp3", "MP3"), ("ac-3", "AC-3"), ("ec-3", "E-AC-3"), ("flac", "FLAC"),
)

GROUP_NAMES = ("VIDEO + AUDIO", "VIDEO ONLY", "AUDIO ONLY", "OTHER")
GROUP_NOTES = {
    "VIDEO + AUDIO": "single file, ready to play",
    "VIDEO ONLY": "merged with an audio stream",
    "AUDIO ONLY": "",
    "OTHER": "codec info not provided",
}

# (key, header, align)
VIDEO_COLS = (("id", "ID", "l"), ("res", "RESOLUTION", "l"), ("fps", "FPS", "r"),
              ("codec", "CODEC", "l"), ("ext", "EXT", "l"), ("br", "BITRATE", "r"),
              ("bar", "", "l"), ("size", "SIZE", "r"), ("tag", "", "l"))
AUDIO_COLS = (("id", "ID", "l"), ("codec", "CODEC", "l"), ("ext", "EXT", "l"),
              ("br", "BITRATE", "r"), ("bar", "", "l"), ("asr", "SAMPLE", "r"),
              ("size", "SIZE", "r"), ("tag", "", "l"))

BAR_W = 8


def _num(x) -> float:
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else 0


def _bitrate(fmt: Dict[str, Any]) -> float:
    return _num(fmt.get("tbr")) or (_num(fmt.get("vbr")) + _num(fmt.get("abr")))


def codec_name(codec, dash: str = "—") -> str:
    if not codec or codec == "none":
        return dash
    low = str(codec).lower()
    for prefix, name in CODECS:
        if low.startswith(prefix):
            return name
    return str(codec).split(".")[0]


def size_text(fmt: Dict[str, Any], duration=None, dash: str = "—") -> str:
    if fmt.get("filesize"):
        return human_bytes(fmt["filesize"])
    if fmt.get("filesize_approx"):
        return "~" + human_bytes(fmt["filesize_approx"])
    bitrate = _bitrate(fmt)
    if bitrate and duration:
        return "~" + human_bytes(bitrate * 1000 / 8.0 * duration)
    return dash


def _kind(item: Dict[str, Any]) -> str:
    video, audio = item.get("vcodec"), item.get("acodec")
    has_v = video not in (None, "none")
    has_a = audio not in (None, "none")
    if has_v and has_a:
        return "VIDEO + AUDIO"
    if has_v:
        return "VIDEO ONLY"
    if has_a:
        return "AUDIO ONLY"
    return "OTHER"


def group_formats(info: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    result: Dict[str, List[Dict[str, Any]]] = {name: [] for name in GROUP_NAMES}
    for item in info.get("formats") or []:
        note = str(item.get("format_note") or "").lower()
        if item.get("ext") in ("mhtml", "mjpeg") or item.get("protocol") == "mhtml" or "storyboard" in note:
            continue
        result[_kind(item)].append(item)
    for name, values in result.items():
        if name == "AUDIO ONLY":
            values.sort(key=lambda x: (_num(x.get("abr")) or _bitrate(x)), reverse=True)
        else:
            values.sort(
                key=lambda x: (_num(x.get("height")), _bitrate(x), _num(x.get("fps"))),
                reverse=True,
            )
    return result


def best_pair(info: Dict[str, Any]) -> str:
    groups = group_formats(info)
    videos, audios, combined = groups["VIDEO ONLY"], groups["AUDIO ONLY"], groups["VIDEO + AUDIO"]
    if videos and audios:
        return f"{videos[0].get('format_id')}+{audios[0].get('format_id')}"
    if combined:
        return str(combined[0].get("format_id"))
    if videos:
        return str(videos[0].get("format_id"))
    return "best"


class _Style:
    OR, BL, GR, MU, WH, YE = "38;5;208", "38;5;75", "38;5;114", "38;5;245", "1;37", "38;5;221"
    OB = "1;38;5;208"

    def __init__(self, color: bool, ascii_mode: bool) -> None:
        self.color = color
        self.ascii = ascii_mode
        self.rule = "-" if ascii_mode else "─"
        self.star = "*" if ascii_mode else "★"
        self.dot = "|" if ascii_mode else "·"
        self.play = ">" if ascii_mode else "▶"
        self.dash = "-" if ascii_mode else "—"
        self.ell = "..." if ascii_mode else "…"
        self.full, self.empty = ("#", "-") if ascii_mode else ("█", "░")

    def paint(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.color else text


def _make_row(item: Dict[str, Any], kind: str, duration, st: _Style) -> Dict[str, Any]:
    tbr = _bitrate(item)
    if kind == "AUDIO ONLY":
        tbr = _num(item.get("abr")) or tbr
        codec = codec_name(item.get("acodec"), st.dash)
    elif kind == "VIDEO + AUDIO":
        codec = codec_name(item.get("vcodec"), st.dash) + "/" + codec_name(item.get("acodec"), st.dash)
    else:
        codec = codec_name(item.get("vcodec"), st.dash)
    width, height = item.get("width"), item.get("height")
    if width and height:
        res = f"{int(width)}x{int(height)}"
    elif height:
        res = f"{int(height)}p"
    else:
        res = st.dash
    dyn = item.get("dynamic_range")
    fps = item.get("fps")
    asr = item.get("asr")
    return {
        "id": str(item.get("format_id", "?")),
        "res": res,
        "height": _num(item.get("height")),
        "fps": f"{fps:g}" if isinstance(fps, (int, float)) and fps else "",
        "codec": codec,
        "ext": str(item.get("ext") or st.dash),
        "br": f"{round(tbr)}k" if tbr else st.dash,
        "tbr": tbr,
        "size": size_text(item, duration, st.dash),
        "asr": f"{asr / 1000.0:g}k" if isinstance(asr, (int, float)) and asr else "",
        "tag": dyn if dyn and dyn != "SDR" else "",
    }


def _render_group(rows, cols_def, idw: int, cols: int, st: _Style):
    mx = max([r["tbr"] for r in rows] + [0])
    present = []
    for key, head, align in cols_def:
        if key == "bar" and mx <= 0:
            continue
        if key in ("fps", "asr", "tag") and not any(r[key] for r in rows):
            continue
        present.append((key, head, align))

    def widths(cs):
        w = {}
        for key, head, _ in cs:
            if key == "bar":
                w[key] = BAR_W
            elif key == "id":
                w[key] = idw
            else:
                w[key] = max([len(head)] + [len(r[key]) for r in rows])
        return w

    def total_of(cs):
        return 2 + sum(widths(cs).values()) + 2 * (len(cs) - 1)

    for drop in ("bar", "ext", "fps", "asr", "tag"):
        if total_of(present) <= cols - 1:
            break
        present = [c for c in present if c[0] != drop]
    w = widths(present)

    def tier(r):
        h = r["height"]
        return st.GR if h >= 1080 else st.BL if h >= 720 else st.MU

    def styled(key, r, text):
        if text.strip() == st.dash:
            return st.paint(st.MU, text)
        code = {"id": st.WH, "res": tier(r), "codec": st.BL, "br": st.WH, "tag": st.YE}.get(key, st.MU)
        return st.paint(code, text)

    def bar(val):
        if not val or not mx:
            return st.paint(st.MU, st.empty * BAR_W)
        n = max(1, min(BAR_W, int(round(BAR_W * val / float(mx)))))
        return st.paint(st.OR, st.full * n) + st.paint(st.MU, st.empty * (BAR_W - n))

    lines = []
    head = [(h.rjust(w[k]) if a == "r" else h.ljust(w[k])) for k, h, a in present]
    lines.append("  " + st.paint(st.MU, "  ".join(head)).rstrip())
    for r in rows:
        parts = []
        for key, _, align in present:
            if key == "bar":
                parts.append(bar(r["tbr"]))
            else:
                text = r[key].rjust(w[key]) if align == "r" else r[key].ljust(w[key])
                parts.append(styled(key, r, text))
        lines.append("  " + "  ".join(parts).rstrip())
    return lines, total_of(present)


def render_table(info: Dict[str, Any], width=None, ascii_mode: bool = False, color: bool = False,
                 only=None) -> str:
    """Render the format tables. `only` restricts the output to the given group names (one tab)."""
    cols = width or shutil.get_terminal_size((100, 24)).columns
    st = _Style(color, ascii_mode)
    duration = info.get("duration")
    groups = group_formats(info)
    names = tuple(only) if only else GROUP_NAMES

    rows_by_group = {}
    for name in names:
        rows = [_make_row(item, name, duration, st) for item in groups[name]]
        if rows and name != "OTHER":
            rows[0]["tag"] = (st.star + " best " + rows[0]["tag"]).strip()
        rows_by_group[name] = rows
    all_rows = [r for name in names for r in rows_by_group[name]]
    idw = max([2] + [len(r["id"]) for r in all_rows])

    out = []
    title = " ".join(str(info.get("title") or "Untitled").split())
    maxw = max(20, cols - 6)
    if len(title) > maxw:
        title = title[: maxw - len(st.ell)] + st.ell
    out.append(f"  {st.paint(st.OR, st.play)} {st.paint(st.WH, title)}")

    dur = info.get("duration_string")
    if not dur and duration:
        d = int(duration)
        dur = f"{d // 3600}:{d % 3600 // 60:02d}:{d % 60:02d}" if d >= 3600 else f"{d // 60}:{d % 60:02d}"
    meta = [str(x) for x in (info.get("uploader") or info.get("channel"), dur,
                             info.get("extractor_key") or info.get("extractor"),
                             f"{len(all_rows)} formats") if x]
    out.append("    " + st.paint(st.MU, f" {st.dot} ".join(meta)))

    for name in names:
        rows = rows_by_group[name]
        if not rows:
            continue
        cols_def = AUDIO_COLS if name == "AUDIO ONLY" else VIDEO_COLS
        body, total = _render_group(rows, cols_def, idw, cols, st)
        sub = f"{len(rows)} {'format' if len(rows) == 1 else 'formats'}"
        if GROUP_NOTES[name]:
            sub += f"  {st.dot}  {GROUP_NOTES[name]}"
        out.append("")
        out.append(f"  {st.paint(st.OB, name)}  {st.paint(st.MU, sub)}")
        out.append("  " + st.paint(st.MU, st.rule * max(10, total - 2)))
        out.extend(body)

    if only is None and groups["VIDEO ONLY"] and groups["AUDIO ONLY"]:
        out.append("")
        out.append(f"  {st.paint(st.YE, st.star)} {st.paint(st.WH, 'Best pair')}"
                   + st.paint(st.MU, "  paste into option [3]:"))
        out.append("    " + st.paint(st.GR, best_pair(info)))

    rendered = "\n".join(out)
    if ascii_mode:
        rendered = rendered.encode("ascii", "replace").decode("ascii")
    return rendered