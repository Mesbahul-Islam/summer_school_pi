from flask import Flask, render_template, jsonify
import paho.mqtt.client as mqtt
import json
from distance_sensor import sense_distance_and_motion  # Assuming this function is available
import threading
import time

app = Flask(__name__)

BROKER = "2823ed90a94448278aa9e1a1a2624e41.s1.eu.hivemq.cloud"
PORT = 8883
TOPIC = "test/sending"

# Variables to store motion, distance, and message
mqtt_message = None
motion = None
distance = None

# MQTT client callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global motion, distance, mqtt_message
    payload = json.loads(msg.payload.decode())
    motion = payload.get("motion")
    distance = payload.get("distance")
    mqtt_message = msg.payload.decode()  # Store the raw message
    print(f"Received message: {mqtt_message}")

def on_publish(client, userdata, mid):
    print(f"Message published with ID {mid}")

# Initialize MQTT client
client = mqtt.Client(userdata=None, protocol=mqtt.MQTTv5)
client.tls_set()
client.username_pw_set("testing", "Testing12345")
client.on_connect = on_connect
client.on_message = on_message
client.on_publish = on_publish

client.connect(BROKER, PORT, 60)

# Start MQTT client loop in a separate thread
def mqtt_loop():
    client.loop_forever()

# Run the MQTT client loop in a background thread
mqtt_thread = threading.Thread(target=mqtt_loop)
mqtt_thread.daemon = True
mqtt_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    # Call the function to get distance and motion from the sensor
    data = sense_distance_and_motion()  # Assuming it returns a tuple (motion, distance)
    motion = data[0]
    distance = data[1]

    # Return the latest motion, distance, and MQTT message as JSON
    return jsonify({
        "motion": motion,
        "distance": distance,
        "mqtt_message": mqtt_message
    })

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, host="0.0.0.0", port=5000)