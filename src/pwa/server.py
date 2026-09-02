#!/usr/bin/env python3
# PWA Server for Pi - WiFi Audio Stream Control + Volume + Bluetooth
import subprocess, re, json, os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, request

BASE = Path(__file__).parent
STATIC = BASE / "static"
app = Flask(__name__, static_folder=str(STATIC), static_url_path="")

def run(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except Exception as e:
        return str(e)

@app.route("/")
def index():
    return send_from_directory(STATIC, "index.html")

@app.route("/manifest.json")
def manifest():
    return send_from_directory(STATIC, "manifest.json")

@app.route("/sw.js")
def sw():
    return send_from_directory(STATIC, "sw.js")

@app.route("/api/status")
def api_status():
    ffmpeg_running = "ffmpeg" in run("ps aux | grep ffmpeg | grep -v grep", timeout=2)
    sink = run("pactl info 2>&1 | grep 'Default Sink' | head -1")
    vol = run("wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1 | head -1")
    aplay = run("aplay -l 2>&1 | grep AudioBox | head -5")
    bt_connected = run("bluetoothctl info 30:E0:44:79:F6:EA 2>&1 | grep Connected | head -1")
    return jsonify({
        "wifi_streaming": ffmpeg_running,
        "sink": sink,
        "volume": vol,
        "audiobox": aplay,
        "bt_connected": bt_connected
    })

@app.route("/api/wifi/start", methods=["POST"])
def wifi_start():
    data = request.json or {}
    codec = data.get("codec", "pcm")
    mode = data.get("mode", "stable")
    # Lance le receiver sur le Pi en arrière-plan
    run("pkill -9 ffmpeg", timeout=2)
    # Lancement local du receiver v2
    cmd = f"nohup /home/timo/dev/fedora-wifi-sound-link/src/stream/rpi_receiver.sh 192.168.1.108 {codec} {mode} 4711 > /tmp/rpi_recv.log 2>&1 &"
    out = run(cmd, timeout=3)
    return jsonify({"out": "WiFi Receiver started", "log": out})

@app.route("/api/wifi/stop", methods=["POST"])
def wifi_stop():
    out = run("pkill -9 ffmpeg", timeout=3)
    return jsonify({"out": "WiFi Stream stopped", "log": out})

@app.route("/api/volume", methods=["GET","POST"])
def volume():
    if request.method == "POST":
        v = request.json.get("volume", 50)
        try:
            v = int(v)
            frac = max(0, min(100, v))/100.0
            out = run(f"wpctl set-volume @DEFAULT_AUDIO_SINK@ {frac:.2f} 2>&1; wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1", timeout=3)
            return jsonify({"out": out, "volume": v})
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        out = run("wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1", timeout=3)
        m = re.search(r"Volume:\s*([\d\.]+)", out)
        vol = int(float(m.group(1))*100) if m else 0
        return jsonify({"volume": vol, "raw": out})

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8080)
    args = p.parse_args()
    print(f"Serving PWA WiFi on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port)
