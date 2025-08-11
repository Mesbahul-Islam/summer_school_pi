from gpiozero import DistanceSensor, MotionSensor
from time import sleep

# Setup for HC-SR04 (Ultrasonic Sensor)
# TRIG = GPIO23 (pin 16), ECHO = GPIO17 (pin 11)
ultrasonic = DistanceSensor(echo=17, trigger=23)

# Setup for HC-SR501 (PIR Motion Sensor)
# Motion sensor connected to GPIO24 (pin 18)
pir = MotionSensor(24)


def sense_distance_and_motion():
    print("Starting sensor monitoring...")
    data = []
    if pir.motion_detected:
        data.append(1)
    else:
        data.append(0)

    distance = ultrasonic.distance * 100  # convert to cm
    data.append(distance)


    return data

def cleanup():
    print("Cleaning up GPIO resources...")
    # Close the individual sensor objects
    ultrasonic.close()
    pir.close()

    # Clean up all GPIO pins used by gpiozero
    from gpiozero import Device
    Device.pin_factory.cleanup()