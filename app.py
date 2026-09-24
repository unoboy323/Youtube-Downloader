#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template_string, request

APP_NAME = "YouTube Backup Downloader"
DEFAULT_FOLDER = Path.home() / "Downloads" / "YouTube Channel Backup"
APP_DIR = Path(__file__).resolve().parent
DENO_PATH = APP_DIR / ".deno" / "bin" / "deno"

app = Flask(__name__)

state_lock = threading.Lock()
state: dict[str, Any] = {
    "status": "idle",
    "percent": 0.0,
    "message": "Ready",
    "current_title": "",
    "speed": "",
    "eta": "",
    "downloaded": 0,
    "total": None,
    "last_file": "",
    "folder": str(DEFAULT_FOLDER),
    "log": deque(maxlen=250),
    "process": None,
    "stop_requested": False,
}

HTML = r'''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Backup Downloader</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f5f7;
      --card: #ffffff;
      --text: #171717;
      --muted: #616161;
      --border: #dedede;
      --primary: #b00020;
      --primary-dark: #850018;
      --soft: #fff1f3;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    main {
      width: min(900px, calc(100% - 32px));
      margin: 36px auto;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 28px;
      box-shadow: 0 12px 35px rgba(0,0,0,.06);
    }
    h1 { margin: 0 0 8px; font-size: clamp(28px, 5vw, 42px); }
    .lead { margin: 0 0 24px; color: var(--muted); line-height: 1.55; }
    label {
      display: block;
      font-weight: 700;
      margin: 18px 0 8px;
    }
    input, select, button { font: inherit; }
    input, select {
      width: 100%;
      min-height: 48px;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 11px 13px;
      background: white;
    }
    input:focus, select:focus {
      outline: 3px solid rgba(176,0,32,.13);
      border-color: var(--primary);
    }
    .folder-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
    }
    .buttons {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 22px;
    }
    button {
      min-height: 44px;
      border: 0;
      border-radius: 10px;
      padding: 10px 17px;
      cursor: pointer;
      font-weight: 750;
    }
    button.primary { background: var(--primary); color: white; }
    button.primary:hover { background: var(--primary-dark); }
    button.secondary { background: #ececec; color: #222; }
    button.danger { background: #2d2d2d; color: white; }
    button:disabled { opacity: .48; cursor: not-allowed; }
    .notice {
      margin-top: 22px;
      background: var(--soft);
      border-left: 4px solid var(--primary);
      padding: 14px 16px;
      border-radius: 8px;
      line-height: 1.45;
      color: #4d1a23;
    }
    .status-card {
      margin-top: 20px;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      background: #fafafa;
    }
    .status-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-top: 12px;
    }
    .stat {
      background: white;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
    }
    .stat strong { display: block; font-size: 13px; color: var(--muted); margin-bottom: 5px; }
    progress {
      width: 100%;
      height: 18px;
      margin-top: 14px;
      accent-color: var(--primary);
    }
    #currentTitle {
      overflow-wrap: anywhere;
      margin-top: 10px;
      font-weight: 650;
    }
    details { margin-top: 18px; }
    pre {
      background: #141414;
      color: #f1f1f1;
      border-radius: 10px;
      padding: 14px;
      max-height: 260px;
      overflow: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-size: 12px;
      line-height: 1.45;
    }
    .footer-note {
      color: var(--muted);
      font-size: 13px;
      margin: 18px 2px 0;
      line-height: 1.45;
    }
    @media (max-width: 650px) {
      main { width: min(100% - 20px, 900px); margin: 14px auto; }
      .card { padding: 20px; border-radius: 14px; }
      .folder-row { grid-template-columns: 1fr; }
      .status-grid { grid-template-columns: 1fr; }
      .buttons button { flex: 1 1 145px; }
    }
  </style>
</head>
<body>
<main>
  <section class="card">
    <h1>YouTube Backup Downloader</h1>
    <p class="lead">Paste a YouTube video, playlist, Shorts page, or channel Videos URL. Choose MP4 for video or MP3 for audio.</p>

    <label for="url">YouTube URL</label>
    <input id="url" type="url" placeholder="https://www.youtube.com/@YourChannel/videos" autocomplete="off">

    <label for="format">Download format</label>
    <select id="format">
      <option value="mp4" selected>MP4 - Video</option>
      <option value="mp3">MP3 - Audio only</option>
    </select>

    <div id="qualityGroup">
      <label for="quality">Video quality</label>
      <select id="quality">
        <option value="best">Best available</option>
        <option value="1080" selected>Up to 1080p</option>
        <option value="720">Up to 720p</option>
        <option value="480">Up to 480p</option>
      </select>
    </div>

    <label for="folder">Save location</label>
    <div class="folder-row">
      <input id="folder" type="text" value="{{ default_folder }}">
      <button class="secondary" id="browseButton" type="button">Choose Folder</button>
    </div>

    <div class="buttons">
      <button class="primary" id="downloadButton" type="button">Download MP4</button>
      <button class="danger" id="stopButton" type="button" disabled>Stop</button>
      <button class="secondary" id="openButton" type="button">Open Download Folder</button>
      <button class="secondary" id="closeButton" type="button">Close App</button>
    </div>

    <div class="notice">
      This can download videos that are publicly viewable. An unlisted video can be downloaded when you have its direct link. A private video cannot be recovered without access to the account that owns it.
    </div>

    <div class="status-card">
      <strong id="statusMessage">Ready</strong>
      <div id="currentTitle"></div>
      <progress id="progressBar" max="100" value="0"></progress>
      <div class="status-grid">
        <div class="stat"><strong>Current file</strong><span id="percent">0%</span></div>
        <div class="stat"><strong>Speed</strong><span id="speed">-</span></div>
        <div class="stat"><strong>Time remaining</strong><span id="eta">-</span></div>
      </div>
      <details>
        <summary>Show activity log</summary>
        <pre id="log">Ready</pre>
      </details>
    </div>

    <p class="footer-note">Use this only for videos you own or have permission to save. YouTube may occasionally change its delivery system, so the launcher checks for downloader updates when opened.</p>
  </section>
</main>
<script>
const urlInput = document.getElementById("url");
const formatInput = document.getElementById("format");
const qualityGroup = document.getElementById("qualityGroup");
const qualityInput = document.getElementById("quality");
const folderInput = document.getElementById("folder");
const downloadButton = document.getElementById("downloadButton");
const stopButton = document.getElementById("stopButton");
const browseButton = document.getElementById("browseButton");
const openButton = document.getElementById("openButton");
const closeButton = document.getElementById("closeButton");
const progressBar = document.getElementById("progressBar");
const statusMessage = document.getElementById("statusMessage");
const currentTitle = document.getElementById("currentTitle");
const percent = document.getElementById("percent");
const speed = document.getElementById("speed");
const eta = document.getElementById("eta");
const log = document.getElementById("log");

function updateFormatUI() {
  const isMp3 = formatInput.value === "mp3";
  qualityGroup.style.display = isMp3 ? "none" : "block";
  downloadButton.textContent = isMp3 ? "Download MP3" : "Download MP4";
}

formatInput.addEventListener("change", updateFormatUI);
updateFormatUI();

async function postJSON(path, payload = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}

downloadButton.addEventListener("click", async () => {
  try {
    const data = await postJSON("/api/start", {
      url: urlInput.value.trim(),
      format: formatInput.value,
      quality: qualityInput.value,
      folder: folderInput.value.trim()
    });
    statusMessage.textContent = data.message;
  } catch (error) {
    alert(error.message);
  }
});

stopButton.addEventListener("click", async () => {
  try {
    await postJSON("/api/stop");
  } catch (error) {
    alert(error.message);
  }
});

browseButton.addEventListener("click", async () => {
  try {
    const data = await postJSON("/api/select-folder");
    if (data.folder) folderInput.value = data.folder;
  } catch (error) {
    alert(error.message);
  }
});

openButton.addEventListener("click", async () => {
  try {
    await postJSON("/api/open-folder", {folder: folderInput.value.trim()});
  } catch (error) {
    alert(error.message);
  }
});

closeButton.addEventListener("click", async () => {
  try {
    await postJSON("/api/shutdown");
    document.body.innerHTML = "<main><section class='card'><h1>App closed</h1><p>You may close this browser tab.</p></section></main>";
  } catch (_) {
    window.close();
  }
});

async function refreshStatus() {
  try {
    const response = await fetch("/api/status", {cache: "no-store"});
    const data = await response.json();
    statusMessage.textContent = data.message || data.status;
    currentTitle.textContent = data.current_title || "";
    progressBar.value = Number(data.percent || 0);
    percent.textContent = `${Number(data.percent || 0).toFixed(1)}%`;
    speed.textContent = data.speed || "-";
    eta.textContent = data.eta || "-";
    log.textContent = (data.log || []).join("\n") || "Ready";
    log.scrollTop = log.scrollHeight;

    const running = data.status === "running" || data.status === "stopping";
    downloadButton.disabled = running;
    stopButton.disabled = !running;
    urlInput.disabled = running;
    formatInput.disabled = running;
    qualityInput.disabled = running;
    folderInput.disabled = running;
    browseButton.disabled = running;
  } catch (_) {}
}
refreshStatus();
setInterval(refreshStatus, 750);
</script>
</body>
</html>
'''

def add_log(line: str) -> None:
    clean = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
    if not clean:
        return
    with state_lock:
        state["log"].append(clean)

def snapshot() -> dict[str, Any]:
    with state_lock:
        return {
            "status": state["status"],
            "percent": state["percent"],
            "message": state["message"],
            "current_title": state["current_title"],
            "speed": state["speed"],
            "eta": state["eta"],
            "downloaded": state["downloaded"],
            "total": state["total"],
            "last_file": state["last_file"],
            "folder": state["folder"],
            "log": list(state["log"]),
        }

def set_state(**changes: Any) -> None:
    with state_lock:
        state.update(changes)

def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)

def find_ffmpeg() -> str:
    system_ffmpeg = shutil_which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError(f"FFmpeg could not be prepared: {exc}") from exc

def validate_youtube_url(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return host == "youtu.be" or host.endswith(".youtube.com") or host == "youtube.com"
    except Exception:
        return False

def format_args(quality: str) -> list[str]:
    base = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
    if quality in {"1080", "720", "480"}:
        base = (
            f"bv*[ext=mp4][height<={quality}]+ba[ext=m4a]/"
            f"b[ext=mp4][height<={quality}]/"
            f"bv*[height<={quality}]+ba/b[height<={quality}]/best[height<={quality}]"
        )
    return [
        "-f", base,
        "-S", "vcodec:h264,acodec:aac,quality,res,fps,hdr:12",
    ]

def build_command(url: str, folder: Path, quality: str, download_format: str) -> list[str]:
    ffmpeg_path = find_ffmpeg()
    archive = folder / (
        ".youtube-backup-downloaded-mp3.txt"
        if download_format == "mp3"
        else ".youtube-backup-downloaded.txt"
    )
    output_template = "%(channel)s/%(upload_date>%Y-%m-%d)s - %(title).180B [%(id)s].%(ext)s"

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--newline",
        "--no-colors",
        "--ignore-errors",
        "--continue",
        "--no-overwrites",
        "--yes-playlist",
        "--download-archive", str(archive),
        "--ffmpeg-location", ffmpeg_path,
        "--embed-metadata",
        "--remote-components", "ejs:github",
        "--progress-template",
        "download:PROGRESS|%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(info.title)s",
        "--print", "before_dl:ITEM|%(playlist_index)s|%(playlist_count)s|%(title)s",
        "--print", "after_move:FILE|%(filepath)s",
        "-P", str(folder),
        "-o", output_template,
    ]
    if DENO_PATH.exists():
        cmd.extend(["--js-runtimes", f"deno:{DENO_PATH}"])

    if download_format == "mp3":
        cmd.extend([
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
        ])
    else:
        cmd.extend([
            "--merge-output-format", "mp4",
            "--remux-video", "mp4",
        ])
        cmd.extend(format_args(quality))

    cmd.append(url)
    return cmd

def parse_line(line: str) -> None:
    add_log(line)
    clean = line.strip()

    if clean.startswith("ITEM|"):
        parts = clean.split("|", 3)
        index = parts[1].strip() if len(parts) > 1 else ""
        count = parts[2].strip() if len(parts) > 2 else ""
        title = parts[3].strip() if len(parts) > 3 else ""
        downloaded = int(index) - 1 if index.isdigit() else 0
        total = int(count) if count.isdigit() else None
        label = f"Preparing video {index}" if index and index != "NA" else "Preparing video"
        if count and count != "NA":
            label += f" of {count}"
        set_state(
            message=label,
            current_title=title,
            downloaded=max(downloaded, 0),
            total=total,
            percent=0.0,
            speed="",
            eta="",
        )
        return

    if clean.startswith("PROGRESS|"):
        parts = clean.split("|", 4)
        percent_text = parts[1].replace("%", "").strip() if len(parts) > 1 else "0"
        speed_text = parts[2].strip() if len(parts) > 2 else ""
        eta_text = parts[3].strip() if len(parts) > 3 else ""
        title = parts[4].strip() if len(parts) > 4 else ""
        try:
            pct = float(percent_text)
        except ValueError:
            pct = 0.0
        set_state(
            message="Downloading",
            percent=max(0.0, min(pct, 100.0)),
            speed="" if speed_text == "NA" else speed_text,
            eta="" if eta_text == "NA" else eta_text,
            current_title=title,
        )
        return

    if clean.startswith("FILE|"):
        filepath = clean.split("|", 1)[1].strip()
        with state_lock:
            state["downloaded"] = int(state.get("downloaded", 0)) + 1
            state["last_file"] = filepath
            state["percent"] = 100.0
            state["message"] = "Saved file"
        return

    lowered = clean.lower()
    if "sign in to confirm" in lowered:
        set_state(message="YouTube requested account verification for this video.")
    elif "error:" in lowered:
        set_state(message="A video could not be downloaded. See the activity log.")

def download_worker(url: str, folder: Path, quality: str, download_format: str) -> None:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        set_state(
            status="running",
            percent=0.0,
            message="Starting downloader",
            current_title="",
            speed="",
            eta="",
            downloaded=0,
            total=None,
            last_file="",
            folder=str(folder),
            stop_requested=False,
        )
        add_log(f"Saving files to: {folder}")
        cmd = build_command(url, folder, quality, download_format)

        env = os.environ.copy()
        env["PATH"] = str(DENO_PATH.parent) + os.pathsep + env.get("PATH", "")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        set_state(process=process)

        assert process.stdout is not None
        for line in process.stdout:
            parse_line(line)
            with state_lock:
                if state.get("stop_requested"):
                    break

        return_code = process.wait()
        with state_lock:
            stopped = bool(state.get("stop_requested"))

        if stopped:
            set_state(status="stopped", message="Download stopped", process=None, speed="", eta="")
            add_log("Download stopped by user.")
        elif return_code == 0:
            set_state(status="complete", message="Backup complete", process=None, percent=100.0, speed="", eta="")
            add_log("All available videos finished.")
        else:
            set_state(status="error", message="Downloader finished with an error. Check the activity log.", process=None, speed="", eta="")
            add_log(f"Downloader exited with code {return_code}.")
    except Exception as exc:
        set_state(status="error", message=str(exc), process=None, speed="", eta="")
        add_log(f"ERROR: {exc}")

@app.get("/")
def index():
    return render_template_string(HTML, default_folder=str(DEFAULT_FOLDER))

@app.get("/api/status")
def api_status():
    return jsonify(snapshot())

@app.post("/api/start")
def api_start():
    payload = request.get_json(silent=True) or {}
    url = str(payload.get("url", "")).strip()
    download_format = str(payload.get("format", "mp4")).strip().lower()
    quality = str(payload.get("quality", "1080")).strip()
    folder_text = str(payload.get("folder", DEFAULT_FOLDER)).strip()

    if not url:
        return jsonify(error="Paste the YouTube video, playlist, or channel URL first."), 400
    if not validate_youtube_url(url):
        return jsonify(error="That does not look like a YouTube URL."), 400
    if download_format not in {"mp4", "mp3"}:
        return jsonify(error="Choose MP4 or MP3."), 400
    if quality not in {"best", "1080", "720", "480"}:
        return jsonify(error="Choose a valid video quality."), 400
    if not folder_text:
        return jsonify(error="Choose a save location."), 400

    with state_lock:
        if state["status"] in {"running", "stopping"}:
            return jsonify(error="A download is already running."), 409

    folder = Path(os.path.expandvars(os.path.expanduser(folder_text))).resolve()
    thread = threading.Thread(
        target=download_worker,
        args=(url, folder, quality, download_format),
        daemon=True,
    )
    thread.start()
    return jsonify(message="Starting download")

@app.post("/api/stop")
def api_stop():
    with state_lock:
        process = state.get("process")
        if not process or state["status"] not in {"running", "stopping"}:
            return jsonify(error="There is no active download."), 409
        state["stop_requested"] = True
        state["status"] = "stopping"
        state["message"] = "Stopping download"

    try:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    except Exception as exc:
        add_log(f"Could not stop cleanly: {exc}")
    return jsonify(message="Stopping")

@app.post("/api/select-folder")
def api_select_folder():
    if sys.platform != "darwin":
        return jsonify(error="The folder chooser in this version is made for macOS."), 400
    script = 'POSIX path of (choose folder with prompt "Choose where the MP4 videos should be saved")'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        return jsonify(folder="")
    return jsonify(folder=result.stdout.strip())

@app.post("/api/open-folder")
def api_open_folder():
    payload = request.get_json(silent=True) or {}
    folder_text = str(payload.get("folder", state.get("folder", DEFAULT_FOLDER))).strip()
    folder = Path(os.path.expandvars(os.path.expanduser(folder_text))).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])
    elif sys.platform.startswith("win"):
        os.startfile(str(folder))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(folder)])
    return jsonify(message="Folder opened")

@app.post("/api/shutdown")
def api_shutdown():
    with state_lock:
        process = state.get("process")
    if process and process.poll() is None:
        try:
            process.terminate()
        except Exception:
            pass
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return jsonify(message="Closing")

def choose_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])

def open_browser(url: str) -> None:
    time.sleep(1.0)
    webbrowser.open(url)

if __name__ == "__main__":
    port = choose_port()
    url = f"http://127.0.0.1:{port}"
    print(f"{APP_NAME} is running at {url}", flush=True)
    print("Keep this Terminal window open while using the app.", flush=True)
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False)
