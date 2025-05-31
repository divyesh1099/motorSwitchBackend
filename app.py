from flask import Flask, request, jsonify
import os
import json

app = Flask(__name__)

STATUS_FILE = "switch_status.json"

def get_status():
    if not os.path.exists(STATUS_FILE):
        # Default: OFF
        with open(STATUS_FILE, "w") as f:
            json.dump({"isOn": False}, f)
    with open(STATUS_FILE, "r") as f:
        return json.load(f)

def set_status(is_on):
    with open(STATUS_FILE, "w") as f:
        json.dump({"isOn": is_on}, f)

@app.route("/switch", methods=['GET'])
def get_switch():
    status = get_status()
    return jsonify(status)

@app.route("/switch", methods=['POST'])
def set_switch():
    data = request.get_json(force=True)
    is_on = data.get("isOn", None)
    if is_on is None:
        return jsonify({"error": "Missing isOn"}), 400
    set_status(bool(is_on))
    return jsonify({"isOn": bool(is_on)})

# Backward compatibility (your old ESP route, can keep or remove)
@app.route("/update", methods=['POST'])
def upd():
    data = request.get_json(force=True)
    print(f"ESP sent: {data}", flush=True)
    # Test: Always respond with OFF
    return jsonify(cmd="OFF")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
