"""
LocalGateway.py
===============
GROUP 2: LOCAL HARDWARE IOT GATEWAY (ESP32-S3 YOLOUNO VIA UART)
Complies with HCMUT IoT Course Criteria T08 & T10.

Key Capabilities:
1. Physical UART serial communication with ESP32-S3 (YoloUNO) over USB cable.
2. Auto-detection of USB Serial ports (CP210x, CH340, USB CDC, ESP32) with automatic cable reconnection.
3. Integrates SQLite WAL offline buffer (OfflineBufferRepository) to prevent data loss.
4. Bridges telemetry to CoreIOT (ThingsBoard) Cloud over MQTT QoS 1.
5. Listens for CoreIOT RPC commands and dispatches them to ESP32-S3 over UART Serial.
6. Hosts Keen Dashboards Web Local Monitor UI on Port 5050 for on-station SCADA operations.
Strictly English logs, UI, and comments. Zero icons or emojis.
"""

import argparse
import json
import logging
import queue
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
import serial
import serial.tools.list_ports

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

# UART defaults
DEFAULT_BAUDRATE = 115200
DEFAULT_PORT = "COM3" if sys.platform == "win32" else "/dev/ttyUSB0"
WEB_PORT = 5050

# CoreIOT Cloud Broker configuration
BROKER_ADDRESS = "app.coreiot.io"
BROKER_PORT = 1883
ACCESS_TOKEN = "i2tchqq1390qcxhun4zr"
DEFAULT_DEVICE_NAME = "FireAlarm_Gateway"

# Topics (Supports both ThingsBoard Gateway API and Device API)
TELEMETRY_TOPIC = "v1/devices/me/telemetry"
RPC_REQUEST_TOPIC = "v1/devices/me/rpc/request/+"
GATEWAY_TELEMETRY_TOPIC = "v1/gateway/telemetry"
GATEWAY_RPC_TOPIC = "v1/gateway/rpc"


def parse_uart_payload(line: str) -> Optional[Dict[str, Any]]:
    """Parse UART telemetry lines supporting both JSON and 01_Firmware_EndNode format."""
    if not line:
        return None
    cleaned = line.strip()

    # 1. Standard JSON string
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # 2. Text log from 01_Firmware_EndNode (main.cpp line 159)
    # e.g.: "MQ-2 ADC: 1450 | Lua: KHONG | Nhiet do: 28.5 C | Do am: 65% | Trang thai: AN TOAN"
    m = re.search(
        r'MQ-2 ADC:\s*(\d+).*?Lua:\s*(PHAT HIEN|KHONG|0|1).*?Nhiet do:\s*([\d\.\-]+).*?Do am:\s*([\d\.\-]+)',
        cleaned,
        re.IGNORECASE
    )
    if m:
        mq2_val = float(m.group(1))
        flame_str = m.group(2).upper()
        flame_val = 1 if ("PHAT HIEN" in flame_str or flame_str == "1") else 0
        try:
            temp_val = float(m.group(3))
        except ValueError:
            temp_val = 24.0
        try:
            hum_val = float(m.group(4))
        except ValueError:
            hum_val = 50.0

        return {
            "smoke": mq2_val,
            "flame": flame_val,
            "temperature": temp_val,
            "humidity": hum_val
        }

    return None


class HardwareSerialAdapter:
    """Manages UART serial connectivity to the physical YoloUNO ESP32-S3 board."""

    def __init__(self, port_name: Optional[str] = None, baudrate: int = DEFAULT_BAUDRATE):
        self.port_name = port_name
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.lock = threading.Lock()

    def auto_detect_port(self) -> str:
        """Scan available serial ports for ESP32/CH340/CP210x USB bridge descriptors."""
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            desc = (p.description or "").upper()
            hwid = (p.hwid or "").upper()
            if any(k in desc or k in hwid for k in ["ESP32", "CH340", "CP210", "UART", "USB SERIAL", "303A"]):
                print(f"[UART Auto-detect] Identified IoT board at {p.device} ({p.description})")
                return p.device
        if ports:
            print(f"[UART Auto-detect] No specific signature matched. Defaulting to first port: {ports[0].device}")
            return ports[0].device
        return DEFAULT_PORT

    def open(self) -> bool:
        """Open the serial port connection."""
        target_port = self.port_name or self.auto_detect_port()
        with self.lock:
            try:
                self.ser = serial.Serial(target_port, self.baudrate, timeout=1.0)
                try:
                    self.ser.dtr = True
                    self.ser.rts = True
                except Exception:
                    pass
                self.ser.reset_input_buffer()
                print(f"[UART Serial] Opened port {target_port} at {self.baudrate} baud.")
                return True
            except Exception as e:
                print(f"[UART Serial] Port {target_port} currently unavailable: {e}")
                self.ser = None
                return False

    def read_line(self) -> Optional[str]:
        """Read a single line from the serial connection."""
        with self.lock:
            if not self.ser or not self.ser.is_open:
                return None
            try:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                return line if line else None
            except Exception as e:
                print(f"[UART Read Error] {e}")
                self.close()
                return None

    def write_command(self, cmd: dict) -> bool:
        """Serialize and transmit a JSON command payload down to ESP32-S3 over UART."""
        with self.lock:
            if not self.ser or not self.ser.is_open:
                print("[UART Write Error] Serial port is not open. Command dropped.")
                return False
            try:
                msg = json.dumps(cmd) + "\n"
                self.ser.write(msg.encode("utf-8"))
                self.ser.flush()
                print(f"[UART Serial TX -> ESP32-S3] {msg.strip()}")
                return True
            except Exception as e:
                print(f"[UART Write Error] Serial transmit failure: {e}")
                return False

    def close(self):
        with self.lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass
            self.ser = None


class LocalHardwareGateway:
    def __init__(
        self,
        serial_port: Optional[str] = None,
        baudrate: int = DEFAULT_BAUDRATE,
        web_port: int = WEB_PORT,
        broker: str = BROKER_ADDRESS,
        token: str = ACCESS_TOKEN,
        device_name: str = DEFAULT_DEVICE_NAME,
        use_gateway_api: bool = True,
    ):
        # 1. Offline storage repository (SQLite WAL)
        self.db_path = Path("gateway_hardware_buffer.db")
        self.buffer_repo = OfflineBufferRepository(self.db_path)

        # 2. UART Adapter
        self.serial_adapter = HardwareSerialAdapter(serial_port, baudrate)

        # 3. Asynchronous Command Queue
        self.command_queue = queue.Queue()

        # 4. Broker configuration
        self.broker = broker
        self.token = token
        self.device_name = device_name
        self.use_gateway_api = use_gateway_api

        # 5. Real-time telemetry snapshot
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
            "gateway_type": "Hardware (UART ESP32-S3)"
        }

        # 6. CoreIOT / ThingsBoard MQTT Client
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="FireAlarm_HwGateway")
        except AttributeError:
            self.mqtt_client = mqtt.Client(client_id="FireAlarm_HwGateway")

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
            if self.use_gateway_api:
                client.subscribe(GATEWAY_RPC_TOPIC)
                print(f"[CoreIOT Cloud] Subscribed to Gateway RPC topic: {GATEWAY_RPC_TOPIC}")
            client.subscribe(RPC_REQUEST_TOPIC)
            print(f"[CoreIOT Cloud] Subscribed to Device RPC topic: {RPC_REQUEST_TOPIC}")
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
            if msg.topic == GATEWAY_RPC_TOPIC:
                # ThingsBoard Gateway RPC payload format: {"device": "...", "data": {"id": 1, "method": "...", "params": ...}}
                rpc_data = json.loads(msg.payload.decode("utf-8"))
                target_dev = rpc_data.get("device", self.device_name)
                data_obj = rpc_data.get("data", {})
                req_id = data_obj.get("id")
                method = data_obj.get("method")
                params = data_obj.get("params")
                print(f"\n[CoreIOT Gateway RPC] Cloud Command: {method}({params}) [Device: {target_dev}, ID: {req_id}]")

                local_cmd = {}
                if method in ("setServo", "servo"):
                    local_cmd["servo"] = int(params)
                elif method in ("setBuzzer", "buzzer"):
                    local_cmd["buzzer"] = 1 if params in (True, 1, "1", "true") else 0
                elif method in ("setLed", "led"):
                    local_cmd["led"] = 1 if params in (True, 1, "1", "true") else 0

                if local_cmd:
                    self.command_queue.put(local_cmd)

                # Gateway RPC response
                if req_id is not None and target_dev:
                    resp_payload = {
                        "device": target_dev,
                        "id": req_id,
                        "data": {"success": True}
                    }
                    try:
                        client.publish(GATEWAY_RPC_TOPIC, json.dumps(resp_payload))
                    except Exception:
                        pass

            elif msg.topic.startswith("v1/devices/me/rpc/request/"):
                req_id = msg.topic.split("/")[-1]
                rpc_data = json.loads(msg.payload.decode("utf-8"))
                method = rpc_data.get("method")
                params = rpc_data.get("params")
                print(f"\n[CoreIOT Device RPC] Cloud Command: {method}({params}) [ReqID: {req_id}]")

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
        """Worker thread dispatching queued commands over UART Serial to ESP32-S3."""
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=1.0)
                self.serial_adapter.write_command(cmd)

                with self.telemetry_lock:
                    for k, v in cmd.items():
                        self.latest_telemetry[k] = v

                self.command_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Command Worker Error] {e}")

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
                        if self.use_gateway_api:
                            rec_data = json.loads(payload_str)
                            gw_dev = "YOLOUNO_FIRE_NODE_01" if self.device_name == "FireAlarm_Gateway" else self.device_name
                            gw_msg = {gw_dev: [{"ts": int(time.time() * 1000), "values": rec_data}]}
                            self.mqtt_client.publish(GATEWAY_TELEMETRY_TOPIC, json.dumps(gw_msg), qos=1)

                        if info.rc == mqtt.MQTT_ERR_SUCCESS:
                            synced_ids.append(rec_id)
                        else:
                            break

                    if synced_ids:
                        self.buffer_repo.mark_synced(synced_ids)
                        print(f"[Buffer Sync] Synchronized {len(synced_ids)} buffered records to CoreIOT.")

                    # Periodic SQLite housekeeping: purge synced records older than 7 days
                    purged = self.buffer_repo.purge_synced(older_than_days=7.0)
                    if purged > 0:
                        print(f"[Buffer Maintenance] Purged {purged} expired synced records from offline database.")

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
        print("STARTING LOCAL HARDWARE IOT GATEWAY (T08 - T10)")
        print(f" -> Serial Configuration : {self.serial_adapter.port_name or 'Auto-detect'} @ {self.serial_adapter.baudrate}")
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

        # 4. Open Serial UART
        self.serial_adapter.open()

        # 5. Continuous UART reading loop
        print("[Gateway Core] Listening for UART data stream from ESP32-S3...")
        while self.running:
            try:
                line = self.serial_adapter.read_line()
                if not line:
                    if not self.serial_adapter.ser or not self.serial_adapter.ser.is_open:
                        time.sleep(3.0)
                        self.serial_adapter.open()
                    else:
                        time.sleep(0.05)
                    continue

                payload = parse_uart_payload(line)
                if payload:
                    try:
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

                        print(f"[UART RX ESP32-S3] Smoke: {payload.get('smoke')} | Flame: {payload.get('flame')} | Temp: {payload.get('temperature')} C | Anomaly: {is_anom}")

                        # Store in SQLite buffer
                        self.buffer_repo.insert(payload)

                        # Publish to Cloud if connected
                        if cloud_ready:
                            # 1. Publish to device telemetry topic (guarantees Dashboard and RuleChain updates)
                            self.mqtt_client.publish(TELEMETRY_TOPIC, json.dumps(payload), qos=1)
                            # 2. Also publish to Gateway topic if enabled
                            if self.use_gateway_api:
                                gw_dev = "YOLOUNO_FIRE_NODE_01" if self.device_name == "FireAlarm_Gateway" else self.device_name
                                gw_msg = {gw_dev: [{"ts": int(now_ts * 1000), "values": payload}]}
                                self.mqtt_client.publish(GATEWAY_TELEMETRY_TOPIC, json.dumps(gw_msg), qos=1)

                    except Exception as parse_err:
                        print(f"[Gateway Processing Error] {parse_err}")
                else:
                    print(f"[UART Raw Log] {line}")

            except KeyboardInterrupt:
                print("\n[Gateway] Shutting down Local Hardware Gateway...")
                break
            except Exception as e:
                print(f"[Gateway Error] {e}")
                time.sleep(1.0)

        self.running = False
        self.mqtt_client.loop_stop()
        self.web_monitor.stop()
        self.serial_adapter.close()
        print("[Gateway] Shutdown complete.")


def main():
    parser = argparse.ArgumentParser(description="HCMUT Local Hardware IoT Gateway (ESP32-S3 UART)")
    parser.add_argument("--port", "-p", default=None, help="Serial COM port (e.g., COM3 or /dev/ttyUSB0)")
    parser.add_argument("--baud", "-b", type=int, default=DEFAULT_BAUDRATE, help="Baudrate (default: 115200)")
    parser.add_argument("--web-port", "-w", type=int, default=WEB_PORT, help="Web Monitor UI port (default: 5050)")
    parser.add_argument("--broker", default=BROKER_ADDRESS, help="MQTT Broker host (e.g., app.coreiot.io or localhost)")
    parser.add_argument("--token", default=ACCESS_TOKEN, help="Device Access Token")
    parser.add_argument("--device-name", default=DEFAULT_DEVICE_NAME, help="Device/Gateway name in ThingsBoard")
    parser.add_argument("--device-api", action="store_true", help="Fallback to legacy Device API (v1/devices/me/telemetry)")
    args = parser.parse_args()

    gw = LocalHardwareGateway(
        serial_port=args.port,
        baudrate=args.baud,
        web_port=args.web_port,
        broker=args.broker,
        token=args.token,
        device_name=args.device_name,
        use_gateway_api=not args.device_api
    )
    gw.run()


if __name__ == "__main__":
    main()
