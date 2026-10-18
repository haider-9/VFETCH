#!/usr/bin/env bash
set -euo pipefail
ROOT="${VFETCH_ROOT:-$HOME/.local/share/vfetch}"; BIN="$HOME/.local/bin"; REPO="$(cd "$(dirname "$0")" && pwd)"; mkdir -p "$ROOT" "$BIN"
if [ "${1:-}" = "--uninstall" ]; then
	rm -f "$BIN/vfetch"; rm -rf "$ROOT"; echo "Uninstalled VFetch"; exit 0
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
	echo "ffmpeg is required by VFetch and was not found. Installing it first..."
	if command -v brew >/dev/null 2>&1; then
		brew install ffmpeg
	elif command -v apt-get >/dev/null 2>&1; then
		if [ "$(id -u)" -eq 0 ]; then apt-get update && apt-get install -y ffmpeg
		elif command -v sudo >/dev/null 2>&1; then sudo apt-get update && sudo apt-get install -y ffmpeg
		else echo "Cannot install ffmpeg: sudo is not available." >&2; exit 1; fi
	elif command -v dnf >/dev/null 2>&1; then
		if [ "$(id -u)" -eq 0 ]; then dnf install -y ffmpeg
		elif command -v sudo >/dev/null 2>&1; then sudo dnf install -y ffmpeg
		else echo "Cannot install ffmpeg: sudo is not available." >&2; exit 1; fi
	elif command -v pacman >/dev/null 2>&1; then
		if [ "$(id -u)" -eq 0 ]; then pacman -Sy --noconfirm ffmpeg
		elif command -v sudo >/dev/null 2>&1; then sudo pacman -Sy --noconfirm ffmpeg
		else echo "Cannot install ffmpeg: sudo is not available." >&2; exit 1; fi
	elif command -v zypper >/dev/null 2>&1; then
		if [ "$(id -u)" -eq 0 ]; then zypper --non-interactive install ffmpeg
		elif command -v sudo >/dev/null 2>&1; then sudo zypper --non-interactive install ffmpeg
		else echo "Cannot install ffmpeg: sudo is not available." >&2; exit 1; fi
	elif command -v apk >/dev/null 2>&1; then
		if [ "$(id -u)" -eq 0 ]; then apk add ffmpeg
		elif command -v sudo >/dev/null 2>&1; then sudo apk add ffmpeg
		else echo "Cannot install ffmpeg: sudo is not available." >&2; exit 1; fi
	else
		echo "Cannot install ffmpeg automatically. Install it with your system package manager and run this installer again." >&2
		exit 1
	fi
	command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg installation did not complete successfully." >&2; exit 1; }
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
