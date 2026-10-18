#!/usr/bin/env bash
set -euo pipefail
ROOT="${VFETCH_ROOT:-$HOME/.local/share/vfetch}"; BIN="$HOME/.local/bin"; mkdir -p "$ROOT" "$BIN"
if [ -f "$BIN/vfetch" ] && head -n 1 "$BIN/vfetch" | grep -q bash; then cp -n "$BIN/vfetch" "$BIN/vfetch.bak-bash" || true; fi
python3 -m venv "$ROOT/venv"; "$ROOT/venv/bin/python" -m pip install -U pip; "$ROOT/venv/bin/python" -m pip install -U "yt-dlp[default]" .
ln -sfn "$ROOT/venv/bin/vfetch" "$BIN/vfetch"; echo "Installed VFetch to $BIN/vfetch"
[ -x "$(command -v ffmpeg 2>/dev/null || true)" ] || echo "ffmpeg missing; install with: sudo apt install ffmpeg (or your package manager)"
