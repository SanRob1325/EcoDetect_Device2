import time
import requests
import json
import lgpio
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration 
MAIN_PI = "http://192.168.42.123:5000/api/sensor-data-upload"
DEVICE_ID = "water_sensor_pi"
ROOM_ID = "bathroom"

# FLow sensor setup
FLOW_SENSOR_PIN = 17
pulse_count = 0
calibration_factor = 7.5 

# Initialise GPIO
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_input(h, FLOW_SENSOR_PIN)


# Callback function for pulse counting
def flow_callback(chip, gpio, level, tick):
    global pulse_count
    if level == 0: # Falling edge
        pulse_count += 1

# Setting up interrupt
lgpio.gpio_claim_alert(h, FLOW_SENSOR_PIN, lgpio.BOTH_EDGES)
lgpio.callback(h, FLOW_SENSOR_PIN, lgpio.BOTH_EDGES, flow_callback)

# Smoothens flow rate calculations
flow_rate_values = []

def collect_data():
    global pulse_count, flow_rate_values

    # Get pulse count difference over 1 second
    pulse_count_start = pulse_count
    time.sleep(1)
    pulse_count_end = pulse_count

    pulses_per_second = pulse_count_end - pulse_count_start
    flow_rate = pulses_per_second / calibration_factor

    # Applying smoothening
    flow_rate_values.append(flow_rate)
    if len(flow_rate_values) > 5:
        flow_rate_values.pop(0)
    smoothened_flow_rate = sum(flow_rate_values) / len(flow_rate_values)

    # Creating a data packet that the other room sensors have
    data = {
        "flow_rate": round(smoothened_flow_rate, 2),
        "unit": "L/min",
        "room_id": ROOM_ID,
        "device_id": DEVICE_ID,
        "location": ROOM_ID.capitalize(),
        # Inciding empty fileds for other sensors to mainatain compatability
        "temperature": None,
        "humidity": None,
        "pressure": None
    }    


    return data

def main_loop():
    print(f"Starting water flow sensor monitoring for {ROOM_ID}...")

    try:
        while True:
            try:
                data = collect_data()
                response = requests.post(MAIN_PI, json=data)
                print(f"[{datetime.now()}] Flow rate: {data['flow_rate']} L/min | Status: {response.status_code}")

                # Pause between readings 
                time.sleep(4) # Total cycle is 5 seconds
            except Exception as e:
                print(f"[{datetime.now()}] Failed to send data: {e}")
                time.sleep(5) # period to wait before trying
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        print("Cleaning up GPIO")
        lgpio.gpiochip_close(h)
        print("GPIO connection closed")

if __name__ == "__main__":
    main_loop()