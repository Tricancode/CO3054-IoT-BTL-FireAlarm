#!/usr/bin/env python3
"""
test_rulechain_alert.py
=======================
4-Stage Verification Script for CoreIOT / ThingsBoard RuleChain (T12) & Telegram Alerts (T13).

Stages tested in sequence (matching thresholds in LocalGateway.py & gateway_infrastructure.py):
1. SAFE     : smoke < 35.0 ppm, flame = 0, is_anomaly = 0 -> Baseline, no alarm, no lockdown RPC.
2. WARNING  : 35.0 <= smoke <= 60.0 ppm, flame = 0, is_anomaly = 1 -> FIRE_ALARM_WARNING created.
3. CRITICAL : smoke > 60.0 ppm, flame = 1, is_anomaly = 1, anomaly_score >= 0.80
              -> FIRE_ALARM_CRITICAL created, expects RPCs setServo(90), setBuzzer(1), setLed(1)
              and Telegram critical alert.
4. CLEAR    : smoke < 35.0 ppm, flame = 0, is_anomaly = 0
              -> Alarms cleared, expects clear RPCs setServo(0), setBuzzer(0), setLed(0)
              and Telegram recovery alert.
"""

import argparse
import json
import os
import sys
import threading
import time
from typing import Dict, List, Tuple

import paho.mqtt.client as mqtt

# Defaults matched 100% with 02_Local_Gateway/hardware_gateway/LocalGateway.py
DEFAULT_BROKER = os.getenv("COREIOT_BROKER", "app.coreiot.io")
DEFAULT_PORT = int(os.getenv("COREIOT_PORT", "1883"))
DEFAULT_TOKEN = os.getenv("COREIOT_TOKEN", "i2tchqq1390qcxhun4zr")

TELEMETRY_TOPIC = "v1/devices/me/telemetry"
RPC_REQUEST_TOPIC = "v1/devices/me/rpc/request/+"

STAGES = [
    {
        "name": "STAGE 1: SAFE (Normal Baseline)",
        "code": "SAFE",
        "telemetry": {
            "smoke": 22.5,
            "temperature": 24.5,
            "flame": 0,
            "is_anomaly": 0,
            "anomaly_score": 0.12,
        },
        "expected_rpcs": {},
        "description": "Normal ambient readings (smoke < 35 ppm, flame=0). No alarm should trigger.",
    },
    {
        "name": "STAGE 2: WARNING (Early Smoke / Anomaly)",
        "code": "WARNING",
        "telemetry": {
            "smoke": 48.0,
            "temperature": 33.5,
            "flame": 0,
            "is_anomaly": 1,
            "anomaly_score": 0.65,
        },
        "expected_rpcs": {},
        "description": "Elevated smoke (35-60 ppm) & anomaly detected. Expects FIRE_ALARM_WARNING.",
    },
    {
        "name": "STAGE 3: CRITICAL (Active Fire Emergency)",
        "code": "CRITICAL",
        "telemetry": {
            "smoke": 88.5,
            "temperature": 65.0,
            "flame": 1,
            "is_anomaly": 1,
            "anomaly_score": 0.96,
        },
        "expected_rpcs": {"servo": 90, "buzzer": 1, "led": 1},
        "description": "High smoke (>60 ppm) + flame=1. Expects FIRE_ALARM_CRITICAL, 3 lockdown RPCs & Telegram Alert.",
    },
    {
        "name": "STAGE 4: CLEAR (Return to Safe State)",
        "code": "CLEAR",
        "telemetry": {
            "smoke": 18.0,
            "temperature": 25.0,
            "flame": 0,
            "is_anomaly": 0,
            "anomaly_score": 0.10,
        },
        "expected_rpcs": {"servo": 0, "buzzer": 0, "led": 0},
        "description": "Environment safe again (<35 ppm, flame=0). Expects Alarms Cleared, 3 reset RPCs & Telegram Clear.",
    },
]


class RuleChainTester:
    def __init__(self, broker: str, port: int, token: str):
        self.broker = broker
        self.port = port
        self.token = token

        self.connected_event = threading.Event()
        self.lock = threading.Lock()
        self.actuator_state = {"servo": 0, "buzzer": 0, "led": 0}
        self.current_stage_rpcs: List[Tuple[str, object, Dict[str, int]]] = []

        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="FireAlarm_RuleChainTest")
        except AttributeError:
            self.client = mqtt.Client(client_id="FireAlarm_RuleChainTest")

        self.client.username_pw_set(self.token)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(RPC_REQUEST_TOPIC)
            self.connected_event.set()
            print(f"[MQTT] Connected to {self.broker}:{self.port} | Subscribed: {RPC_REQUEST_TOPIC}")
        else:
            print(f"[MQTT Error] Connection failed (rc={rc})")

    def _on_message(self, client, userdata, msg):
        """Process incoming RuleChain RPC identically to LocalGateway.py."""
        try:
            req_id = msg.topic.split("/")[-1]
            rpc_data = json.loads(msg.payload.decode("utf-8"))
            method = rpc_data.get("method")
            params = rpc_data.get("params")

            local_cmd: Dict[str, int] = {}
            if method in ("setServo", "servo"):
                local_cmd["servo"] = int(params)
            elif method in ("setBuzzer", "buzzer"):
                local_cmd["buzzer"] = 1 if params in (True, 1, "1", "true") else 0
            elif method in ("setLed", "led"):
                local_cmd["led"] = 1 if params in (True, 1, "1", "true") else 0

            with self.lock:
                self.actuator_state.update(local_cmd)
                self.current_stage_rpcs.append((str(method), params, local_cmd))

            print(f"  <- [RPC RX] {method}({params}) [ReqID: {req_id}] -> Applied: {local_cmd}")

            resp_topic = f"v1/devices/me/rpc/response/{req_id}"
            client.publish(resp_topic, json.dumps({"status": "SUCCESS", "applied": local_cmd}))
        except Exception as exc:
            print(f"  [RPC Error] Failed to decode RPC: {exc}")

    def connect(self) -> bool:
        self.connected_event.clear()
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
        except Exception as exc:
            print(f"[MQTT Error] Unable to connect to {self.broker}:{self.port}: {exc}")
            return False

        self.client.loop_start()
        if not self.connected_event.wait(timeout=10.0):
            print("[MQTT Error] Connection timed out.")
            self.client.loop_stop()
            return False
        return True

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def run_stage(self, stage: dict, wait_sec: float) -> Dict[str, object]:
        print("\n" + "-" * 74)
        print(stage["name"])
        print(f"Description : {stage['description']}")
        print("-" * 74)

        with self.lock:
            self.current_stage_rpcs = []
            payload = dict(stage["telemetry"])
            payload.update(self.actuator_state)
            payload["timestamp"] = round(time.time(), 2)

        print(f"  -> [Telemetry TX] {json.dumps(payload)}")
        info = self.client.publish(TELEMETRY_TOPIC, json.dumps(payload), qos=1)
        info.wait_for_publish(timeout=5.0)

        print(f"  ... Waiting {wait_sec:.1f}s for CoreIOT RuleChain evaluation & RPC commands...")
        time.sleep(wait_sec)

        with self.lock:
            received = list(self.current_stage_rpcs)
            applied_map: Dict[str, int] = {}
            for _, _, cmd in received:
                applied_map.update(cmd)
            updated_state = dict(self.actuator_state)

        # Publish feedback telemetry if actuators changed so Dashboard reflects the new state
        if received:
            feedback_payload = dict(stage["telemetry"])
            feedback_payload.update(updated_state)
            feedback_payload["timestamp"] = round(time.time(), 2)
            print(f"  -> [Actuator Feedback TX] {json.dumps(feedback_payload)}")
            self.client.publish(TELEMETRY_TOPIC, json.dumps(feedback_payload), qos=1)

        expected = stage["expected_rpcs"]
        if expected:
            matched = all(applied_map.get(k) == v for k, v in expected.items())
            status = "PASS" if matched else "MISSING_RPC"
            missing = {k: v for k, v in expected.items() if applied_map.get(k) != v}
        else:
            matched = len(received) == 0
            status = "PASS" if matched else "UNEXPECTED_RPC"
            missing = {}

        print(f"  [Stage Result] {status} | RPCs Received: {len(received)} | Actuator State: {updated_state}")
        if missing:
            print(f"  [Missing Expected RPCs] {missing}")

        return {
            "stage": stage["code"],
            "status": status,
            "rpcs_received": len(received),
            "applied": applied_map,
            "missing": missing,
        }


def main():
    parser = argparse.ArgumentParser(description="4-Stage CoreIOT RuleChain & Telegram Alert Tester")
    parser.add_argument("--broker", default=DEFAULT_BROKER, help=f"MQTT broker host (default: {DEFAULT_BROKER})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"MQTT broker port (default: {DEFAULT_PORT})")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Device Access Token")
    parser.add_argument("--delay", type=float, default=6.0, help="Wait time per stage in seconds (default: 6.0)")
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Pause and wait for Enter before each stage (useful for live demo/screenshots)",
    )
    args = parser.parse_args()

    print("=" * 74)
    print("COREIOT FIRE ALARM - 4-STAGE RULECHAIN & ALERT VERIFICATION")
    print(f" -> Broker : {args.broker}:{args.port}")
    print(f" -> Stages : SAFE -> WARNING -> CRITICAL -> CLEAR")
    print("=" * 74)

    tester = RuleChainTester(broker=args.broker, port=args.port, token=args.token)
    if not tester.connect():
        sys.exit(1)

    report = []
    try:
        for stage in STAGES:
            if args.interactive:
                input(f"\nPress [Enter] to run {stage['name']}...")
            res = tester.run_stage(stage, wait_sec=args.delay)
            report.append(res)
    except KeyboardInterrupt:
        print("\n[Tester] Stopped by user.")
    finally:
        tester.disconnect()

    print("\n" + "=" * 74)
    print("4-STAGE VERIFICATION SUMMARY")
    print("=" * 74)
    for item in report:
        print(f"  {item['stage']:<10} | Status: {item['status']:<15} | RPCs: {item['rpcs_received']} | Applied: {item['applied']}")
    print("=" * 74)
    print("Reminder: Verify CoreIOT Alarms tab & Telegram chat for WARNING, CRITICAL, and CLEAR alerts.")


if __name__ == "__main__":
    main()
