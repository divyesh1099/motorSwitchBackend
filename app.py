from flask import Flask, request, jsonify
import os
import json
import threading
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

STATUS_FILE = "switch_status.json"
LOG_FILE = "motor_log.json"
NOTIFY_FILE = "notify_queue.json"

AUTO_OFF_MINS = 50

# For tracking the current ON event and the auto-off timer
auto_off_timer = None
on_event = {}

def get_status():
    if not os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "w") as f:
            json.dump({"isOn": False}, f)
    with open(STATUS_FILE, "r") as f:
        return json.load(f)

def set_status(is_on):
    with open(STATUS_FILE, "w") as f:
        json.dump({"isOn": is_on}, f)

def append_log(on_time, off_time):
    duration_sec = int((off_time - on_time).total_seconds())
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                log = json.load(f)
            except:
                log = []
    log.append({
        "on_time": on_time.isoformat(),
        "off_time": off_time.isoformat(),
        "duration_sec": duration_sec
    })
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

def add_notification(msg):
    notif = []
    if os.path.exists(NOTIFY_FILE):
        with open(NOTIFY_FILE, "r") as f:
            try:
                notif = json.load(f)
            except:
                notif = []
    notif.append({
        "time": datetime.now().isoformat(),
        "msg": msg
    })
    with open(NOTIFY_FILE, "w") as f:
        json.dump(notif, f, indent=2)

def auto_turn_off():
    global auto_off_timer, on_event
    print("⏰ Auto-off: Turning motor OFF after 50 mins.", flush=True)
    set_status(False)
    off_time = datetime.now()
    add_notification("Motor turned OFF automatically after 50 mins.")
    if on_event.get("on_time"):
        append_log(on_event["on_time"], off_time)
    on_event = {}
    auto_off_timer = None

@app.route("/switch", methods=['GET'])
def get_switch():
    status = get_status()
    return jsonify(status)

@app.route("/switch", methods=['POST'])
def set_switch():
    global auto_off_timer, on_event
    data = request.get_json(force=True)
    is_on = data.get("isOn", None)
    if is_on is None:
        return jsonify({"error": "Missing isOn"}), 400

    current_status = get_status().get("isOn", False)
    set_status(bool(is_on))

    if bool(is_on) and not current_status:
        # Turned ON: set timer, log ON time, notify
        on_event["on_time"] = datetime.now()
        add_notification("Motor turned ON. Will turn OFF in 50 minutes automatically.")
        if auto_off_timer:
            auto_off_timer.cancel()
        auto_off_timer = threading.Timer(AUTO_OFF_MINS * 60, auto_turn_off)
        auto_off_timer.start()
    elif not bool(is_on) and current_status:
        # Turned OFF manually
        off_time = datetime.now()
        add_notification("Motor turned OFF manually.")
        if on_event.get("on_time"):
            append_log(on_event["on_time"], off_time)
        if auto_off_timer:
            auto_off_timer.cancel()
            auto_off_timer = None
        on_event = {}

    return jsonify({"isOn": bool(is_on)})

@app.route("/logs", methods=['GET'])
def get_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                log = json.load(f)
            except:
                log = []
    else:
        log = []
    return jsonify(log)

@app.route("/notifications", methods=['GET'])
def get_notifications():
    if os.path.exists(NOTIFY_FILE):
        with open(NOTIFY_FILE, "r") as f:
            try:
                notif = json.load(f)
            except:
                notif = []
    else:
        notif = []
    return jsonify(notif)

@app.route("/notifications/clear", methods=['POST'])
def clear_notifications():
    # You can clear notifications after showing in app/browser
    with open(NOTIFY_FILE, "w") as f:
        json.dump([], f)
    return jsonify({"cleared": True})

# Backward compatibility (your old ESP route, can keep or remove)
@app.route("/update", methods=['POST'])
def upd():
    data = request.get_json(force=True)
    print(f"ESP sent: {data}", flush=True)
    # Test: Always respond with OFF
    return jsonify(cmd="OFF")

# if __name__ == "__main__":
#     app.run(debug=True, host="0.0.0.0", port=5000)
