from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import RPi.GPIO as GPIO
import os
import time
import requests 
from dotenv import load_dotenv
"""Water flow sensor"""
load_dotenv()
app = Flask(__name__)
CORS(app)

FLOW_SENSOR_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(FLOW_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

pulse_count = 0
last_time = time.time()
MAIN_PI_IP = os.getenv("MAIN_PI_IP")
if not MAIN_PI_IP:
    raise ValueError("Main PI IP has not been configured correctly in .env file")
"""Counts flow pulse"""
def count_pulse(channel):
    global pulse_count
    pulse_count += 1

GPIO.add_event_detect(FLOW_SENSOR_PIN,GPIO.RISING, callback=count_pulse)

def calculate_flow_rate():
    """
    Calculate the water flow in liters per minute
    """
    global pulse_count, last_time
    current_time = time.time()
    elapsed_time = current_time - last_time

    if elapsed_time <= 0:
        return 0.0
    
    flow_rate = (pulse_count / 450.0) / (elapsed_time / 60.0)
    pulse_count = 0
    last_time = current_time
    return round(flow_rate, 2)

@app.route('/api/water-flow', methods=['GET'])
def get_water_flow():
    """Calculates and returns the current waterflow rate"""
    try:
        flow_rate = calculate_flow_rate()
        return jsonify({"flow_rate": flow_rate, "timestamp": datetime.now().isoformat}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/send-water-flow', methods=['POST'])
def send_water_flow():
    """Calculates the flow rate and sends it to the main Raspberry Pi"""
    try:
        flow_rate = calculate_flow_rate()

        forward_url = f"http://{MAIN_PI_IP}:5000/api/water-flow"
        payload = {"flow_rate": flow_rate, "timestamp": datetime.now().isoformat()}
        response = requests.post(forward_url, json=payload)

        if response.status_code != 200:
            return jsonify({"error": f"Failed to send data to main Pi.Response: {response.text}"}), response.status_code
        
        return jsonify({"message": "Water flow data sent successfully", "flow_rate": flow_rate }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    try: 
        app.run(host='0.0.0.0', port=5001)

    except KeyboardInterrupt:
        print("Exiting...")
        GPIO.cleanup() 