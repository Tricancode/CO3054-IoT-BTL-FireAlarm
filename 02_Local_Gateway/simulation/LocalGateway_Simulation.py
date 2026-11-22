"""
LocalGateway_Simulation.py
==========================
GROUP 1: LOCAL SIMULATION IOT GATEWAY
Complies with HCMUT IoT Course Criteria T08 & T10.

Key Capabilities:
1. Receives UDP telemetry packets from virtual End Node (SimulationNode.py) on Port 5000.
2. Integrates SQLite WAL offline buffer (OfflineBufferRepository) to guarantee store-and-forward reliability.
3. Bridges telemetry to CoreIOT (ThingsBoard) Cloud over MQTT QoS 1.
4. Listens for CoreIOT RPC commands and dispatches them down to End Node over UDP (Port 5001).
5. Hosts Keen Dashboards Web Local Monitor UI on Port 5050 for direct on-station SCADA operations.
Strictly English logs, UI, and comments. Zero icons or emojis.
"""

import json
import logging
import queue
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict

import paho.mqtt.client as mqtt

# Ensure project root is in sys.path for modular imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ui.gateway_infrastructure import EmbeddedWebMonitor, OfflineBufferRepository
    from ui.isolation_detector import IsolationDetector
except ImportError:
    from gateway_infrastructure import EmbeddedWebMonitor, OfflineBufferRepository
    from isolation_detector import IsolationDetector

# Local network socket configuration
LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 5000       # Inbound telemetry port
NODE_IP = "127.0.0.1"
NODE_PORT = 5001        # Outbound downstream command port
WEB_PORT = 5050         # Keen Dashboards Web UI port

# CoreIOT Cloud Broker configuration
BROKER_ADDRESS = "app.coreiot.io"
BROKER_PORT = 1883
ACCESS_TOKEN = "i2tchqq1390qcxhun4zr"
TELEMETRY_TOPIC = "v1/devices/me/telemetry"
RPC_REQUEST_TOPIC = "v1/devices/me/rpc/request/+"


class LocalGatewaySimulation:
    def __init__(self, broker: str = BROKER_ADDRESS, token: str = ACCESS_TOKEN, web_port: int = WEB_PORT):
        # 1. Offline storage repository (SQLite WAL)
        self.db_path = Path("gateway_simulation_buffer.db")
        self.buffer_repo = OfflineBufferRepository(self.db_path)

        # 2. Thread-safe command queue (Prevents blocking MQTT client loop)
        self.command_queue = queue.Queue()

        # 3. Broker and Token configuration
        self.broker = broker
        self.token = token

        # 4. Real-time telemetry snapshot
        self.detector = IsolationDetector()
        self.telemetry_lock = threading.Lock()
        self.latest_telemetry: Dict[str, Any] = {
            "smoke": 0.0,
            "flame": 0,
            "servo": 0,
            "buzzer": 0,
            "led": 0,
            "is_anomaly": 0,
            "anomaly_score": 0.0,
            "timestamp": time.time(),
            "last_seen": 0,
            "cloud_connected": False,
            "buffer_count": 0,
            "gateway_type": "Simulation (UDP)"
        }

        # 5. Inbound UDP socket
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.udp_sock.bind((LOCAL_IP, LOCAL_PORT))
        except Exception as e:
            print(f"[Gateway Error] Failed to bind UDP socket on {LOCAL_IP}:{LOCAL_PORT}: {e}")
            sys.exit(1)

        # 6. CoreIOT / ThingsBoard MQTT client
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="FireAlarm_SimGateway")
        except AttributeError:
            self.mqtt_client = mqtt.Client(client_id="FireAlarm_SimGateway")

        self.mqtt_client.username_pw_set(self.token)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_client.on_message = self.on_mqtt_message

        # 7. Keen Dashboards HTTP Monitor
        self.web_monitor = EmbeddedWebMonitor(host="0.0.0.0", port=web_port)
        self.running = False

    # --- CoreIOT MQTT Callbacks ---
    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"\n[CoreIOT Cloud] Connected successfully to {self.broker}")
            with self.telemetry_lock:
                self.latest_telemetry["cloud_connected"] = True
            client.subscribe(RPC_REQUEST_TOPIC)
            print(f"[CoreIOT Cloud] Subscribed to RPC requests: {RPC_REQUEST_TOPIC}")
        else:
            print(f"[CoreIOT Cloud] Connection failed with result code {rc}")
            with self.telemetry_lock:
                self.latest_telemetry["cloud_connected"] = False

    def on_mqtt_disconnect(self, client, userdata, rc):
        print(f"\n[CoreIOT Cloud] Connection lost (code: {rc}). Switching to local offline buffering mode.")
        with self.telemetry_lock:
            self.latest_telemetry["cloud_connected"] = False

    def on_mqtt_message(self, client, userdata, msg):
        """Process RPC control messages dispatched from CoreIOT RuleChain or Dashboard."""
        try:
            req_id = msg.topic.split("/")[-1]
            rpc_data = json.loads(msg.payload.decode("utf-8"))
            method = rpc_data.get("method")
            params = rpc_data.get("params")
            print(f"\n[CoreIOT RPC] Cloud Command Received: {method}({params}) [ReqID: {req_id}]")

            local_cmd = {}
            if method in ("setServo", "servo"):
                local_cmd["servo"] = int(params)
            elif method in ("setBuzzer", "buzzer"):
                local_cmd["buzzer"] = 1 if params in (True, 1, "1", "true") else 0
            elif method in ("setLed", "led"):
                local_cmd["led"] = 1 if params in (True, 1, "1", "true") else 0

            if local_cmd:
                self.command_queue.put(local_cmd)

            # Publish ACK back to CoreIOT
            resp_topic = f"v1/devices/me/rpc/response/{req_id}"
            client.publish(resp_topic, json.dumps({"status": "SUCCESS", "applied": local_cmd}))

        except Exception as e:
            print(f"[CoreIOT RPC Error] Error decoding RPC command: {e}")

    # --- Downstream Command Dispatcher ---
    def command_worker(self):
        """Worker thread dispatching queued commands over UDP to SimulationNode."""
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=1.0)
                data_bytes = json.dumps(cmd).encode("utf-8")
                self.udp_sock.sendto(data_bytes, (NODE_IP, NODE_PORT))
                print(f"[Gateway Command -> Node] Dispatched command to {NODE_IP}:{NODE_PORT}: {cmd}")

                # Immediate UI snapshot feedback
                with self.telemetry_lock:
                    for k, v in cmd.items():
                        self.latest_telemetry[k] = v

                self.command_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Gateway Command Error] Failed to send UDP command: {e}")

    # --- Store & Forward Synchronization Worker ---
    def sync_worker(self):
        """Worker thread periodically syncing buffered SQLite records to CoreIOT Cloud."""
        while self.running:
            try:
                cloud_ok = False
                with self.telemetry_lock:
                    cloud_ok = self.latest_telemetry["cloud_connected"]
                    self.latest_telemetry["buffer_count"] = self.buffer_repo.count_unsynced()

                if cloud_ok:
                    unsynced = self.buffer_repo.fetch_unsynced(limit=25)
                    synced_ids = []
                    for rec_id, payload_str in unsynced:
                        info = self.mqtt_client.publish(TELEMETRY_TOPIC, payload_str, qos=1)
                        if info.rc == mqtt.MQTT_ERR_SUCCESS:
                            synced_ids.append(rec_id)
                        else:
                            break

                    if synced_ids:
                        self.buffer_repo.mark_synced(synced_ids)
                        print(f"[Buffer Sync] Synchronized {len(synced_ids)} buffered records to CoreIOT.")

            except Exception as e:
                print(f"[Sync Worker Error] Synchronization error: {e}")

            time.sleep(3.0)

    # --- Web Local Monitor UI Providers ---
    def web_data_provider(self) -> Dict[str, Any]:
        with self.telemetry_lock:
            return dict(self.latest_telemetry)

    def web_command_consumer(self, cmd: Dict[str, Any]):
        print(f"\n[Web Monitor Control] Command dispatched from station UI: {cmd}")
        self.command_queue.put(cmd)

    # --- Main Gateway Loop ---
    def run(self):
        self.running = True

        print("=" * 65)
        print("STARTING LOCAL IOT SIMULATION GATEWAY (T08 - T10)")
        print(f" -> UDP Inbound Port     : {LOCAL_IP}:{LOCAL_PORT}")
        print(f" -> CoreIOT Cloud Broker : {BROKER_ADDRESS}:{BROKER_PORT}")
        print(f" -> Web Local Monitor UI : http://localhost:{WEB_PORT}")
        print("=" * 65)

        # 1. Start Keen Dashboards HTTP Server
        self.web_monitor.start(self.web_data_provider, self.web_command_consumer)

        # 2. Start background workers
        threading.Thread(target=self.command_worker, daemon=True).start()
        threading.Thread(target=self.sync_worker, daemon=True).start()

        # 3. Connect to MQTT Cloud
        try:
            self.mqtt_client.connect_async(self.broker, BROKER_PORT, keepalive=60)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"[CoreIOT Warning] Failed to initialize MQTT client: {e}")

        # 4. Inbound telemetry receiver loop
        print("[Gateway Core] Inbound telemetry listener active...")
        while self.running:
            try:
                data, addr = self.udp_sock.recvfrom(2048)
                payload = json.loads(data.decode("utf-8"))

                # Run Isolation Forest Anomaly Detection
                s_val = float(payload.get("smoke", 0.0))
                t_val = float(payload.get("temperature", 24.0))
                f_val = float(payload.get("flame", 0.0))
                is_anom, anom_score = self.detector.update_and_predict(s_val, t_val, f_val)
                payload["is_anomaly"] = is_anom
                payload["anomaly_score"] = anom_score

                now_ts = time.time()
                with self.telemetry_lock:
                    self.latest_telemetry.update(payload)
                    self.latest_telemetry["last_seen"] = int(now_ts)
                    cloud_ready = self.latest_telemetry["cloud_connected"]

                print(f"[Gateway RX from {addr[0]}:{addr[1]}] Smoke: {payload.get('smoke')} | Flame: {payload.get('flame')} | Anomaly: {is_anom} (Score: {anom_score})")

                # Store into local SQLite buffer (Offline-first durability)
                self.buffer_repo.insert(payload)

                # Direct telemetry forwarding if cloud connection is active
                if cloud_ready:
                    self.mqtt_client.publish(TELEMETRY_TOPIC, json.dumps(payload), qos=1)

            except KeyboardInterrupt:
                print("\n[Gateway] Shutting down Local Gateway...")
                break
            except Exception as e:
                print(f"[Gateway Error] Error processing inbound packet: {e}")

        self.running = False
        self.mqtt_client.loop_stop()
        self.web_monitor.stop()
        self.udp_sock.close()
        print("[Gateway] Shutdown complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HCMUT Local Simulation Gateway")
    parser.add_argument("--broker", default=BROKER_ADDRESS, help="MQTT Broker host")
    parser.add_argument("--token", default=ACCESS_TOKEN, help="Device Access Token")
    parser.add_argument("--web-port", type=int, default=WEB_PORT, help="Web Monitor port")
    args = parser.parse_args()

    gateway = LocalGatewaySimulation(broker=args.broker, token=args.token, web_port=args.web_port)
    gateway.run()
