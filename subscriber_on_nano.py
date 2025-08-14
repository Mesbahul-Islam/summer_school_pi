import paho.mqtt.client as mqtt
import json
import time
import requests

BROKER = "172.20.10.4"
TOPICS = ["/group1/sensors", "group2/sensors/pir", "group2/sensors/ultrasonic", "group3/status"]

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:1.5b"

# Store sensor history for each sensor
sensor_history = {
    "group1": [],
    "group2_pir": [],
    "group2_ultrasonic": [],
    "group3": []
}
MAX_HISTORY = 10  # Keep last 10 readings per sensor
OCCUPANCY_DISTANCE_THRESHOLD = 50  # cm - within this range indicates presence
MIN_SENSORS_FOR_OCCUPANCY = 2  # Minimum sensors that must agree for occupancy confirmation
OCCUPANCY_TIMEOUT = 30  # seconds - no motion for this long = vacant

# Aggregated data for multi-sensor analysis
aggregated_data = {
    "latest_readings": {},
    "last_analysis_time": 0,
    "analysis_interval": 3,  # seconds between analyses
    "current_occupancy_state": "vacant",  # vacant, occupied, unknown
    "last_occupied_time": 0,
    "last_vacant_time": 0
}

def call_ollama(messages):
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": False
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")
    except Exception as e:
        print(f"Ollama call failed: {e}")
        return None

def detect_presence_pattern(sensor_history_list):
    """Check for consistent presence patterns in sensor history"""
    if len(sensor_history_list) < 3:
        return False, "insufficient_data"
    
    recent_readings = sensor_history_list[-5:]  # Last 5 readings
    motion_count = sum(1 for reading in recent_readings if reading.get("motion", 0) == 1)
    
    # Check for distances within occupancy range
    close_distances = [reading["distance"] for reading in recent_readings 
                      if "distance" in reading and reading["distance"] < OCCUPANCY_DISTANCE_THRESHOLD]
    
    # Presence indicators
    has_motion = motion_count > 0
    has_close_proximity = len(close_distances) > 0
    consistent_presence = motion_count >= 2 or len(close_distances) >= 3
    
    if has_motion and has_close_proximity:
        return True, "motion_and_proximity"
    elif consistent_presence:
        return True, "consistent_activity"
    else:
        return False, "no_presence_indicators"

def get_sensor_key_from_topic(topic):
    """Extract sensor key from topic"""
    if topic == "/group1/sensors":
        return "group1"
    elif topic == "group2/sensors/pir":
        return "group2_pir"
    elif topic == "group2/sensors/ultrasonic":
        return "group2_ultrasonic"
    elif topic == "group3/status":
        return "group3"
    return None

def analyze_group2_combined():
    """Analyze group2 PIR and ultrasonic sensors as a single combined sensor"""
    current_time = time.time()
    
    # Get latest readings from both group2 sensors
    pir_latest = None
    ultrasonic_latest = None
    
    if sensor_history["group2_pir"]:
        pir_reading = sensor_history["group2_pir"][-1]
        if current_time - pir_reading["ts"] <= 10:  # Recent data
            pir_latest = pir_reading
    
    if sensor_history["group2_ultrasonic"]:
        ultrasonic_reading = sensor_history["group2_ultrasonic"][-1]
        if current_time - ultrasonic_reading["ts"] <= 10:  # Recent data
            ultrasonic_latest = ultrasonic_reading
    
    # Combine group2 sensor data
    if not pir_latest and not ultrasonic_latest:
        return False, None  # No recent data from group2
    
    # Analyze combined group2 occupancy indicators
    group2_motion = False
    group2_distance = float('inf')
    group2_reasons = []
    
    if pir_latest:
        if pir_latest.get("motion", 0) == 1:
            group2_motion = True
            group2_reasons.append("pir_motion")
    
    if ultrasonic_latest:
        if ultrasonic_latest.get("motion", 0) == 1:
            group2_motion = True
            group2_reasons.append("ultrasonic_motion")
        
        distance = ultrasonic_latest.get("distance", float('inf'))
        group2_distance = min(group2_distance, distance)
        
        # Check presence pattern for ultrasonic
        presence_pattern, pattern_reason = detect_presence_pattern(sensor_history["group2_ultrasonic"])
        within_range = distance < OCCUPANCY_DISTANCE_THRESHOLD
        
        if within_range and presence_pattern:
            group2_reasons.append(f"ultrasonic_proximity_{pattern_reason}")
    
    # Determine if group2 indicates occupancy
    group2_indicates_occupancy = group2_motion or (group2_distance < OCCUPANCY_DISTANCE_THRESHOLD)
    
    if group2_indicates_occupancy:
        return True, {
            "sensor": "group2_combined",
            "motion": 1 if group2_motion else 0,
            "distance": group2_distance if group2_distance != float('inf') else "N/A",
            "occupancy_reason": ",".join(group2_reasons) if group2_reasons else "combined_detection",
            "pir_active": pir_latest is not None,
            "ultrasonic_active": ultrasonic_latest is not None
        }
    else:
        return False, None

def analyze_aggregated_data():
    """Analyze data from all sensors for occupancy detection"""
    current_time = time.time()
    
    # Check individual sensors (group1 and group3)
    active_sensors = []
    occupancy_sensors = []
    
    # Check group1 sensor
    if sensor_history["group1"]:
        latest = sensor_history["group1"][-1]
        if current_time - latest["ts"] <= 10:
            active_sensors.append("group1")
            
            motion_detected = latest.get("motion", 0) == 1
            distance = latest.get("distance", float('inf'))
            presence_pattern, pattern_reason = detect_presence_pattern(sensor_history["group1"])
            within_range = distance < OCCUPANCY_DISTANCE_THRESHOLD
            
            if motion_detected or (within_range and presence_pattern):
                occupancy_sensors.append({
                    "sensor": "group1",
                    "motion": latest.get("motion", 0),
                    "distance": latest.get("distance", "N/A"),
                    "occupancy_reason": f"motion:{motion_detected}, range:{within_range}, pattern:{pattern_reason}"
                })
    
    # Check group3 sensor
    if sensor_history["group3"]:
        latest = sensor_history["group3"][-1]
        if current_time - latest["ts"] <= 10:
            active_sensors.append("group3")
            
            motion_detected = latest.get("motion", 0) == 1
            distance = latest.get("distance", float('inf'))
            presence_pattern, pattern_reason = detect_presence_pattern(sensor_history["group3"])
            within_range = distance < OCCUPANCY_DISTANCE_THRESHOLD
            
            if motion_detected or (within_range and presence_pattern):
                occupancy_sensors.append({
                    "sensor": "group3",
                    "motion": latest.get("motion", 0),
                    "distance": latest.get("distance", "N/A"),
                    "occupancy_reason": f"motion:{motion_detected}, range:{within_range}, pattern:{pattern_reason}"
                })
    
    # Check group2 combined sensor
    group2_active, group2_data = analyze_group2_combined()
    if group2_active:
        active_sensors.append("group2_combined")
        if group2_data:
            occupancy_sensors.append(group2_data)
    
    print(f"Active sensors: {active_sensors}")
    print(f"Occupancy sensors: {[s['sensor'] for s in occupancy_sensors]}")
    
    # VOTING LOGIC: Need at least MIN_SENSORS_FOR_OCCUPANCY sensors to confirm occupancy
    occupancy_confirmed = len(occupancy_sensors) >= MIN_SENSORS_FOR_OCCUPANCY
    
    # Check for vacancy (no motion for OCCUPANCY_TIMEOUT seconds)
    last_motion_time = 0
    for readings in sensor_history.values():
        for reading in reversed(readings):
            if reading.get("motion", 0) == 1:
                last_motion_time = max(last_motion_time, reading["ts"])
                break
    
    time_since_motion = current_time - last_motion_time if last_motion_time > 0 else float('inf')
    vacancy_timeout = time_since_motion > OCCUPANCY_TIMEOUT
    
    # Determine occupancy state
    if vacancy_timeout:
        predicted_state = "vacant"  # If no motion for 30+ seconds, assume vacant
    elif occupancy_confirmed:
        predicted_state = "occupied"  # If sensors agree on occupancy
    else:
        predicted_state = "unknown" 
    
    print(f"Voting result: {len(occupancy_sensors)}/{len(active_sensors)} sensors indicate occupancy")
    print(f"Time since last motion: {time_since_motion:.1f}s (timeout: {OCCUPANCY_TIMEOUT}s)")
    print(f"Predicted state: {predicted_state}")
    
    # Prepare context for AI analysis
    context = {
        "occupancy_analysis": {
            "active_sensors": active_sensors,
            "occupancy_sensors": occupancy_sensors,
            "voting_result": f"{len(occupancy_sensors)}/{len(active_sensors)} sensors indicate occupancy",
            "voting_threshold": MIN_SENSORS_FOR_OCCUPANCY,
            "time_since_motion": time_since_motion,
            "vacancy_timeout": OCCUPANCY_TIMEOUT,
            "predicted_state": predicted_state,
            "current_state": aggregated_data["current_occupancy_state"],
            "group2_treated_as_single": True
        },
        "sensor_histories": {sensor: history[-3:] for sensor, history in sensor_history.items() if history},
        "latest_readings": aggregated_data["latest_readings"],
        "timestamp": current_time
    }

    system_prompt = (
        "You are an intelligent occupancy detection system analyzing multi-sensor data. "
        "Respond with 'OCCUPIED', 'VACANT', or 'UNKNOWN'. YOU DO NOT HAVE TO PROVIDE ANY REASON. "
        "Rules: "
        "- motion=1 means movement detected, motion=0 means no movement "
        "- distance in cm (smaller = closer to sensor) "
        "- group2_combined represents PIR and ultrasonic sensors working together as ONE sensor "
        "- group1 and group3 are individual sensors "
        "- Multiple sensors agreeing = higher confidence "
        "- Recent motion + close proximity = likely occupied "
        "- No motion for 30+ seconds = likely vacant "
        "- Consider sensor reliability and patterns "
        "Focus on determining current room/space occupancy status."
    )
    
    user_prompt = f"Analyze this occupancy data: {json.dumps(context, indent=2)}"

    response_text = call_ollama([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])

    if response_text is None:
        return None

    print(f"AI Occupancy Analysis: {response_text}")

    # Determine final occupancy state
    ai_state = "unknown"
    if "OCCUPIED" in response_text.upper():
        ai_state = "occupied"
    elif "VACANT" in response_text.upper():
        ai_state = "vacant"
    
    # Update occupancy state if changed
    previous_state = aggregated_data["current_occupancy_state"]
    if ai_state != "unknown" and ai_state != previous_state:
        aggregated_data["current_occupancy_state"] = ai_state
        if ai_state == "occupied":
            aggregated_data["last_occupied_time"] = current_time
        elif ai_state == "vacant":
            aggregated_data["last_vacant_time"] = current_time
        
        print(f"🏠 OCCUPANCY STATE CHANGED: {previous_state} → {ai_state}")
        
        # Send occupancy update to group3
        occupancy_data = {
            "occupancy_state": ai_state,
            "previous_state": previous_state,
            "voting_result": f"{len(occupancy_sensors)}/{len(active_sensors)} sensors",
            "occupancy_sensors": occupancy_sensors,
            "active_sensors": active_sensors,
            "ai_analysis": response_text,
            "timestamp": current_time,
            "confidence": "high" if len(occupancy_sensors) >= MIN_SENSORS_FOR_OCCUPANCY else "low"
        }
        
        # Publish occupancy status
        client.publish("group3/occupancy", json.dumps(occupancy_data))
        
        # Send command for occupancy-based actions
        client.publish("group3/command", json.dumps({
            "occupancy_state": ai_state,
            "confidence": occupancy_data["confidence"],
            "active_sensors_count": len(active_sensors)
        }))
        print(f"Occupancy update sent to group3: {ai_state}")
        print(f"Occupancy confidence: {occupancy_data['confidence']}")
    else:
        print(f"Occupancy state unchanged: {aggregated_data['current_occupancy_state']}")
    
    return response_text

def process_sensor_data(sensor_key, data):
    """Process data from a specific sensor"""
    # Add current reading to sensor history
    sensor_history[sensor_key].append({
        **data,
        "ts": round(time.time(), 2)
    })
    
    # Maintain history size
    if len(sensor_history[sensor_key]) > MAX_HISTORY:
        sensor_history[sensor_key].pop(0)
    
    # Update latest readings for aggregation
    aggregated_data["latest_readings"][sensor_key] = {
        **data,
        "timestamp": time.time()
    }
    
    # Print sensor-specific info
    if sensor_key == "group2_pir":
        print(f"{sensor_key}: motion={data.get('motion', 0)}")
    else:
        print(f"{sensor_key}: motion={data.get('motion', 0)}, distance={data.get('distance', 'N/A')}cm")

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    for topic in TOPICS:
        client.subscribe(topic)
        print(f"Subscribed to {topic}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        sensor_key = get_sensor_key_from_topic(topic)
        
        if sensor_key is None:
            return
            
        payload = json.loads(msg.payload.decode())
        print(f"Received from {topic}: {payload}")
        
        # Extract data based on sensor type
        if sensor_key == "group2_pir":
            # PIR sensor only has motion
            data = {
                "motion": int(payload.get("motion", 0))
            }
        elif sensor_key == "group1":
            # Group1 sensor uses distance_cm key
            data = {
                "motion": int(payload.get("motion_detected", 0)),
                "distance": float(payload.get("distance_cm", 999.0))
            }
        elif sensor_key == "group2_ultrasonic":
            # Ultrasonic sensor uses distance key
            data = {
                "distance": float(payload.get("distance_cm", 999.0))
            }
        else:
            # Other sensors use distance key
            data = {
                "distance": float(payload.get("distance", 999.0)),
                "motion": int(payload.get("motion", 0))
            }

        # Process data for this specific sensor
        process_sensor_data(sensor_key, data)
        
        current_time = time.time()
        
        # Perform occupancy analysis at intervals or when motion is detected
        if (data.get("motion", 0) == 1 or 
            current_time - aggregated_data["last_analysis_time"] > aggregated_data["analysis_interval"]):
            
            aggregated_data["last_analysis_time"] = current_time
            result = analyze_aggregated_data()
            
            if result:
                print(f"Occupancy Analysis Result: {result}")
            
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from {msg.topic}")
    except Exception as e:
        print(f"Error processing message from {msg.topic}: {e}")

def on_subscribe(client, userdata, mid, granted_qos):
    print(f"Subscribed with mid: {mid}, QoS: {granted_qos}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe


client.connect(BROKER, 1883, 60)
client.loop_forever()
