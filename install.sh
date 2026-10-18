#!/usr/bin/env bash
set -euo pipefail

ROOT="${VFETCH_ROOT:-$HOME/.local/share/vfetch}"
BIN="$HOME/.local/bin"
GIT_URL="git+https://github.com/haider-9/VFETCH.git${VFETCH_REF:+@$VFETCH_REF}"

die() { echo "Error: $*" >&2; exit 1; }

# ── Uninstall ──────────────────────────────────────────────
if [ "${1:-}" = "--uninstall" ]; then
	# Only remove the launcher if it is our symlink, never a user's own script.
	if [ -L "$BIN/vfetch" ] && [[ "$(readlink "$BIN/vfetch")" == "$ROOT/"* ]]; then
		rm -f "$BIN/vfetch"
	fi
	if [ ! -e "$BIN/vfetch" ] && [ -f "$BIN/vfetch.bak-bash" ]; then
		mv "$BIN/vfetch.bak-bash" "$BIN/vfetch"
		echo "Restored your previous bash vfetch."
	fi
	# Only delete a directory that really is a VFetch install.
	if [ -d "$ROOT/venv" ]; then rm -rf "$ROOT"; fi
	echo "Uninstalled VFetch."
	exit 0
fi

mkdir -p "$ROOT" "$BIN"

as_root() {
	if [ "$(id -u)" -eq 0 ]; then "$@"
	elif command -v sudo >/dev/null 2>&1; then echo "Running: sudo $*"; sudo "$@"
	else die "root or sudo is required to run: $*"; fi
}

# ── Where to install from: a local checkout, otherwise GitHub ──
SRC="$GIT_URL"
if [ -f "${BASH_SOURCE[0]:-}" ]; then
	DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
	if [ -f "$DIR/pyproject.toml" ]; then SRC="$DIR"; fi
fi
if [ "$SRC" = "$GIT_URL" ]; then
	command -v git >/dev/null 2>&1 || die "git is required to install from GitHub"
fi

# ── Python ─────────────────────────────────────────────────
PY="$(command -v python3 || true)"
[ -n "$PY" ] || die "python3 not found"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
	|| die "Python 3.10+ is required (adjust to match pyproject.toml)"

# ── ffmpeg ─────────────────────────────────────────────────
if ! command -v ffmpeg >/dev/null 2>&1; then
	echo "ffmpeg is required by VFetch and was not found. Installing it first..."
	if   command -v brew    >/dev/null 2>&1; then brew install ffmpeg
	elif command -v apt-get >/dev/null 2>&1; then as_root apt-get update && as_root apt-get install -y ffmpeg
	elif command -v dnf     >/dev/null 2>&1; then as_root dnf install -y ffmpeg-free
	elif command -v pacman  >/dev/null 2>&1; then as_root pacman -S --needed --noconfirm ffmpeg
	elif command -v zypper  >/dev/null 2>&1; then as_root zypper --non-interactive install ffmpeg
	elif command -v apk     >/dev/null 2>&1; then as_root apk add ffmpeg
	else die "cannot install ffmpeg automatically; install it and re-run"; fi
	command -v ffmpeg >/dev/null 2>&1 || die "ffmpeg installation did not complete successfully"
fi

# ── Back up an old bash-based vfetch (a real file, not our symlink) ──
if [ -f "$BIN/vfetch" ] && [ ! -L "$BIN/vfetch" ] && head -n 1 "$BIN/vfetch" | grep -q bash; then
	cp -n "$BIN/vfetch" "$BIN/vfetch.bak-bash" || true
fi

# ── Private venv (with pip, so `vfetch --update` works) ────
if command -v uv >/dev/null 2>&1; then
	uv venv --seed --allow-existing "$ROOT/venv"
	uv pip install --python "$ROOT/venv/bin/python" -U --reinstall-package vfetch "$SRC"
else
	"$PY" -m venv "$ROOT/venv" \
		|| die "venv creation failed (on Debian/Ubuntu: sudo apt install python3-venv)"
	"$ROOT/venv/bin/python" -m pip install -U pip
	"$ROOT/venv/bin/python" -m pip install -U "$SRC"
fi

ln -sfn "$ROOT/venv/bin/vfetch" "$BIN/vfetch"
"$BIN/vfetch" --version >/dev/null || die "install finished but 'vfetch --version' failed"
echo "Installed VFetch to $BIN/vfetch"

case ":$PATH:" in
	*":$BIN:"*) ;;
	*) echo "Note: $BIN is not on your PATH. Add this to your shell profile:"
	   echo "  export PATH=\"$BIN:\$PATH\"" ;;
esac