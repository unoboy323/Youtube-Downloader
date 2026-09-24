#!/bin/bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"
clear

echo "YouTube Backup Downloader"
echo "========================="
echo

show_error() {
  /usr/bin/osascript -e "display alert \"YouTube Backup Downloader\" message \"$1\" as critical" >/dev/null 2>&1 || true
}

if ! command -v python3 >/dev/null 2>&1; then
  show_error "Python 3 is required. Install the current Python 3 release from python.org, then open this app again."
  open "https://www.python.org/downloads/macos/"
  exit 1
fi

if ! python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  show_error "Python 3.10 or newer is required. Install the current Python 3 release from python.org, then open this app again."
  open "https://www.python.org/downloads/macos/"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Preparing the app for first use..."
  python3 -m venv .venv
fi

source ".venv/bin/activate"

echo "Checking required components..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet --upgrade --pre "yt-dlp[default]" Flask imageio-ffmpeg

if [ ! -x ".deno/bin/deno" ]; then
  echo "Installing the local YouTube JavaScript helper..."
  mkdir -p ".deno"
  if ! curl -fsSL https://deno.land/install.sh | DENO_INSTALL="$APP_DIR/.deno" sh; then
    show_error "The JavaScript helper could not be installed. Check your internet connection and try again."
    exit 1
  fi
fi

export PATH="$APP_DIR/.deno/bin:$PATH"

echo
echo "Opening the app in your browser..."
echo "Keep this Terminal window open while downloading."
echo
python app.py

echo
echo "The app has closed. You may close this window."
