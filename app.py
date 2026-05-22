import time
import csv
import threading
import os
import socket
import urllib.request
from datetime import datetime
from flask import Flask, jsonify, render_template
from collections import deque

app = Flask(__name__)

# ── Config ──────────────────────────────────────────────
CSV_FILE    = "internet_log.csv"
INTERVAL    = 5
HISTORY_LEN = 60
CHECK_HOSTS = [
    ("google.com",  80),
    ("cloudflare.com", 80),
    ("amazon.com",  80),
]

# ── Shared state ─────────────────────────────────────────
lock         = threading.Lock()
history      = deque(maxlen=HISTORY_LEN)
uptime_start = None
last_down    = None

# ── Internet check (socket — works on all hosts) ─────────
def check_internet():
    for host, port in CHECK_HOSTS:
        try:
            start = time.time()
            sock = socket.create_connection((host, port), timeout=3)
            latency = round((time.time() - start) * 1000, 1)   # ms
            sock.close()
            return "Up", latency
        except OSError:
            continue
    return "Down", None

# ── CSV helper ───────────────────────────────────────────
def ensure_csv():
    if not os.path.isfile(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["Timestamp", "Status", "Latency"])

def append_csv(ts, status, latency):
    with open(CSV_FILE, "a", newline="") as f:
        csv.writer(f).writerow([ts, status, latency if latency is not None else "N/A"])

# ── Background monitor thread ────────────────────────────
def monitor():
    global uptime_start, last_down
    ensure_csv()

    while True:
        status, latency = check_internet()
        ts     = datetime.now()
        ts_str = ts.strftime("%d-%m-%Y %H:%M:%S")

        append_csv(ts_str, status, latency)

        with lock:
            if status == "Up" and uptime_start is None:
                uptime_start = ts
            elif status == "Down":
                last_down    = ts
                uptime_start = None

            history.append({
                "timestamp": ts_str,
                "status":    status,
                "latency":   latency,
            })

        print(f"{ts_str} --> {status} --> {latency} ms" if latency else f"{ts_str} --> {status}")
        time.sleep(INTERVAL)

# ── Flask routes ─────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    with lock:
        if not history:
            return jsonify({"error": "No data yet"}), 503

        latest    = history[-1]
        hist_list = list(history)

        # Uptime
        if uptime_start:
            delta   = datetime.now() - uptime_start
            hours   = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            uptime_str = f"{hours}h {minutes}m"
        else:
            uptime_str = "0m"

        # Packet loss
        recent   = hist_list[-20:]
        loss_pct = round(sum(1 for r in recent if r["status"] == "Down") / len(recent) * 100)

        # Chart points
        chart_points = [
            {"t": r["timestamp"][-8:-3], "v": r["latency"]}
            for r in hist_list[-20:]
        ]

        # Jitter
        latencies = [r["latency"] for r in recent if r["latency"] is not None]
        if len(latencies) >= 2:
            mean   = sum(latencies) / len(latencies)
            jitter = round((sum((x - mean) ** 2 for x in latencies) / len(latencies)) ** 0.5, 1)
        else:
            jitter = 0

        return jsonify({
            "status":       latest["status"],
            "latency":      latest["latency"],
            "uptime":       uptime_str,
            "packet_loss":  loss_pct,
            "jitter":       jitter,
            "chart":        chart_points,
            "last_updated": latest["timestamp"],
        })

@app.route("/api/history")
def api_history():
    with lock:
        return jsonify(list(history))

# ── Entry point ──────────────────────────────────────────
if __name__ == "__main__":
    t = threading.Thread(target=monitor, daemon=True)
    t.start()
    print("HomeNet running at http://localhost:5000")
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
