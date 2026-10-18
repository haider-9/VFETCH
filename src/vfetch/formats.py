from dataclasses import dataclass
from typing import Any, Dict, List
from .util import human_bytes

CODECS = {"avc1": "H.264", "vp09": "VP9", "av01": "AV1", "hev1": "H.265", "hvc1": "H.265", "mp4a": "AAC", "opus": "Opus"}

def codec_name(codec):
    if not codec: return "—"
    for key, name in CODECS.items():
        if str(codec).startswith(key): return name
    return str(codec).split(".")[0]

def size_text(fmt: Dict[str, Any], duration=None) -> str:
    if fmt.get("filesize"): return human_bytes(fmt["filesize"])
    if fmt.get("filesize_approx"): return human_bytes(fmt["filesize_approx"])
    bitrate = fmt.get("tbr") or fmt.get("abr")
    if bitrate and duration: return "~" + human_bytes(float(bitrate) * 1000 * duration / 8)
    return "—"

def group_formats(info: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    result = {"VIDEO + AUDIO": [], "VIDEO ONLY": [], "AUDIO ONLY": [], "OTHER": []}
    for item in info.get("formats", []):
        if item.get("ext") in ("mhtml", "mjpeg") or item.get("protocol") == "mhtml": continue
        video, audio = item.get("vcodec"), item.get("acodec")
        if video and video != "none" and audio and audio != "none": group = "VIDEO + AUDIO"
        elif video and video != "none": group = "VIDEO ONLY"
        elif audio and audio != "none": group = "AUDIO ONLY"
        else: group = "OTHER"
        result[group].append(item)
    for key, values in result.items():
        values.sort(key=lambda x: (x.get("height") or 0, x.get("tbr") or x.get("abr") or 0, x.get("fps") or 0), reverse=True)
    return result

def best_pair(info):
    groups = group_formats(info)
    videos = groups["VIDEO ONLY"] or groups["VIDEO + AUDIO"]
    audios = groups["AUDIO ONLY"]
    return f"{videos[0].get('format_id')}+{audios[0].get('format_id')}" if videos and audios else (videos[0].get("format_id") if videos else "best")

def render_table(info, width=100, ascii_mode=False) -> str:
    title = str(info.get("title") or "Untitled")
    duration = info.get("duration")
    meta = f"{info.get('uploader') or 'Unknown'} · {duration or 0}s · {info.get('extractor_key') or info.get('extractor') or 'video'} · {len(info.get('formats', []))} formats"
    lines = [f"▶ {title[:max(10, width - 4)]}", f"  {meta}"]
    star = "*" if ascii_mode else "★"
    for name in ("VIDEO + AUDIO", "VIDEO ONLY", "AUDIO ONLY", "OTHER"):
        rows = group_formats(info)[name]
        if not rows: continue
        note = {"VIDEO + AUDIO":"single file, ready to play", "VIDEO ONLY":"merged with an audio stream", "AUDIO ONLY":"", "OTHER":"codec info not provided"}[name]
        lines += [f"\n{name} ({len(rows)})  {note}", "-" * min(width, 96)]
        for index, item in enumerate(rows):
            tag = f"{star} best" if index == 0 else ""
            if name == "AUDIO ONLY":
                row = f"{item.get('format_id','—'):>8} {codec_name(item.get('acodec')):<7} {item.get('ext','—'):<4} {item.get('abr') or item.get('tbr') or 0:>6}k {item.get('asr') or '—':>6} {size_text(item,duration):>10} {tag}"
            else:
                resolution = f"{item.get('width','?')}x{item.get('height','?')}" if item.get('height') else "—"
                row = f"{item.get('format_id','—'):>8} {resolution:<10} {str(item.get('fps') or '—'):>4} {codec_name(item.get('vcodec')):<7} {item.get('ext','—'):<4} {item.get('tbr') or 0:>6}k {size_text(item,duration):>10} {tag}"
            lines.append(row[:width])
    lines += [f"\n{star} Best pair, paste into option [3]:", f"  {best_pair(info)}"]
    rendered = "\n".join(lines)
    if ascii_mode:
        rendered = rendered.replace("—", "-").replace("▶", ">").replace("★", "*").replace("·", "|").replace("…", "...")
    return rendered
