#!/bin/sh
# One line from nothing to ready, on macOS, Linux, WSL and Windows Git Bash:
#
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/sheetaldharshan200/munich-mobility-agents/main/get.sh)"
#
# PowerShell users: irm https://raw.githubusercontent.com/sheetaldharshan200/munich-mobility-agents/main/get.ps1 | iex
# (do not paste the curl line into PowerShell; curl is an alias there and rejects -fsSL)
#
# This only clones and calls install.py, so every platform runs one implementation.
# MUNICH_AGENTS_REPO / MUNICH_AGENTS_DIR override the source and the clone location.
set -e
REPO="${MUNICH_AGENTS_REPO:-https://github.com/sheetaldharshan200/munich-mobility-agents}"
DEST="${MUNICH_AGENTS_DIR:-$HOME/munich-mobility-agents}"

PY=""
for candidate in python3 python py; do
    path=$(command -v "$candidate" 2>/dev/null) || continue
    major=$("$path" -c 'import sys; print(sys.version_info[0])' 2>/dev/null) || continue
    if [ "$major" = "3" ]; then PY="$path"; break; fi
done
[ -n "$PY" ] || { echo "Python 3 is required but no working interpreter was found on PATH (tried python3, python, py)." >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "git is required but was not found on PATH." >&2; exit 1; }

if [ -d "$DEST/.git" ]; then
    printf 'Updating %s ... ' "$(basename "$DEST")"
    git -C "$DEST" pull --quiet --ff-only >/dev/null 2>&1 || true
    printf 'done\n'
else
    printf 'Cloning %s ... ' "$(basename "$DEST")"
    git clone --quiet "$REPO" "$DEST"
    printf 'done\n'
fi
exec "$PY" "$DEST/install.py" "$@"
