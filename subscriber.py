#!/usr/bin/env python3
# encoding: utf-8

import json
import time
import threading
import signal
import sys
import paho.mqtt.client as mqtt
from gpiozero import LED

# ------- Display Class --------

class FourDigit7SegmentDisplay:
    def __init__(self):
        self.segments = {
            'a': LED(26, active_high=False),
            'b': LED(19, active_high=False),
            'c': LED(13, active_high=False),
            'd': LED(6, active_high=False),
            'e': LED(5, active_high=False),
            'f': LED(11, active_high=False),
            'g': LED(9, active_high=False),
            'dp': LED(10, active_high=False)
        }

        self.digits = [
            LED(12),
            LED(16),
            LED(20),
            LED(21)
        ]

        self.digit_codes = {
            0: [1,1,1,1,1,1,0],
            1: [0,1,1,0,0,0,0],
            2: [1,1,0,1,1,0,1],
            3: [1,1,1,1,0,0,1],
            4: [0,1,1,0,0,1,1],
            5: [1,0,1,1,0,1,1],
            6: [1,0,1,1,1,1,1],
            7: [1,1,1,0,0,0,0],
            8: [1,1,1,1,1,1,1],
            9: [1,1,1,1,0,1,1]
        }

        self.current_digits = [0, 0, 0, 0]
        self.dp_position = None
        self.clear()

    def clear(self):
        for segment in self.segments.values():
            segment.off()
        for digit in self.digits:
            digit.off()

    def set_display(self, values, dp_position=None):
        self.current_digits = values
        self.dp_position = dp_position

    def refresh(self, refresh_delay=0.005):
        for i in range(4):
            self.set_digit(i, self.current_digits[i], show_dp=(i == self.dp_position))
            time.sleep(refresh_delay)
            self.clear()

    def set_digit(self, digit_pos, number, show_dp=False):
        if not 0 <= digit_pos < 4 or number not in self.digit_codes:
            return

        segment_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        code = self.digit_codes[number]
        for i, segment_name in enumerate(segment_list):
            self.segments[segment_name].on() if code[i] else self.segments[segment_name].off()

        self.segments['dp'].on() if show_dp else self.segments['dp'].off()
        self.digits[digit_pos].on()

# ------- Global Display & State --------

display = FourDigit7SegmentDisplay()
occupancy_led = LED(18)  # Change if 18 is already used
last_valid_update = time.time()
display_lock = threading.Lock()
update_timeout = 60  # seconds

# ------- Display Thread --------

def display_loop():
    while True:
        with display_lock:
            if time.time() - last_valid_update > update_timeout:
                display.set_display([0, 0, 0, 0])  # Fallback
        display.refresh()

display_thread = threading.Thread(target=display_loop, daemon=True)
display_thread.start()

# ------- MQTT Handlers --------

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[MQTT] Connected with result code {rc}")
    client.subscribe("group3/command")
    print("[MQTT] Subscribed to topic: group3/command")

def on_message(client, userdata, msg):
    global last_valid_update
    try:
        payload = msg.payload.decode()
        print(f"[MQTT] Received: {payload}")
        data = json.loads(payload)

        state = data.get("occupancy_state", "").lower()
        confidence = data.get("confidence", "").lower()
        active_sensors_count = int(data.get("active_sensors_count", 0))

        # LED control
        if state == "occupied" and confidence == "high":
            occupancy_led.on()
            with display_lock:
                last_valid_update = time.time()
        else:
            occupancy_led.off()

        # Update display with sensor count (always 4 digits)
        digits = [int(d) for d in f"{active_sensors_count:0>4}"[-4:]]
        with display_lock:
            display.set_display(digits)

    except Exception as e:
        print(f"[ERROR] Invalid message: {e}")

# ------- MQTT Setup --------

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("172.20.10.4", 1883, 60)

# ------- Graceful Exit --------

def handle_exit(sig, frame):
    print("\n[System] Shutting down...")
    display.clear()
    occupancy_led.off()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# ------- Start MQTT Loop --------

print("[System] Display & MQTT Listener Running...")
client.loop_forever()