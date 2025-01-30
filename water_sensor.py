from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import lgpio 
import os
import time
import requests 
import paho.mqtt.client as mqtt
from datetime import datetime

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


try:    
    while True:
        pulse_count_start = pulse_count
        time.sleep(1)
        pulse_count_end = pulse_count

        pulses_per_second = pulse_count_end - pulse_count_start
        flow_rate = pulses_per_second / calibration_factor

        print(f"Flow Rate: {flow_rate:.2f} L/min")

except KeyboardInterrupt:
    print("\nExiting")

finally:
    lgpio.gpiochip_close(h)        