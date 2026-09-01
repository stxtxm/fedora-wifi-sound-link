#!/usr/bin/env python3
# PWA Server for Pi - control Bluetooth + volume, serve PWA
# Run on Pi: python3 src/pwa/server.py --host 0.0.0.0 --port 8080
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
    # Pi status
    bt = run("bluetoothctl show 2>&1 | grep -E 'Powered|Discoverable|Pairable|Name' | head -5")
    devices = run("bluetoothctl devices 2>&1 | head -20")
    paired = run("bluetoothctl paired-devices 2>&1 | head -20")
    # fallback for paired
    if "Invalid" in paired:
        paired = run("bluetoothctl devices Paired 2>&1 | head -20")
    sink = run("pactl info 2>&1 | grep 'Default Sink' | head -1")
    vol = run("wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1 | head -1")
    aplay = run("aplay -l 2>&1 | grep AudioBox | head -5")
    connected = run("bluetoothctl info 2>&1 | grep Connected | head -5")
    return jsonify({
        "bluetooth": bt,
        "devices": devices,
        "paired": paired,
        "sink": sink,
        "volume": vol,
        "audiobox": aplay,
        "connected": connected
    })

@app.route("/api/bt/discoverable", methods=["POST"])
def bt_disc():
    data = request.json or {}
    on = data.get("on", True)
    cmd = "bluetoothctl discoverable on 2>&1 | head -5; bluetoothctl pairable on 2>&1 | head -5; sleep 1; bluetoothctl show 2>&1 | grep Discoverable"
    if not on:
        cmd = "bluetoothctl discoverable off 2>&1 | head -5; bluetoothctl pairable off 2>&1 | head -5"
    out = run(cmd, timeout=6)
    return jsonify({"out": out})

@app.route("/api/bt/scan", methods=["POST"])
def bt_scan():
    # scan 8s
    out = run("timeout 9 bash -c 'bluetoothctl scan on 2>&1 & pid=$!; sleep 8; bluetoothctl scan off 2>&1 | head -3; wait $pid 2>/dev/null; bluetoothctl devices 2>&1' 2>&1", timeout=12)
    return jsonify({"out": out})

@app.route("/api/bt/connect", methods=["POST"])
def bt_connect():
    mac = (request.json or {}).get("mac", "")
    if not re.match(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", mac, re.I):
        return jsonify({"error": "MAC invalide"}), 400
    out = run(f"bluetoothctl trust {mac} 2>&1 | tail -5; bluetoothctl pair {mac} 2>&1 | tail -10", timeout=15)
    return jsonify({"out": out})

@app.route("/api/bt/disconnect", methods=["POST"])
def bt_disc2():
    mac = (request.json or {}).get("mac", "")
    out = run(f"bluetoothctl disconnect {mac} 2>&1 | tail -10", timeout=5)
    return jsonify({"out": out})

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

@app.route("/api/bt/remove/<mac>", methods=["POST"])
def bt_remove(mac):
    out = run(f"bluetoothctl remove {mac} 2>&1 | tail -10", timeout=5)
    return jsonify({"out": out})

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--debug", action="store_true")
    args = p.parse_args()
    print(f"Serving PWA on http://{args.host}:{args.port} static={STATIC}")
    # ensure discoverable on start
    run("bluetoothctl discoverable on 2>&1 | head -2; bluetoothctl pairable on 2>&1 | head -2", timeout=3)
    app.run(host=args.host, port=args.port, debug=args.debug)
