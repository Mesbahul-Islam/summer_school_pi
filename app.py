# dashboard.py
from flask import Flask, render_template, jsonify
import threading
import json
import time
import paho.mqtt.client as mqtt
from paho import mqtt as bla

BROKER = "172.20.10.4"
PORT = 1883
TOPIC = "group3/status"

latest_data = {"motion": None, "distance": None}
history = []  # store readings as list of dicts

MAX_HISTORY = 100  # keep only last 100 points

# MQTT Callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global latest_data, history
    try:
        payload = json.loads(msg.payload.decode())
        timestamp = time.strftime("%H:%M:%S")  # format time
        latest_data = {
            "time": timestamp,
            "motion": payload["motion"],
            "distance": payload["distance"]
        }
        history.append(latest_data)
        if len(history) > MAX_HISTORY:
            history.pop(0)  # keep list small
        print(f"Updated dashboard data: {latest_data}")
    except json.JSONDecodeError:
        print("Invalid JSON received")

# MQTT Thread Function
def mqtt_thread():
    client = mqtt.Client(userdata=None)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

# Flask App
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def get_data():
    return jsonify(history)

if __name__ == "__main__":
    threading.Thread(target=mqtt_thread, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)