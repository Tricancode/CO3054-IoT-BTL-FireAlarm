#!/usr/bin/env python3
"""
verify_telemetry.py

Gateway Telemetry Simulator and Verification Script.
Connects to local ThingsBoard MQTT broker (localhost:1883) using the device access token
'i2tchqq1390qcxhun4zr', publishes live fire alarm sensor telemetry, and listens for RPC commands.
"""

import os
import sys
import json
import time
import logging
import threading
from pathlib import Path
import paho.mqtt.client as mqtt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from ui.isolation_detector import IsolationDetector

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("TB_Gateway")

# MQTT Configuration
MQTT_HOST = os.getenv("TB_MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("TB_MQTT_PORT", "1883"))
DEVICE_TOKEN = os.getenv("TB_DEVICE_TOKEN", "i2tchqq1390qcxhun4zr")

TELEMETRY_TOPIC = "v1/devices/me/telemetry"
RPC_REQUEST_TOPIC = "v1/devices/me/rpc/request/+"

# Device Actuator States
actuator_state = {
    "servo": False,
    "buzzer": False,
    "led": False
}

published_count = 0
publish_ack_event = threading.Event()
anomaly_detector = IsolationDetector()


def create_mqtt_client(client_id="FireAlarm_Gateway_Node"):
    """Instantiates a Paho MQTT client compatible with versions 1.x and 2.x."""
    try:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            client_id=client_id
        )
    except AttributeError:
        client = mqtt.Client(client_id=client_id)
    
    client.username_pw_set(DEVICE_TOKEN)
    return client


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Successfully connected to ThingsBoard MQTT Broker ({MQTT_HOST}:{MQTT_PORT})")
        client.subscribe(RPC_REQUEST_TOPIC)
        logger.info(f"Subscribed to RPC requests: '{RPC_REQUEST_TOPIC}'")
    else:
        logger.error(f"Failed to connect to MQTT broker, return code: {rc}")


def on_publish(client, userdata, mid):
    global published_count
    published_count += 1
    logger.info(f"Message published successfully (mid={mid}, total_published={published_count})")
    publish_ack_event.set()


def on_message(client, userdata, msg):
    """Handles incoming RPC commands from ThingsBoard dashboard."""
    logger.info(f"Received RPC on topic '{msg.topic}': {msg.payload.decode('utf-8')}")
    try:
        request_id = msg.topic.split("/")[-1]
        data = json.loads(msg.payload.decode("utf-8"))
        method = data.get("method")
        params = data.get("params", False)

        response_payload = {}
        if method in ("getServo", "getServoStatus"):
            response_payload = {"servo": actuator_state["servo"]}
        elif method in ("setServo", "setServoStatus"):
            actuator_state["servo"] = bool(params)
            response_payload = {"servo": actuator_state["servo"]}
            logger.info(f"RPC: Servo set to {actuator_state['servo']}")
        elif method in ("getBuzzer", "getBuzzerStatus"):
            response_payload = {"buzzer": actuator_state["buzzer"]}
        elif method in ("setBuzzer", "setBuzzerStatus"):
            actuator_state["buzzer"] = bool(params)
            response_payload = {"buzzer": actuator_state["buzzer"]}
            logger.info(f"RPC: Buzzer set to {actuator_state['buzzer']}")
        elif method in ("getLed", "getLedStatus"):
            response_payload = {"led": actuator_state["led"]}
        elif method in ("setLed", "setLedStatus"):
            actuator_state["led"] = bool(params)
            response_payload = {"led": actuator_state["led"]}
            logger.info(f"RPC: LED set to {actuator_state['led']}")
        else:
            response_payload = {"status": "ok"}

        response_topic = f"v1/devices/me/rpc/response/{request_id}"
        client.publish(response_topic, json.dumps(response_payload))
        logger.info(f"Responded to RPC '{method}' on topic '{response_topic}'")

    except Exception as e:
        logger.error(f"Error parsing RPC message: {e}")


def generate_telemetry_sample(iteration: int) -> dict:
    """Generate readings and score them with the same detector as the gateway."""
    flame_detected = 1 if iteration >= 3 else 0
    # Match the firmware's raw 12-bit MQ-2 ADC scale and 1800 alarm threshold.
    smoke_adc = 1900.0 + (iteration * 25.5) if flame_detected else 250.0 + (iteration * 10)
    temperature = 55.0 + (iteration * 2.1) if flame_detected else 24.5 + (iteration % 3)

    if flame_detected:
        actuator_state["servo"] = True
        actuator_state["buzzer"] = True
        actuator_state["led"] = True

    is_anomaly, anomaly_score = anomaly_detector.update_and_predict(
        smoke_adc, temperature, flame_detected
    )

    return {
        "smoke": round(smoke_adc, 2),
        "flame": flame_detected,
        "temperature": round(temperature, 2),
        "is_anomaly": is_anomaly,
        "anomaly_score": anomaly_score,
        "servo": actuator_state["servo"],
        "buzzer": actuator_state["buzzer"],
        "led": actuator_state["led"]
    }


def verify_telemetry_transmission(cycles: int = 5, duration_sec: float = 1.0) -> bool:
    """Connects to broker, publishes telemetry cycles, and verifies delivery."""
    client = create_mqtt_client()
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_message = on_message

    logger.info(f"Connecting to MQTT Broker at {MQTT_HOST}:{MQTT_PORT}...")
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    except Exception as e:
        logger.warning(f"Could not connect to live MQTT broker ({MQTT_HOST}:{MQTT_PORT}): {e}")
        return False

    client.loop_start()
    success = True

    try:
        for i in range(1, cycles + 1):
            publish_ack_event.clear()
            telemetry = generate_telemetry_sample(i)
            payload = json.dumps(telemetry)
            logger.info(f"Publishing telemetry [{i}/{cycles}]: {payload}")
            
            res = client.publish(TELEMETRY_TOPIC, payload, qos=1)
            if not publish_ack_event.wait(timeout=5.0):
                logger.warning(f"Publish ACK timeout on cycle {i}")
                success = False

            time.sleep(duration_sec)
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("MQTT Client disconnected.")

    return success


if __name__ == "__main__":
    cycles_to_run = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    ok = verify_telemetry_transmission(cycles=cycles_to_run)
    sys.exit(0 if ok else 1)
