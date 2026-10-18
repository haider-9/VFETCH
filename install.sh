#!/usr/bin/env bash
set -euo pipefail
ROOT="${VFETCH_ROOT:-$HOME/.local/share/vfetch}"; BIN="$HOME/.local/bin"; REPO="$(cd "$(dirname "$0")" && pwd)"; mkdir -p "$ROOT" "$BIN"
if [ "${1:-}" = "--uninstall" ]; then
	rm -f "$BIN/vfetch"; rm -rf "$ROOT"; echo "Uninstalled VFetch"; exit 0
fi
if [ -f "$BIN/vfetch" ] && head -n 1 "$BIN/vfetch" | grep -q bash; then cp -n "$BIN/vfetch" "$BIN/vfetch.bak-bash" || true; fi
if command -v uv >/dev/null 2>&1; then
	uv venv "$ROOT/venv" --allow-existing
	uv pip install --python "$ROOT/venv/bin/python" -U "$REPO"
else
	python3 -m venv "$ROOT/venv"
	"$ROOT/venv/bin/python" -m pip install -U pip
	"$ROOT/venv/bin/python" -m pip install -U "$REPO"
fi
ln -sfn "$ROOT/venv/bin/vfetch" "$BIN/vfetch"; echo "Installed VFetch to $BIN/vfetch"
command -v ffmpeg >/dev/null 2>&1 || echo "ffmpeg missing; install with: sudo apt install ffmpeg (or your package manager)"
