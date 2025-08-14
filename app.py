# dashboard.py
from flask import Flask, render_template, jsonify
import threading
import json
import time
import paho.mqtt.client as mqtt
from paho import mqtt as bla

BROKER = "172.20.10.4"
PORT = 1883
TOPICS = [
    "group3/status",
    "group2/sensors/ultrasonic",
    "group2/sensors/pir",
    "/group1/sensors",
    "group3/command"
]

latest_data = {
    "group3": {"motion": None, "distance": None, "time": None},
    "group2_ultrasonic": {"distance": None, "time": None},
    "group2_pir": {"motion": None, "time": None},
    "group1": {"motion":None, "distance": None}
    "occupancy" : {"occupancy": None, "confidence": None}
}
history = []  # store readings as list of dicts

MAX_HISTORY = 100  # keep only last 100 points

# MQTT Callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    for topic in TOPICS:
        client.subscribe(topic)

def on_message(client, userdata, msg):
    global latest_data
    timestamp = time.strftime("%H:%M:%S")

    try:
        payload = json.loads(msg.payload.decode())

        if msg.topic == "group3/status":
            latest_data["group3"] = {
                "time": timestamp,
                "motion": payload.get("motion"),
                "distance": payload.get("distance")
            }
        elif msg.topic == "group2/sensors/ultrasonic":
            latest_data["group2_ultrasonic"] = {
                "time": timestamp,
                "distance": payload.get("distance_cm")
            }
        elif msg.topic == "group2/sensors/pir":
            latest_data["group2_pir"] = {
                "time": timestamp,
                "motion": payload.get("motion_detected")
            }
        elif msg.topic == "/group1/sensors":
            latest_data["group1"] = {
                "motion": payload.get("motion_detected"),
                "distance": payload.get("distance_cm"),
                "timestamp": timestamp
            }
        elif msg.topic == "group3/command":
            latest_data["occupancy"] = {
            "occupancy" = payload.get("occupancy_state"),
            "confidence" = payload.get("confidence")}


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
    print(latest_data["group1"])
    return jsonify(latest_data)

if __name__ == "__main__":
    threading.Thread(target=mqtt_thread, daemon=True).start()
    app.run(host="0.0.0.0", port=5003, debug=True)