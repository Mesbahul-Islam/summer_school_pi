from time import sleep
import paho.mqtt.client as mqtt
from paho import mqtt as bla
from distance_sensor import sense_distance_and_motion
import json
import os

# BROKER = "2823ed90a94448278aa9e1a1a2624e41.s1.eu.hivemq.cloud"
BROKER = "172.20.10.4"
PORT = 1883
TOPIC = "group3/status"
LOG_FILE = "sensor_data.json"

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    print(f"Received message: {msg.payload.decode()} on topic {msg.topic}")

def on_publish(client, userdata, mid):
    print(f"Message published with ID {mid}")


def main():
    client = mqtt.Client(userdata=None)

    # client.tls_set(tls_version=bla.client.ssl.PROTOCOL_TLS)
    # client.username_pw_set("testing", "Testing12345")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    try:
        while True:
            data = sense_distance_and_motion()
            motion = data[0]
            distance = data[1]

            payload = {
                "motion": motion,
                "distance": distance
            }

            json_payload = json.dumps(payload)

            # Send over MQTT
            result = client.publish(TOPIC, json_payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Success! Sent data: {json_payload}")
            else:
                print("Failed to publish message")

            sleep(3)
    except KeyboardInterrupt:
        print("Stopped by user")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()