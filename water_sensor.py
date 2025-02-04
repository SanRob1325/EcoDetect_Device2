from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import lgpio 
import os
import time
import requests 
import json
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
import boto3
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from dotenv import load_dotenv
import os

load_dotenv()

IOT_ENDPOINT = os.getenv("IOT_ENDPOINT")
THING_NAME = os.getenv("THING_NAME")
IOT_TOPIC = os.getenv("IOT_TOPIC")

CERTIFICATE_PATH = os.getenv("CERTIFICATE_PATH")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
ROOT_CA_PATH = os.getenv("ROOT_CA_PATH")

mqtt_client = AWSIoTMQTTClient(THING_NAME)
mqtt_client.configureEndpoint(IOT_ENDPOINT, 8883)
mqtt_client.configureCredentials(ROOT_CA_PATH, PRIVATE_KEY_PATH, CERTIFICATE_PATH)
mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
mqtt_client.configureOfflinePublishQueueing(-1)
mqtt_client.configureDrainingFrequency(2)
mqtt_client.configureConnectDisconnectTimeout(10)

try:
    mqtt_client.connect()
    print("Connected to AWS IoT Core")
except Exception as e:
    print(f"MQTT CONNECTION FAILED")


FLOW_SENSOR_PIN = 17
pulse_count = 0
calibration_factor = 7.5

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_input(h, FLOW_SENSOR_PIN)

def flow_callback(chip, gpio, level, tick):
    global pulse_count
    if level == 0:
        pulse_count += 1

lgpio.gpio_claim_alert(h, FLOW_SENSOR_PIN, lgpio.BOTH_EDGES)
lgpio.callback(h, FLOW_SENSOR_PIN, lgpio.BOTH_EDGES, flow_callback)

flow_rate_values = []

try:    
    while True:
        pulse_count_start = pulse_count
        time.sleep(1)
        pulse_count_end = pulse_count

        pulses_per_second = pulse_count_end - pulse_count_start
        flow_rate = pulses_per_second / calibration_factor

        flow_rate_values.append(flow_rate)
        if len(flow_rate_values) > 5:
            flow_rate_values.pop(0)
        smoothed_flow_rate = sum(flow_rate_values) / len(flow_rate_values)
        timestamp = datetime.now(timezone.utc).isoformat()

        sensor_data = {
            "device_id": THING_NAME,
            "timestamp": timestamp,
            "flow_rate": round(smoothed_flow_rate,2),
            "unit": "L/min"
        }
        try:
            mqtt_client.publish(IOT_TOPIC, json.dumps(sensor_data), 1)
            print(f"Flow Rate: {flow_rate:.2f} L/min | Sent to IoT Core")
        except Exception as e:
            print(f"MQTT Publishing Error: {e}")

except KeyboardInterrupt:
    print("\nExiting")

finally:
    print("Closing GPIO connection")
    lgpio.gpiochip_close(h)        
    print("GPIO Connection successfully closed")