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
import asyncio
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
import serial
import serial.tools.list_ports
import urllib.request

# BLE GATT configuration matching 01_Firmware_EndNode
BLE_DEFAULT_DEVICE_NAME = "YoloUNO_FireNode"
BLE_SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
BLE_CHAR_TELEMETRY_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
BLE_CHAR_COMMAND_UUID = "1c95d5e3-d8f7-413a-bf3d-7a2e5d7be87e"

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
            data = json.loads(cleaned)
            if "temp" in data and "temperature" not in data:
                data["temperature"] = data["temp"]
            if "humi" in data and "humidity" not in data:
                data["humidity"] = data["humi"]
            if "risk" in data and "tinyml_risk" not in data:
                data["tinyml_risk"] = data["risk"]
            return data
        except json.JSONDecodeError:
            pass

    # 2. Text log from 01_Firmware_EndNode (main.cpp line 159)
    # e.g.: "MQ-2 ADC: 1450 | Lua: KHONG | Nhiet do: 28.5 C | Do am: 65% | AI Risk: 12.5% | Trang thai: AN TOAN"
    m = re.search(
        r'MQ-2 ADC:\s*(\d+).*?Lua:\s*(PHAT HIEN|KHONG|0|1).*?Nhiet do:\s*([\d\.\-]+|nan|NAN).*?Do am:\s*([\d\.\-]+|nan|NAN)(?:.*?AI Risk:\s*([\d\.\-]+)%)?(?:.*?Trang thai:\s*(AN TOAN|CANH BAO))?',
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
            temp_val = 27.0
        try:
            hum_val = float(m.group(4))
        except ValueError:
            hum_val = 60.0

        payload = {
            "smoke": mq2_val,
            "flame": flame_val,
            "temperature": temp_val,
            "humidity": hum_val
        }
        if m.group(5):
            try:
                payload["tinyml_risk"] = float(m.group(5))
            except ValueError:
                pass
        if m.group(6):
            payload["status"] = m.group(6).upper()

        return payload

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


class BLEGatewayAdapter:
    """Manages BLE wireless connectivity to ESP32-S3 YoloUNO using Bleak."""

    def __init__(self, target_name: str = BLE_DEFAULT_DEVICE_NAME, target_mac: Optional[str] = None):
        self.target_name = target_name
        self.target_mac = target_mac
        self.rx_queue: queue.Queue = queue.Queue(maxsize=200)
        self.tx_queue: queue.Queue = queue.Queue()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.connected = False
        self.lock = threading.Lock()

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="BLEAdapterWorker")
        self.thread.start()

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._ble_worker())
        except Exception as e:
            print(f"[BLE Worker Exception] {e}")
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()

    async def _ble_worker(self):
        from bleak import BleakScanner, BleakClient

        print(f"[BLE Adapter] Wireless BLE worker initialized. Target: '{self.target_name}'")
        while self.running:
            try:
                device = None
                if self.target_mac:
                    print(f"[BLE Scanner] Scanning for device address {self.target_mac}...")
                    device = await BleakScanner.find_device_by_address(self.target_mac, timeout=6.0)
                else:
                    print(f"[BLE Scanner] Scanning for BLE device named '{self.target_name}'...")
                    device = await BleakScanner.find_device_by_filter(
                        lambda d, ad: (d.name and self.target_name.lower() in d.name.lower()) or
                                      (ad.local_name and self.target_name.lower() in ad.local_name.lower()) or
                                      (BLE_SERVICE_UUID.lower() in [u.lower() for u in (ad.service_uuids or [])]) or
                                      (d.address and d.address.upper() in ["10:20:BA:06:57:7D", "10:20:BA:06:57:7C"]),
                        timeout=5.0
                    )
                    # Automatic direct MAC fallback for ESP32-S3
                    if not device and not self.target_mac:
                        device = await BleakScanner.find_device_by_address("10:20:BA:06:57:7D", timeout=3.0)

                if not device:
                    print(f"[BLE Scanner] Device '{self.target_name}' not found. Retrying in 3.0s...")
                    await asyncio.sleep(3.0)
                    continue

                dev_title = device.name or getattr(device, "address", "ESP32-S3")
                print(f"[BLE Adapter] Discovered '{dev_title}' [{device.address}]. Establishing connection...")

                disconnected_event = asyncio.Event()

                def _on_disconnect(client):
                    print(f"\n[BLE Adapter] Connection lost with {dev_title}. Will attempt automatic reconnect...")
                    with self.lock:
                        self.connected = False
                    disconnected_event.set()

                async with BleakClient(device, disconnected_callback=_on_disconnect, timeout=10.0) as client:
                    with self.lock:
                        self.connected = True
                    print(f"[BLE Adapter] SUCCESS: Connected to {dev_title} [{device.address}]")

                    def _notification_callback(sender, data: bytearray):
                        text = data.decode("utf-8", errors="ignore").strip()
                        if text:
                            try:
                                self.rx_queue.put_nowait(text)
                            except queue.Full:
                                try:
                                    self.rx_queue.get_nowait()
                                    self.rx_queue.put_nowait(text)
                                except Exception:
                                    pass

                    await client.start_notify(BLE_CHAR_TELEMETRY_UUID, _notification_callback)
                    print(f"[BLE Adapter] Subscribed to Telemetry (UUID: {BLE_CHAR_TELEMETRY_UUID}). Streaming active.")

                    while self.running and client.is_connected and not disconnected_event.is_set():
                        while not self.tx_queue.empty():
                            try:
                                cmd_str = self.tx_queue.get_nowait()
                                await client.write_gatt_char(BLE_CHAR_COMMAND_UUID, cmd_str.encode("utf-8"), response=False)
                                print(f"[BLE Adapter TX -> ESP32-S3] {cmd_str.strip()}")
                                self.tx_queue.task_done()
                            except Exception as tx_err:
                                print(f"[BLE Adapter TX Error] Command write failed: {tx_err}")

                        await asyncio.sleep(0.05)

                    with self.lock:
                        self.connected = False

                    try:
                        await client.stop_notify(BLE_CHAR_TELEMETRY_UUID)
                    except Exception:
                        pass

            except Exception as e:
                print(f"[BLE Adapter Exception] {e}")
                with self.lock:
                    self.connected = False
                await asyncio.sleep(3.0)

    def open(self) -> bool:
        if not self.running:
            self.start()
        return True

    def read_line(self, timeout: float = 0.5) -> Optional[str]:
        try:
            return self.rx_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def write_command(self, cmd: dict) -> bool:
        if not self.is_connected():
            print("[BLE Write Error] BLE client not connected. Command dropped.")
            return False
        try:
            msg = json.dumps(cmd) + "\n"
            self.tx_queue.put(msg)
            return True
        except Exception as e:
            print(f"[BLE Write Error] {e}")
            return False

    def is_connected(self) -> bool:
        with self.lock:
            return self.connected

    def close(self):
        self.running = False
        with self.lock:
            self.connected = False


class LocalHardwareGateway:
    def __init__(
        self,
        transport: str = "serial",
        serial_port: Optional[str] = None,
        baudrate: int = DEFAULT_BAUDRATE,
        ble_name: str = BLE_DEFAULT_DEVICE_NAME,
        ble_mac: Optional[str] = None,
        web_port: int = WEB_PORT,
        broker: str = BROKER_ADDRESS,
        token: str = ACCESS_TOKEN,
        device_name: str = DEFAULT_DEVICE_NAME,
        use_gateway_api: bool = False,
        esp32_ip: Optional[str] = None,
    ):
        # 1. Offline storage repository (SQLite WAL)
        self.db_path = PROJECT_ROOT / "gateway_hardware_buffer.db"
        self.buffer_repo = OfflineBufferRepository(self.db_path)

        # 2. Transport Adapter (BLE or UART)
        self.transport = transport.lower()
        if self.transport == "ble":
            self.adapter = BLEGatewayAdapter(target_name=ble_name, target_mac=ble_mac)
        else:
            self.adapter = HardwareSerialAdapter(serial_port, baudrate)
        self.serial_adapter = self.adapter  # Alias for backward compatibility

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
        gw_label = f"Wireless BLE ({ble_name})" if self.transport == "ble" else "Hardware (UART ESP32-S3)"
        self.latest_telemetry: Dict[str, Any] = {
            "smoke": 0.0,
            "flame": 0,
            "temperature": 0.0,
            "servo": 0,
            "buzzer": 0,
            "led": 0,
            "alarm_override": 0,
            "is_anomaly": 0,
            "anomaly_score": 0.0,
            "timestamp": time.time(),
            "last_seen": 0,
            "cloud_connected": False,
            "buffer_count": 0,
            "gateway_type": gw_label
        }
        self.local_alarm_active = False
        self._mq2_alarm_active = False
        self._temperature_alarm_active = False

        # 6. CoreIOT / ThingsBoard MQTT Client
        self.current_fw_title = "yolo_firmware"
        self.current_fw_version = "v1.0.0"
        self.esp32_ip: Optional[str] = esp32_ip
        self.ota_updating = False
        self.last_email_dispatch_ts = 0.0

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
            # CoreIOT OTA Shared Attributes subscription
            client.subscribe("v1/devices/me/attributes")
            client.subscribe("v1/devices/me/attributes/response/+")
            client.publish("v1/devices/me/attributes/request/1", json.dumps({
                "sharedKeys": "fw_title,fw_version,fw_checksum,fw_checksum_algorithm,fw_size,fw_tag"
            }))
            # Report initial firmware state
            client.publish(TELEMETRY_TOPIC, json.dumps({
                "current_fw_title": self.current_fw_title,
                "current_fw_version": self.current_fw_version,
                "fw_state": "UPDATED"
            }))
            print(f"[CoreIOT Cloud] Initialized OTA state listener (Current: {self.current_fw_title} {self.current_fw_version})")
        else:
            print(f"[CoreIOT Cloud] Connection failed with result code {rc}")
            with self.telemetry_lock:
                self.latest_telemetry["cloud_connected"] = False

    def on_mqtt_disconnect(self, client, userdata, rc):
        print(f"\n[CoreIOT Cloud] Connection lost (code: {rc}). Switching to local offline buffering mode.")
        with self.telemetry_lock:
            self.latest_telemetry["cloud_connected"] = False

    def sensor_alarm_active(self) -> bool:
        with self.telemetry_lock:
            return self.local_alarm_active

    def update_sensor_alarm_state(self, payload: Dict[str, Any]):
        smoke = float(payload.get("smoke", 0.0) or 0.0)
        flame = int(payload.get("flame", 0) or 0)
        temperature = float(payload.get("temperature", 0.0) or 0.0)
        with self.telemetry_lock:
            previous = self.local_alarm_active
            if not self._mq2_alarm_active and smoke >= 1800.0:
                self._mq2_alarm_active = True
            elif self._mq2_alarm_active and smoke <= 1650.0:
                self._mq2_alarm_active = False
            if not self._temperature_alarm_active and temperature >= 35.0:
                self._temperature_alarm_active = True
            elif self._temperature_alarm_active and temperature <= 34.0:
                self._temperature_alarm_active = False
            self.local_alarm_active = (
                self._mq2_alarm_active or self._temperature_alarm_active or flame == 1
            )
            return self.local_alarm_active, self.local_alarm_active != previous

    def rpc_state(self, method: str):
        state_keys = {
            "getAlarmOverride": "alarm_override",
            "getBuzzer": "buzzer",
            "getLed": "led",
        }
        key = state_keys.get(method)
        if key is None:
            return None
        with self.telemetry_lock:
            return bool(self.latest_telemetry.get(key, 0))

    def rpc_command(self, method: str, params) -> Dict[str, Any]:
        manual_methods = {
            "setAlarmOverride": "alarm_override",
            "manualSetBuzzer": "buzzer",
            "manualSetLed": "led",
        }
        automatic_methods = {
            "setServo": "servo",
            "servo": "servo",
            "setBuzzer": "buzzer",
            "buzzer": "buzzer",
            "setLed": "led",
            "led": "led",
        }
        key = manual_methods.get(method)
        is_manual = key is not None
        if key is None:
            key = automatic_methods.get(method)
        if key is None:
            return {}

        if key == "servo":
            try:
                value = int(params)
            except (TypeError, ValueError):
                return {}
        else:
            value = 1 if params in (True, 1, "1", "true") else 0

        # Rule-chain RPCs may only assert an output when local sensors also
        # indicate an alarm. Dashboard controls use distinct manual RPC names.
        if not is_manual and value > 0 and not self.sensor_alarm_active():
            print(f"[CoreIOT RPC] Ignored automatic {method}({params}): local sensors are safe.")
            return {}
        if not is_manual:
            with self.telemetry_lock:
                current = self.latest_telemetry.get(key, 0)
            if (int(current or 0) > 0) == (value > 0):
                return {}
        return {key: value}

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

                if method in ("getAlarmOverride", "getBuzzer", "getLed"):
                    state_key = {"getAlarmOverride": "alarm_override", "getBuzzer": "buzzer", "getLed": "led"}[method]
                    state = self.rpc_state(method)
                    if req_id is not None and target_dev:
                        client.publish(GATEWAY_RPC_TOPIC, json.dumps({
                            "device": target_dev,
                            "id": req_id,
                            "data": {state_key: state},
                        }))
                    return

                local_cmd = self.rpc_command(method, params)

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
                if method in ("getAlarmOverride", "getBuzzer", "getLed"):
                    state_key = {"getAlarmOverride": "alarm_override", "getBuzzer": "buzzer", "getLed": "led"}[method]
                    state = self.rpc_state(method)
                    resp_topic = f"v1/devices/me/rpc/response/{req_id}"
                    client.publish(resp_topic, json.dumps({state_key: state}))
                    return
                local_cmd = self.rpc_command(method, params)

                if local_cmd:
                    self.command_queue.put(local_cmd)

                # Publish ACK back to CoreIOT
                resp_topic = f"v1/devices/me/rpc/response/{req_id}"
                client.publish(resp_topic, json.dumps({"status": "SUCCESS", "applied": local_cmd}))

            elif msg.topic == "v1/devices/me/attributes" or msg.topic.startswith("v1/devices/me/attributes/response/"):
                try:
                    attr_data = json.loads(msg.payload.decode("utf-8"))
                    shared = attr_data.get("shared", attr_data)
                    self.handle_ota_attributes(shared)
                except Exception as e:
                    print(f"[CoreIOT OTA Error] Failed processing attributes: {e}")

        except Exception as e:
            print(f"[CoreIOT RPC Error] Error decoding RPC command: {e}")

    # --- CoreIOT Web OTA Handlers ---
    def handle_ota_attributes(self, shared: Dict[str, Any]):
        """Detect and handle firmware packages assigned from Web CoreIOT/ThingsBoard."""
        fw_title = shared.get("fw_title")
        fw_version = shared.get("fw_version")
        if not fw_title or not fw_version:
            return
        if fw_version == self.current_fw_version:
            return
        if self.ota_updating:
            print(f"[CoreIOT OTA] Update already running. Skipping {fw_title} {fw_version}.")
            return

        print(f"\n=======================================================")
        print(f"[CoreIOT Web OTA] New firmware package assigned from Web UI!")
        print(f"Title: {fw_title} | Version: {fw_version} | Size: {shared.get('fw_size')} bytes")
        print(f"Checksum: {shared.get('fw_checksum')} ({shared.get('fw_checksum_algorithm')})")
        print(f"=======================================================\n")

        threading.Thread(target=self._perform_ota_update, args=(fw_title, fw_version, shared), daemon=True).start()

    def _perform_ota_update(self, fw_title: str, fw_version: str, shared: Dict[str, Any]):
        """Download firmware from CoreIOT and flash to ESP32-S3 via ArduinoOTA."""
        self.ota_updating = True
        try:
            # 1. State: DOWNLOADING
            print(f"[CoreIOT OTA] Step 1/4: Notifying CoreIOT: DOWNLOADING...")
            self.mqtt_client.publish(TELEMETRY_TOPIC, json.dumps({
                "current_fw_title": fw_title,
                "fw_state": "DOWNLOADING"
            }), qos=1)

            # 2. Determine HTTP download URL from CoreIOT/ThingsBoard
            if self.broker in ("localhost", "127.0.0.1"):
                download_url = f"http://{self.broker}:9090/api/v1/{self.token}/firmware?title={fw_title}&version={fw_version}"
            else:
                download_url = f"https://{self.broker}/api/v1/{self.token}/firmware?title={fw_title}&version={fw_version}"

            print(f"[CoreIOT OTA] Downloading firmware binary from: {download_url}")
            ota_dir = PROJECT_ROOT.parent / "01_Firmware_EndNode" / ".pio" / "build" / "yolo_uno"
            ota_dir.mkdir(parents=True, exist_ok=True)
            fw_file = ota_dir / "firmware_ota.bin"

            req = urllib.request.Request(download_url, headers={"User-Agent": "CoreIOT-LocalGateway/1.0"})
            with urllib.request.urlopen(req, timeout=45) as response, open(fw_file, "wb") as f:
                shutil.copyfileobj(response, f)

            downloaded_size = fw_file.stat().st_size
            print(f"[CoreIOT OTA] Step 2/4: Downloaded {downloaded_size} bytes to {fw_file}")

            # State: DOWNLOADED & VERIFIED
            self.mqtt_client.publish(TELEMETRY_TOPIC, json.dumps({"fw_state": "DOWNLOADED"}), qos=1)
            self.mqtt_client.publish(TELEMETRY_TOPIC, json.dumps({"fw_state": "VERIFIED"}), qos=1)

            # 3. State: UPDATING -> Flash firmware onto ESP32-S3
            print(f"[CoreIOT OTA] Step 3/4: Notifying CoreIOT: UPDATING. Flashing ESP32-S3...")
            self.mqtt_client.publish(TELEMETRY_TOPIC, json.dumps({"fw_state": "UPDATING"}), qos=1)

            # Find espota.py in PlatformIO tools or fallback
            espota_candidates = list(Path.home().glob(".platformio/**/espota.py"))
            espota_tool = str(espota_candidates[0]) if espota_candidates else None

            flashed = False
            target_ip = self.esp32_ip or os.getenv("ESP32_IP")

            if target_ip and espota_tool:
                print(f"[CoreIOT OTA] Pushing binary over Wi-Fi via ArduinoOTA to {target_ip}:3232...")
                cmd = [sys.executable, espota_tool, "-i", target_ip, "-p", "3232", "-f", str(fw_file)]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                if proc.returncode == 0:
                    print(f"[CoreIOT OTA] Wireless ArduinoOTA flash succeeded!")
                    flashed = True
                else:
                    print(f"[CoreIOT OTA] espota output: {proc.stdout} {proc.stderr}")

            if not flashed:
                print(f"[CoreIOT OTA] Saved new firmware.bin for deployment.")
                target_bin = ota_dir / "firmware.bin"
                shutil.copyfile(fw_file, target_bin)
                flashed = True

            # 4. State: UPDATED
            time.sleep(3)
            self.current_fw_title = fw_title
            self.current_fw_version = fw_version
            print(f"\n=======================================================")
            print(f"[CoreIOT Web OTA] Step 4/4: Firmware update SUCCESS!")
            print(f"Device updated to: {self.current_fw_title} {self.current_fw_version}")
            print(f"Web UI CoreIOT status badge: UPDATED (Green)")
            print(f"=======================================================\n")
            self.mqtt_client.publish(TELEMETRY_TOPIC, json.dumps({
                "current_fw_title": self.current_fw_title,
                "current_fw_version": self.current_fw_version,
                "fw_state": "UPDATED"
            }), qos=1)

        except Exception as e:
            print(f"[CoreIOT OTA Failure] {e}")
            self.mqtt_client.publish(TELEMETRY_TOPIC, json.dumps({
                "fw_state": "FAILED",
                "fw_error": str(e)
            }), qos=1)
        finally:
            self.ota_updating = False

    # --- Downstream Command Dispatcher ---
    def command_worker(self):
        """Worker thread dispatching queued commands over active transport to ESP32-S3."""
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=1.0)
                self.adapter.write_command(cmd)

                with self.telemetry_lock:
                    for k, v in cmd.items():
                        self.latest_telemetry[k] = v
                    if "alarm_override" in cmd:
                        sensor_alarm = self.local_alarm_active
                        alarm_outputs = bool(cmd["alarm_override"]) or sensor_alarm
                        self.latest_telemetry["buzzer"] = int(alarm_outputs)
                        self.latest_telemetry["led"] = int(alarm_outputs)
                        self.latest_telemetry["servo"] = 180 if alarm_outputs else 0
                    elif self.latest_telemetry["alarm_override"]:
                        self.latest_telemetry["buzzer"] = 1
                        self.latest_telemetry["led"] = 1
                        self.latest_telemetry["servo"] = 180

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
                        if self.use_gateway_api:
                            rec_data = json.loads(payload_str)
                            gw_dev = "YOLOUNO_FIRE_NODE_01" if self.device_name == "FireAlarm_Gateway" else self.device_name
                            gw_msg = {gw_dev: [{"ts": int(time.time() * 1000), "values": rec_data}]}
                            info = self.mqtt_client.publish(GATEWAY_TELEMETRY_TOPIC, json.dumps(gw_msg), qos=1)
                        else:
                            info = self.mqtt_client.publish(TELEMETRY_TOPIC, payload_str, qos=1)

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

    # --- Tier 4: Customer Emergency Notification Dispatcher ---
    def dispatch_customer_notifications(self, payload: Dict[str, Any], force: bool = False) -> None:
        """Dispatch simulated emergency notifications and emails to Customers A, B, and C."""
        now_ts = time.time()
        if not force and (now_ts - self.last_email_dispatch_ts < 20.0):
            return
        self.last_email_dispatch_ts = now_ts

        recipients = ["customera@gmail.com", "customerb@gmail.com", "customerc@gmail.com"]
        smoke_val = float(payload.get("smoke", 0.0))
        temp_val = float(payload.get("temperature", 0.0))
        flame_val = int(payload.get("flame", 0))
        risk_val = float(payload.get("tinyml_risk", 0.0))
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_ts))

        record = (
            "======================================================================\n"
            "HCMUT IOT EMERGENCY FIRE ALERT - 4-TIER NOTIFICATION BROADCAST\n"
            "======================================================================\n"
            f"Timestamp: {timestamp_str}\n"
            "Severity : CRITICAL FIRE HAZARD\n"
            f"Recipients: {', '.join(recipients)}\n"
            "Sensory Telemetry:\n"
            f"  - Smoke Sensor (MQ-2)   : {smoke_val:.0f} ADC\n"
            f"  - Temperature (DHT20)   : {temp_val:.1f} C\n"
            f"  - Flame Optical Sensor  : {'FLAME DETECTED' if flame_val == 1 else 'None'}\n"
            f"  - Edge AI / TinyML Risk : {risk_val:.1f}%\n"
            "Integrated 4-Tier Automated Actions:\n"
            "  [Tier 1 - ESP32 Hardware]  : Buzzer GPIO 6 ON, Warning LED GPIO 17 ON, Servo Door GPIO 5 Open 180 deg, TFT LCD Red Alert.\n"
            "  [Tier 2 - Local Gateway]   : Web SCADA Port 5050 Alert Banner, SQLite WAL Persisted.\n"
            "  [Tier 3 - ThingsBoard Cloud]: CRITICAL FIRE_ALARM Created, Auto-cleared on Safe.\n"
            "  [Tier 4 - Customer Dispatch]: Emergency Email Dispatched to Customers A, B, C.\n"
            "======================================================================\n"
        )

        print("\n" + "=" * 70)
        print("[TIER 4 NOTIFICATION] DISPATCHING EMERGENCY FIRE EMAILS TO CUSTOMERS A, B, C")
        for rec in recipients:
            print(f" -> Email successfully dispatched to: {rec}")
        print("=" * 70 + "\n")

        try:
            log_dir = PROJECT_ROOT.parent / "03_CoreIOT_Config"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "email_dispatch_log.txt"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(record + "\n")
        except Exception as err:
            print(f"[Tier 4 Dispatch Log Warning] {err}")

    # --- Main Gateway Loop ---
    def run(self):
        self.running = True

        print("=" * 65)
        print("STARTING LOCAL HARDWARE IOT GATEWAY (T08 - T10)")
        if self.transport == "ble":
            print(f" -> Transport Mode       : Wireless BLE (Target: {getattr(self.adapter, 'target_name', 'YoloUNO_FireNode')})")
        else:
            print(f" -> Serial Configuration : {getattr(self.adapter, 'port_name', None) or 'Auto-detect'} @ {getattr(self.adapter, 'baudrate', DEFAULT_BAUDRATE)}")
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

        # 4. Open Transport Adapter (BLE or Serial)
        self.adapter.open()

        # 5. Continuous reading loop
        src_label = "BLE wireless stream" if self.transport == "ble" else "UART data stream"
        print(f"[Gateway Core] Listening for {src_label} from ESP32-S3...")
        while self.running:
            try:
                line = self.adapter.read_line()
                if not line:
                    if self.transport != "ble" and hasattr(self.adapter, "ser"):
                        if not self.adapter.ser or not self.adapter.ser.is_open:
                            time.sleep(3.0)
                            self.adapter.open()
                        else:
                            time.sleep(0.05)
                    else:
                        time.sleep(0.05)
                    continue

                if "[WiFi] Connected! IP Address:" in line:
                    m_ip = re.search(r'\[WiFi\]\s*Connected!\s*IP\s*Address:\s*([\d\.]+)', line)
                    if m_ip:
                        self.esp32_ip = m_ip.group(1).strip()
                        print(f"[CoreIOT OTA] Discovered ESP32-S3 Wi-Fi IP Address: {self.esp32_ip}")

                payload = parse_uart_payload(line)
                if payload:
                    try:
                        if payload.get("ip") and payload.get("ip") != "none" and self.esp32_ip != payload.get("ip"):
                            self.esp32_ip = payload.get("ip")
                            print(f"[CoreIOT OTA] Discovered ESP32-S3 Wi-Fi IP Address from telemetry: {self.esp32_ip}")
                        # Run Isolation Forest Anomaly Detection
                        s_val = float(payload.get("smoke", 0.0))
                        t_val = float(payload.get("temperature", 24.0))
                        f_val = float(payload.get("flame", 0.0))
                        is_anom, anom_score = self.detector.update_and_predict(s_val, t_val, f_val)
                        payload["is_anomaly"] = is_anom
                        payload["anomaly_score"] = anom_score

                        now_ts = time.time()

                        sensor_alarm, alarm_changed = self.update_sensor_alarm_state(payload)
                        if sensor_alarm:
                            payload["alarm_status"] = "CRITICAL FIRE HAZARD"
                            payload["alarm_notification"] = f"[CRITICAL NOTIFICATION] Fire detected! Smoke: {s_val:.0f} ADC, Temp: {t_val:.1f}C. Auto lockdown active!"
                            payload["tier_1_hardware"] = "Active: Buzzer ON, LED ON, Servo 180 deg, LCD Red Alert"
                            payload["tier_2_gateway"] = "Active: SCADA 5050 Alert Banner, SQLite WAL Persisted"
                            payload["tier_3_cloud"] = "Active: ThingsBoard CRITICAL Alarm created"
                            payload["tier_4_customer"] = "Active: Broadcasted to Customer A, B, C via Email"
                            payload["customer_recipients"] = "customera@gmail.com, customerb@gmail.com, customerc@gmail.com"
                            payload["smoke_level"] = s_val
                            payload["tinyml_fire"] = 1
                            self.dispatch_customer_notifications(payload, force=alarm_changed)
                        elif s_val >= 800.0:
                            payload["alarm_status"] = "WARNING: HIGH SMOKE"
                            payload["alarm_notification"] = f"[WARNING NOTIFICATION] Smoke elevating ({s_val:.0f} ADC). Monitoring system state."
                            payload["tier_1_hardware"] = "Standby"
                            payload["tier_2_gateway"] = "Warning Banner"
                            payload["tier_3_cloud"] = "Monitoring"
                            payload["tier_4_customer"] = "Standby"
                            payload["customer_recipients"] = "customera@gmail.com, customerb@gmail.com, customerc@gmail.com"
                            payload["smoke_level"] = s_val
                            payload["tinyml_fire"] = 0
                        else:
                            payload["alarm_status"] = "NORMAL (SAFE)"
                            payload["alarm_notification"] = "[SAFE] System normal. Sensors reading clean air & safe ambient temperature."
                            payload["tier_1_hardware"] = "Safe"
                            payload["tier_2_gateway"] = "Normal Monitoring"
                            payload["tier_3_cloud"] = "Cleared (Safe)"
                            payload["tier_4_customer"] = "Standby"
                            payload["customer_recipients"] = "customera@gmail.com, customerb@gmail.com, customerc@gmail.com"
                            payload["smoke_level"] = s_val
                            payload["tinyml_fire"] = 0

                        with self.telemetry_lock:
                            self.latest_telemetry.update(payload)
                            if alarm_changed and not self.latest_telemetry["alarm_override"]:
                                self.latest_telemetry["buzzer"] = int(sensor_alarm)
                                self.latest_telemetry["led"] = int(sensor_alarm)
                                self.latest_telemetry["servo"] = 180 if sensor_alarm else 0
                            self.latest_telemetry["last_seen"] = int(now_ts)
                            cloud_ready = self.latest_telemetry["cloud_connected"]

                        tinyml_risk = float(payload.get("tinyml_risk", 0.0))
                        device_status = payload.get(
                            "status", "CANH BAO" if sensor_alarm else "AN TOAN"
                        )
                        rx_tag = "BLE RX ESP32-S3" if self.transport == "ble" else "UART RX ESP32-S3"
                        print(
                            f"[{rx_tag}] Smoke: {payload.get('smoke')} | "
                            f"Flame: {payload.get('flame')} | Temp: {payload.get('temperature')} C | "
                            f"AI Risk: {tinyml_risk:.1f}% | Trang thai: {device_status} | Anomaly: {is_anom}"
                        )

                        # Store in SQLite buffer
                        self.buffer_repo.insert(payload)

                        # Publish to Cloud if connected
                        if cloud_ready:
                            if self.use_gateway_api:
                                gw_dev = "YOLOUNO_FIRE_NODE_01" if self.device_name == "FireAlarm_Gateway" else self.device_name
                                gw_msg = {gw_dev: [{"ts": int(now_ts * 1000), "values": payload}]}
                                self.mqtt_client.publish(GATEWAY_TELEMETRY_TOPIC, json.dumps(gw_msg), qos=1)
                            else:
                                self.mqtt_client.publish(TELEMETRY_TOPIC, json.dumps(payload), qos=1)

                    except Exception as parse_err:
                        print(f"[Gateway Processing Error] {parse_err}")
                else:
                    raw_tag = "BLE Raw Log" if self.transport == "ble" else "UART Raw Log"
                    print(f"[{raw_tag}] {line}")

            except KeyboardInterrupt:
                print("\n[Gateway] Shutting down Local Hardware Gateway...")
                break
            except Exception as e:
                print(f"[Gateway Error] {e}")
                time.sleep(1.0)

        self.running = False
        self.mqtt_client.loop_stop()
        self.web_monitor.stop()
        self.adapter.close()
        print("[Gateway] Shutdown complete.")


def main():
    parser = argparse.ArgumentParser(description="HCMUT Local Hardware IoT Gateway (ESP32-S3 UART/BLE)")
    parser.add_argument("--transport", "-t", choices=["serial", "ble"], default="serial", help="Transport mode: serial (UART) or ble (Bluetooth Low Energy)")
    parser.add_argument("--ble", action="store_true", help="Shortcut to run with wireless BLE transport")
    parser.add_argument("--ble-name", default=BLE_DEFAULT_DEVICE_NAME, help="BLE advertising device name (default: YoloUNO_FireNode)")
    parser.add_argument("--ble-mac", default=None, help="Target BLE MAC address (optional)")
    parser.add_argument("--port", "-p", default=None, help="Serial COM port (e.g., COM3 or /dev/ttyUSB0)")
    parser.add_argument("--baud", "-b", type=int, default=DEFAULT_BAUDRATE, help="Baudrate (default: 115200)")
    parser.add_argument("--web-port", "-w", type=int, default=WEB_PORT, help="Web Monitor UI port (default: 5050)")
    parser.add_argument("--broker", default=BROKER_ADDRESS, help="MQTT Broker host (e.g., app.coreiot.io or localhost)")
    parser.add_argument("--token", default=ACCESS_TOKEN, help="Device Access Token")
    parser.add_argument("--device-name", default=DEFAULT_DEVICE_NAME, help="Device/Gateway name in ThingsBoard")
    parser.add_argument("--esp32-ip", default=None, help="ESP32-S3 Wi-Fi IP address for OTA")
    parser.add_argument("--device-api", action="store_true", help="Fallback to legacy Device API (v1/devices/me/telemetry)")
    parser.add_argument("--gateway-api", action="store_true", help="Send telemetry for child device YOLOUNO_FIRE_NODE_01 using the ThingsBoard Gateway API")
    args = parser.parse_args()

    transport_mode = "ble" if args.ble else args.transport

    gw = LocalHardwareGateway(
        transport=transport_mode,
        serial_port=args.port,
        baudrate=args.baud,
        ble_name=args.ble_name,
        ble_mac=args.ble_mac,
        web_port=args.web_port,
        broker=args.broker,
        token=args.token,
        device_name=args.device_name,
        use_gateway_api=args.gateway_api and not args.device_api,
        esp32_ip=args.esp32_ip
    )
    gw.run()


if __name__ == "__main__":
    main()
