import paho.mqtt.client as mqtt
from paho import mqtt as bla
from gpiozero import LED
import json
import time

#BROKER = "2823ed90a94448278aa9e1a1a2624e41.s1.eu.hivemq.cloud"
BROKER = "10.117.156.225"
PORT = 1883
TOPIC = "group3/alert"
led = LED(27)
#USERNAME = "testing"
#PASSWORD = "Testing12345"


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(TOPIC)
    print(f"Subscribed to topic: {TOPIC}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print(f"Received message on topic {msg.topic}: {payload}")

        data = json.loads(payload)

        if data.get("status") == "intrusion_detected":
            led.on()
            time.sleep(1)
            led.off()

    except json.JSONDecodeError:
        print("Failed to decode JSON from message payload.")

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    print("Subscription successful")

# Create the MQTT client
client = mqtt.Client()
#client.tls_set(tls_version=bla.client.ssl.PROTOCOL_TLS)
#client.username_pw_set(USERNAME, PASSWORD)

# Attach callback functions
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe

# Connect to the broker
client.connect(BROKER, PORT, keepalive=60)

# Blocking loop to keep script running and receiving messages
client.loop_forever()