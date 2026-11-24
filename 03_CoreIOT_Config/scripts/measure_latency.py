#!/usr/bin/env python3
"""
measure_latency.py
==================
Automated End-to-End (E2E) Round-Trip Latency Benchmark for CoreIOT / ThingsBoard RuleChain (T12).

Workflow per trial:
1. Publishes a SAFE telemetry packet to clear any previous alarm state and waits for cooldown.
2. Publishes a CRITICAL fire telemetry packet matching LocalGateway.py keys
   (smoke > 60.0 ppm, flame = 1, is_anomaly = 1, anomaly_score >= 0.80) over MQTT QoS 1.
3. Measures:
   - MQTT PUBACK latency (client -> broker confirmation).
   - First RPC arrival latency (publish -> first RuleChain RPC command received).
   - Individual RPC latencies for setServo(90), setBuzzer(1), setLed(1).
   - Full 3-RPC completion latency (all three actuators commanded).
4. Responds to each RPC on v1/devices/me/rpc/response/{req_id} identically to LocalGateway.py.
5. Exports raw trial records to 04_Docs_Media/experiments/latency_results.csv and prints Min/Max/Avg.
"""

import argparse
import csv
import json
import os
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
import socket
from typing import Dict, List, Optional

import paho.mqtt.client as mqtt

def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0

# Defaults matched 100% with 02_Local_Gateway/hardware_gateway/LocalGateway.py
DEFAULT_BROKER = "127.0.0.1" if is_port_open("127.0.0.1", 1883) else os.getenv("COREIOT_BROKER", "app.coreiot.io")
DEFAULT_PORT = int(os.getenv("COREIOT_PORT", "1883"))
DEFAULT_TOKEN = os.getenv("COREIOT_TOKEN", "i2tchqq1390qcxhun4zr")

TELEMETRY_TOPIC = "v1/devices/me/telemetry"
RPC_REQUEST_TOPIC = "v1/devices/me/rpc/request/+"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_CSV = REPO_ROOT / "04_Docs_Media" / "experiments" / "latency_results.csv"

EXPECTED_CRITICAL_METHODS = {"servo", "buzzer", "led"}


def normalize_rpc_method(method: Optional[str], params) -> Optional[str]:
    """Map CoreIOT RPC method names identically to LocalGateway.py lines 216-221."""
    if method in ("setServo", "servo"):
        try:
            return "servo" if int(params) >= 45 else None
        except (ValueError, TypeError):
            return None
    if method in ("setBuzzer", "buzzer"):
        return "buzzer" if params in (True, 1, "1", "true") else None
    if method in ("setLed", "led"):
        return "led" if params in (True, 1, "1", "true") else None
    return None


def parse_local_cmd(method: Optional[str], params) -> Dict[str, int]:
    """Decode RPC command into LocalGateway.py actuator payload format."""
    local_cmd: Dict[str, int] = {}
    if method in ("setServo", "servo"):
        local_cmd["servo"] = int(params)
    elif method in ("setBuzzer", "buzzer"):
        local_cmd["buzzer"] = 1 if params in (True, 1, "1", "true") else 0
    elif method in ("setLed", "led"):
        local_cmd["led"] = 1 if params in (True, 1, "1", "true") else 0
    return local_cmd


class LatencyBenchmarker:
    def __init__(
        self,
        broker: str,
        port: int,
        token: str,
        timeout_sec: float = 10.0,
        grace_sec: float = 1.0,
    ):
        self.broker = broker
        self.port = port
        self.token = token
        self.timeout_sec = timeout_sec
        self.grace_sec = grace_sec

        self.connected_event = threading.Event()
        self.puback_event = threading.Event()
        self.first_rpc_event = threading.Event()
        self.all_rpcs_event = threading.Event()

        self.lock = threading.Lock()
        self.measuring = False
        self.t_start: float = 0.0
        self.t_puback: Optional[float] = None
        self.target_mid: Optional[int] = None
        self.rpc_times: Dict[str, float] = {}

        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="FireAlarm_LatencyBench")
        except AttributeError:
            self.client = mqtt.Client(client_id="FireAlarm_LatencyBench")

        self.client.username_pw_set(self.token)
        self.client.on_connect = self._on_connect
        self.client.on_publish = self._on_publish
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(RPC_REQUEST_TOPIC)
            self.connected_event.set()
            print(f"[MQTT] Connected to {self.broker}:{self.port} and subscribed to {RPC_REQUEST_TOPIC}")
        else:
            print(f"[MQTT Error] Connection failed with return code {rc}")

    def _on_publish(self, client, userdata, mid):
        now = time.perf_counter()
        with self.lock:
            if self.measuring and self.target_mid == mid and self.t_puback is None:
                self.t_puback = now
                self.puback_event.set()

    def _on_message(self, client, userdata, msg):
        arrival_t = time.perf_counter()
        try:
            req_id = msg.topic.split("/")[-1]
            rpc_data = json.loads(msg.payload.decode("utf-8"))
            method = rpc_data.get("method")
            params = rpc_data.get("params")

            local_cmd = parse_local_cmd(method, params)
            resp_topic = f"v1/devices/me/rpc/response/{req_id}"
            client.publish(resp_topic, json.dumps({"status": "SUCCESS", "applied": local_cmd}))

            matched_key = normalize_rpc_method(method, params)
            with self.lock:
                if self.measuring and matched_key is not None and matched_key not in self.rpc_times:
                    self.rpc_times[matched_key] = arrival_t
                    self.first_rpc_event.set()
                    if EXPECTED_CRITICAL_METHODS.issubset(self.rpc_times.keys()):
                        self.all_rpcs_event.set()
        except Exception as exc:
            print(f"[RPC Parse Error] {exc}")

    def connect(self) -> bool:
        self.connected_event.clear()
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
        except Exception as exc:
            print(f"[MQTT Error] Unable to connect to {self.broker}:{self.port}: {exc}")
            return False

        self.client.loop_start()
        if not self.connected_event.wait(timeout=10.0):
            print("[MQTT Error] Timed out waiting for broker CONNACK.")
            self.client.loop_stop()
            return False
        return True

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def send_safe_reset(self, cooldown_sec: float):
        """Publish SAFE baseline telemetry so RuleChain clears active alarms before the next trial."""
        safe_payload = {
            "smoke": 20.0,
            "temperature": 24.5,
            "flame": 0,
            "is_anomaly": 0,
            "anomaly_score": 0.10,
            "servo": 0,
            "buzzer": 0,
            "led": 0,
            "timestamp": round(time.time(), 2),
        }
        with self.lock:
            self.measuring = False
        self.client.publish(TELEMETRY_TOPIC, json.dumps(safe_payload), qos=1)
        time.sleep(cooldown_sec)

    def run_single_trial(
        self,
        trial_idx: int,
        smoke: float,
        temperature: float,
        flame: int,
    ) -> Dict[str, object]:
        """Publish one CRITICAL fire telemetry packet and measure round-trip RPC latencies."""
        self.puback_event.clear()
        self.first_rpc_event.clear()
        self.all_rpcs_event.clear()

        sent_iso = datetime.now(timezone.utc).isoformat()
        critical_payload = {
            "smoke": round(smoke, 2),
            "temperature": round(temperature, 2),
            "flame": int(flame),
            "is_anomaly": 1,
            "anomaly_score": 0.95,
            "servo": 0,
            "buzzer": 0,
            "led": 0,
            "timestamp": round(time.time(), 2),
        }

        with self.lock:
            self.rpc_times = {}
            self.t_puback = None
            self.measuring = True
            self.t_start = time.perf_counter()
            info = self.client.publish(TELEMETRY_TOPIC, json.dumps(critical_payload), qos=1)
            self.target_mid = info.mid

        # Wait for all 3 RPCs or timeout; if at least 1 RPC arrives, allow grace_sec for remaining ones
        got_first = self.first_rpc_event.wait(timeout=self.timeout_sec)
        if got_first and not self.all_rpcs_event.is_set():
            self.all_rpcs_event.wait(timeout=self.grace_sec)

        with self.lock:
            self.measuring = False
            t_start = self.t_start
            t_puback = self.t_puback
            rpc_snapshot = dict(self.rpc_times)

        mqtt_ack_ms = round((t_puback - t_start) * 1000.0, 2) if t_puback is not None else None
        servo_ms = round((rpc_snapshot["servo"] - t_start) * 1000.0, 2) if "servo" in rpc_snapshot else None
        buzzer_ms = round((rpc_snapshot["buzzer"] - t_start) * 1000.0, 2) if "buzzer" in rpc_snapshot else None
        led_ms = round((rpc_snapshot["led"] - t_start) * 1000.0, 2) if "led" in rpc_snapshot else None

        if rpc_snapshot:
            first_rpc_ms = round((min(rpc_snapshot.values()) - t_start) * 1000.0, 2)
        else:
            first_rpc_ms = None

        if EXPECTED_CRITICAL_METHODS.issubset(rpc_snapshot.keys()):
            all_3_rpc_ms = round((max(rpc_snapshot.values()) - t_start) * 1000.0, 2)
            status = "PASS_ALL_3"
        elif rpc_snapshot:
            all_3_rpc_ms = None
            status = f"PARTIAL_{len(rpc_snapshot)}_OF_3"
        else:
            all_3_rpc_ms = None
            status = "TIMEOUT"

        return {
            "trial": trial_idx,
            "timestamp_utc": sent_iso,
            "broker": f"{self.broker}:{self.port}",
            "smoke_ppm": critical_payload["smoke"],
            "temperature_c": critical_payload["temperature"],
            "flame": critical_payload["flame"],
            "mqtt_ack_ms": mqtt_ack_ms if mqtt_ack_ms is not None else "",
            "first_rpc_ms": first_rpc_ms if first_rpc_ms is not None else "",
            "servo_rpc_ms": servo_ms if servo_ms is not None else "",
            "buzzer_rpc_ms": buzzer_ms if buzzer_ms is not None else "",
            "led_rpc_ms": led_ms if led_ms is not None else "",
            "all_3_rpc_ms": all_3_rpc_ms if all_3_rpc_ms is not None else "",
            "rpcs_received": len(rpc_snapshot),
            "status": status,
        }


def compute_stats(values: List[float]) -> Optional[Dict[str, float]]:
    if not values:
        return None
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "avg": statistics.mean(values),
        "stdev": statistics.stdev(values) if len(values) >= 2 else 0.0,
    }


def save_results_csv(rows: List[Dict[str, object]], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "trial",
        "timestamp_utc",
        "broker",
        "smoke_ppm",
        "temperature_c",
        "flame",
        "mqtt_ack_ms",
        "first_rpc_ms",
        "servo_rpc_ms",
        "buzzer_rpc_ms",
        "led_rpc_ms",
        "all_3_rpc_ms",
        "rpcs_received",
        "status",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: List[Dict[str, object]], output_path: Path):
    print("\n" + "=" * 78)
    print("E2E ROUND-TRIP LATENCY BENCHMARK SUMMARY (CoreIOT RuleChain -> RPC)")
    print("=" * 78)

    metrics = [
        ("MQTT PUBACK (ms)", "mqtt_ack_ms"),
        ("First RPC Received (ms)", "first_rpc_ms"),
        ("Servo RPC setServo(90) (ms)", "servo_rpc_ms"),
        ("Buzzer RPC setBuzzer(1) (ms)", "buzzer_rpc_ms"),
        ("LED RPC setLed(1) (ms)", "led_rpc_ms"),
        ("All 3 RPCs Complete (ms)", "all_3_rpc_ms"),
    ]

    print(f"{'Metric':<30} | {'N':>3} | {'Min':>9} | {'Avg':>9} | {'Max':>9} | {'StdDev':>8}")
    print("-" * 78)
    for label, key in metrics:
        vals = [float(r[key]) for r in rows if r[key] != ""]
        stats = compute_stats(vals)
        if stats:
            print(
                f"{label:<30} | {stats['count']:>3} | "
                f"{stats['min']:>9.2f} | {stats['avg']:>9.2f} | "
                f"{stats['max']:>9.2f} | {stats['stdev']:>8.2f}"
            )
        else:
            print(f"{label:<30} |   0 |       N/A |       N/A |       N/A |      N/A")

    pass_all = sum(1 for r in rows if r["status"] == "PASS_ALL_3")
    pass_any = sum(1 for r in rows if int(r["rpcs_received"]) > 0)
    total = len(rows)
    print("-" * 78)
    print(f"Trials Passed (All 3 RPCs) : {pass_all}/{total} ({(pass_all / total * 100.0) if total else 0:.1f}%)")
    print(f"Trials Passed (>= 1 RPC)   : {pass_any}/{total} ({(pass_any / total * 100.0) if total else 0:.1f}%)")
    print(f"CSV Saved To               : {output_path}")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(description="Measure CoreIOT RuleChain E2E Round-Trip Latency")
    parser.add_argument("--broker", default=DEFAULT_BROKER, help=f"MQTT broker host (default: {DEFAULT_BROKER})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"MQTT broker port (default: {DEFAULT_PORT})")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Device Access Token")
    parser.add_argument("--trials", "-n", type=int, default=10, help="Number of measurement trials (default: 10)")
    parser.add_argument("--timeout", type=float, default=10.0, help="RPC wait timeout per trial in seconds (default: 10.0)")
    parser.add_argument("--cooldown", type=float, default=2.5, help="Cooldown after SAFE reset in seconds (default: 2.5)")
    parser.add_argument("--smoke", type=float, default=85.5, help="Critical test smoke value in ppm (default: 85.5)")
    parser.add_argument("--temp", type=float, default=62.0, help="Critical test temperature in C (default: 62.0)")
    parser.add_argument("--flame", type=int, default=1, choices=[0, 1], help="Critical test flame value (default: 1)")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_CSV), help=f"Output CSV path (default: {DEFAULT_OUTPUT_CSV})")
    args = parser.parse_args()

    output_path = Path(args.output).resolve()

    print("=" * 78)
    print("COREIOT FIRE ALARM - AUTOMATED E2E LATENCY BENCHMARK")
    print(f" -> Broker      : {args.broker}:{args.port}")
    print(f" -> Trials      : {args.trials}")
    print(f" -> Output CSV  : {output_path}")
    print("=" * 78)

    bench = LatencyBenchmarker(
        broker=args.broker,
        port=args.port,
        token=args.token,
        timeout_sec=args.timeout,
    )

    if not bench.connect():
        sys.exit(1)

    results: List[Dict[str, object]] = []
    try:
        for i in range(1, args.trials + 1):
            print(f"\n[Trial {i:02d}/{args.trials:02d}] Sending SAFE reset and waiting {args.cooldown:.1f}s...")
            bench.send_safe_reset(args.cooldown)

            print(f"[Trial {i:02d}/{args.trials:02d}] Publishing CRITICAL fire telemetry (smoke={args.smoke}, flame={args.flame})...")
            row = bench.run_single_trial(
                trial_idx=i,
                smoke=args.smoke,
                temperature=args.temp,
                flame=args.flame,
            )
            results.append(row)
            print(
                f"[Trial {i:02d}/{args.trials:02d}] Status={row['status']} | "
                f"PUBACK={row['mqtt_ack_ms'] or 'N/A'} ms | "
                f"FirstRPC={row['first_rpc_ms'] or 'N/A'} ms | "
                f"Servo={row['servo_rpc_ms'] or 'N/A'} ms | "
                f"All3={row['all_3_rpc_ms'] or 'N/A'} ms"
            )

        # Final SAFE reset so device/dashboard does not stay in alarm state after benchmark
        print("\n[Cleanup] Sending final SAFE telemetry to clear alarms...")
        bench.send_safe_reset(1.0)

    except KeyboardInterrupt:
        print("\n[Benchmark] Interrupted by user. Saving collected trials...")
    finally:
        bench.disconnect()

    if results:
        save_results_csv(results, output_path)
        print_summary(results, output_path)
    else:
        print("[Benchmark] No trials completed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
