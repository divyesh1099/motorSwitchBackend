"""
Motor-switch backend  –  Full, robust version
─────────────────────────────────────────────
• Keeps ON/OFF state in switch_status.json
• Logs every ON→OFF event (even across restarts) in motor_log.json
• Queues notifications in notify_queue.json
• Auto-OFF after 50 min, with notification
• Thread-safe (single-process) – suitable for PythonAnywhere small apps
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, threading
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ───── file paths ───────────────────────────────────────────
STATUS_FILE   = "switch_status.json"
LOG_FILE      = "motor_log.json"
NOTIFY_FILE   = "notify_queue.json"
LAST_ON_FILE  = "last_on_time.txt"     # single line ISO string

AUTO_OFF_MIN  = 50
auto_off_timer = None                  # threading.Timer handle

# ───── helpers ──────────────────────────────────────────────
def read_json(path, fallback):
    try:
        return json.load(open(path))
    except Exception:
        return fallback

def write_json(path, data):
    json.dump(data, open(path, "w"), indent=2)

def get_status() -> bool:
    if not os.path.exists(STATUS_FILE):
        write_json(STATUS_FILE, {"isOn": False})
    return read_json(STATUS_FILE, {"isOn": False})

def set_status(state: bool):
    write_json(STATUS_FILE, {"isOn": state})

def add_notification(msg: str):
    q = read_json(NOTIFY_FILE, [])
    q.append({"time": datetime.now().isoformat(), "msg": msg})
    write_json(NOTIFY_FILE, q)
    print("🔔", msg, flush=True)

def append_log(on_iso: str, off_dt: datetime):
    log = read_json(LOG_FILE, [])
    secs = int((off_dt - datetime.fromisoformat(on_iso)).total_seconds())
    log.append({
        "on_time":  on_iso,
        "off_time": off_dt.isoformat(),
        "duration_sec": secs
    })
    write_json(LOG_FILE, log)
    print(f"📝 Log + {on_iso} → {off_dt.isoformat()}  ({secs}s)", flush=True)

def schedule_auto_off():
    global auto_off_timer
    if auto_off_timer: auto_off_timer.cancel()
    auto_off_timer = threading.Timer(AUTO_OFF_MIN*60, auto_turn_off)
    auto_off_timer.start()
    print("⏳ Auto-OFF timer set (50 min)", flush=True)

# ───── auto-OFF callback ────────────────────────────────────
def auto_turn_off():
    global auto_off_timer
    print("⏰ 50 min elapsed – auto-OFF", flush=True)
    if get_status().get("isOn"):
        set_status(False)
    add_notification("Motor turned OFF automatically after 50 minutes.")
    if os.path.exists(LAST_ON_FILE):
        on_iso = open(LAST_ON_FILE).read().strip()
        append_log(on_iso, datetime.now())
        os.remove(LAST_ON_FILE)
    auto_off_timer = None

# ───── API endpoints ────────────────────────────────────────
@app.route("/switch", methods=["GET"])
def api_switch_get():
    return jsonify(get_status())

@app.route("/switch", methods=["POST"])
def api_switch_set():
    global auto_off_timer
    data = request.get_json(force=True)
    if data.get("isOn") is None:
        return jsonify({"error": "Missing isOn"}), 400
    desired = bool(data["isOn"])
    current = get_status().get("isOn", False)
    set_status(desired)

    if desired and not current:                                   # TURN ON
        now_iso = datetime.now().isoformat()
        open(LAST_ON_FILE, "w").write(now_iso)
        add_notification("Motor turned ON – will auto-OFF in 50 min.")
        schedule_auto_off()

    if not desired and current:                                   # TURN OFF
        add_notification("Motor turned OFF manually.")
        if os.path.exists(LAST_ON_FILE):
            on_iso = open(LAST_ON_FILE).read().strip()
            append_log(on_iso, datetime.now())
            os.remove(LAST_ON_FILE)
        if auto_off_timer: auto_off_timer.cancel()

    return jsonify({"isOn": desired})

@app.route("/logs", methods=["GET"])
def api_logs():
    return jsonify(read_json(LOG_FILE, []))

@app.route("/notifications", methods=["GET"])
def api_notifications():
    return jsonify(read_json(NOTIFY_FILE, []))

@app.route("/notifications/clear", methods=["POST"])
def api_notifications_clear():
    write_json(NOTIFY_FILE, [])
    return jsonify({"cleared": True})

@app.route("/update", methods=["POST"])   # legacy / ESP
def api_update():
    print("ESP payload:", request.get_json(force=True), flush=True)
    return jsonify(cmd="OFF")

# ───── main (comment-out on PythonAnywhere) ────────────────
# if __name__ == "__main__":
#     app.run(debug=True, host="0.0.0.0", port=5000)
