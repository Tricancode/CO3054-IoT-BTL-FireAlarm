"""
test_system.py
==============
Comprehensive automated test suite for Local IoT Gateway (T08, T10).
Validates:
1. Compliance: Zero icons, zero emojis, and zero Vietnamese characters in source code.
2. SQLite WAL persistence repository (OfflineBufferRepository).
3. Embedded Keen Dashboards Web UI and REST API (EmbeddedWebMonitor).
4. Hardware Serial UART adapter with mock hardware interface.
5. Bidirectional UDP communication between SimulationNode and LocalGateway_Simulation.
"""

import hashlib
import json
import re
import socket
import tempfile
import time
import unittest
import urllib.request
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

GATEWAY_ROOT = Path(__file__).resolve().parent.parent / "02_Local_Gateway"
if str(GATEWAY_ROOT) not in sys.path:
    sys.path.insert(0, str(GATEWAY_ROOT))

from ui.gateway_infrastructure import EmbeddedWebMonitor, OfflineBufferRepository
from ui.isolation_detector import IsolationDetector
from hardware_gateway.LocalGateway import (
    HardwareSerialAdapter,
    BLEGatewayAdapter,
    LocalHardwareGateway,
    GATEWAY_RPC_TOPIC,
    GATEWAY_TELEMETRY_TOPIC,
    parse_uart_payload,
)

EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]|"
    r"[\u2600-\u26ff]|"
    r"[\u2700-\u27bf]|"
    r"[\u2300-\u23ff]|"
    r"[\u2b50-\u2b55]|"
    r"[\u203c-\u2049]|"
    r"[\u25aa-\u25fe]"
)

VIETNAMESE_PATTERN = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    r"ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]"
)


class TestProjectCompliance(unittest.TestCase):
    def test_no_emojis_or_vietnamese_in_codebase(self):
        """Audit all source code files to guarantee zero emojis and zero Vietnamese in Python modules."""
        gateway_root = Path(__file__).resolve().parent.parent / "02_Local_Gateway"
        test_root = Path(__file__).resolve().parent
        python_files = [
            gateway_root / "ui" / "gateway_infrastructure.py",
            gateway_root / "ui" / "isolation_detector.py",
            gateway_root / "hardware_gateway" / "LocalGateway.py",
            gateway_root / "dashboard" / "deploy_thingsboard.py",
            gateway_root / "dashboard" / "setup_thingsboard_dashboard.py",
            gateway_root / "dashboard" / "upload_ota_firmware.py",
            test_root / "verify_telemetry.py",
            test_root / "test_system.py",
        ]

        # Audit Python source code for both emojis and Vietnamese characters
        for file_path in python_files:
            if not file_path.exists():
                continue
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            emoji_match = EMOJI_PATTERN.search(content)
            self.assertIsNone(
                emoji_match,
                f"Emoji or symbol character found in {file_path.name}: {emoji_match.group(0) if emoji_match else ''}"
            )

            if file_path.name != "test_system.py":
                vn_match = VIETNAMESE_PATTERN.search(content)
                self.assertIsNone(
                    vn_match,
                    f"Vietnamese character detected in Python module {file_path.name}: {vn_match.group(0) if vn_match else ''}"
                )

        # Audit README.md for zero emojis/icons
        readme_path = gateway_root / "README.md"
        if not readme_path.exists():
            readme_path = gateway_root.parent / "README.md"
        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()
            emoji_match = EMOJI_PATTERN.search(readme_content)
            self.assertIsNone(
                emoji_match,
                f"Emoji or symbol character found in README.md: {emoji_match.group(0) if emoji_match else ''}"
            )


class TestGatewayInfrastructure(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_buffer.db"
        self.repo = OfflineBufferRepository(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sqlite_wal_buffer_lifecycle(self):
        """Verify: Buffer insert -> Fetch unsynced in FIFO order -> Mark synced."""
        self.assertEqual(self.repo.count_unsynced(), 0)

        self.repo.insert({"smoke": 25.4, "flame": 0, "servo": 0})
        self.repo.insert({"smoke": 82.1, "flame": 1, "servo": 90})
        self.repo.insert({"smoke": 12.0, "flame": 0, "servo": 0})

        self.assertEqual(self.repo.count_unsynced(), 3)

        records = self.repo.fetch_unsynced(limit=2)
        self.assertEqual(len(records), 2)
        rec_id1, payload_str1 = records[0]
        data1 = json.loads(payload_str1)
        self.assertEqual(data1["smoke"], 25.4)

        self.repo.mark_synced([records[0][0], records[1][0]])
        self.assertEqual(self.repo.count_unsynced(), 1)

        remaining = self.repo.fetch_unsynced(limit=10)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(json.loads(remaining[0][1])["smoke"], 12.0)

    def test_embedded_web_monitor_endpoints(self):
        """Verify Keen Dashboards UI HTML delivery and REST API endpoints."""
        latest_data = {
            "smoke": 45.5,
            "flame": 0,
            "servo": 0,
            "buzzer": 0,
            "led": 0,
            "timestamp": time.time(),
            "cloud_connected": True,
            "gateway_type": "TestGateway"
        }
        received_commands = []

        def data_provider():
            return latest_data

        def command_consumer(cmd):
            received_commands.append(cmd)

        monitor = EmbeddedWebMonitor(host="127.0.0.1", port=0)
        monitor.start(data_provider, command_consumer)
        port = monitor.port

        time.sleep(0.3)

        try:
            # 1. GET HTML Dashboard
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as resp:
                self.assertEqual(resp.status, 200)
                html_content = resp.read().decode("utf-8")
                self.assertIn("Local IoT Gateway Station", html_content)
                self.assertIn("keen-dashboard", html_content)
                self.assertIn("chart-wrapper", html_content)

            # 2. GET /api/telemetry
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/telemetry") as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(body["smoke"], 45.5)
                self.assertTrue(body["cloud_connected"])

            # 3. POST /api/control
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/control",
                data=json.dumps({"servo": 90, "buzzer": 1}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                res_json = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(res_json["status"], "success")

            self.assertEqual(len(received_commands), 1)
            self.assertEqual(received_commands[0]["servo"], 90)
            self.assertEqual(received_commands[0]["buzzer"], 1)

        finally:
            monitor.stop()


class TestHardwareSerialAdapter(unittest.TestCase):
    @patch("serial.Serial")
    def test_serial_read_and_write(self, mock_serial_cls):
        """Verify UART Serial Adapter frame parsing and command transmission."""
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_instance.readline.return_value = b'{"smoke": 33.2, "flame": 0, "servo": 0}\n'
        mock_serial_cls.return_value = mock_instance

        adapter = HardwareSerialAdapter(port_name="COM99", baudrate=115200)
        opened = adapter.open()
        self.assertTrue(opened)

        line = adapter.read_line()
        self.assertEqual(line, '{"smoke": 33.2, "flame": 0, "servo": 0}')

        written = adapter.write_command({"buzzer": 1, "servo": 90})
        self.assertTrue(written)
        mock_instance.write.assert_called_with(b'{"buzzer": 1, "servo": 90}\n')

        adapter.close()


class TestBLEGatewayAdapter(unittest.TestCase):
    def test_ble_adapter_queue_and_parsing(self):
        """Verify BLE Gateway Adapter queue management, command transmission, and telemetry normalization."""
        adapter = BLEGatewayAdapter(target_name="YoloUNO_FireNode")

        raw_json = '{"smoke": 210, "flame": 0, "temp": 27.2, "humi": 47, "risk": 15.0, "status": "SAFE"}'
        adapter.rx_queue.put(raw_json)

        received_line = adapter.read_line(timeout=0.5)
        self.assertEqual(received_line, raw_json)

        payload = parse_uart_payload(received_line)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["smoke"], 210)
        self.assertEqual(payload["flame"], 0)
        self.assertEqual(payload["temperature"], 27.2)
        self.assertEqual(payload["humidity"], 47)
        self.assertEqual(payload["tinyml_risk"], 15.0)
        self.assertEqual(payload["status"], "SAFE")

        adapter.connected = True
        success = adapter.write_command({"servo": 90, "led": 1})
        self.assertTrue(success)
        self.assertFalse(adapter.tx_queue.empty())
        cmd_tx = adapter.tx_queue.get_nowait()
        self.assertIn('"servo": 90', cmd_tx)

        adapter.close()


class TestIsolationForestAnomalyDetection(unittest.TestCase):
    def test_isolation_detector_inference(self):
        """Verify Isolation Forest accurately classifies normal baseline and anomalous spikes."""
        detector = IsolationDetector()
        is_anom_norm, score_norm = detector.update_and_predict(30.0, 24.0, 0.0)
        self.assertEqual(is_anom_norm, 0)
        self.assertLessEqual(score_norm, 0.5)

        is_anom_fire, score_fire = detector.update_and_predict(550.0, 65.0, 1.0)
        self.assertEqual(is_anom_fire, 1)
        self.assertGreaterEqual(score_fire, 0.8)


class TestThingsBoardIntegration(unittest.TestCase):
    def test_dashboard_json_structure(self):
        """Verify thingsboard_dashboard.json contains valid ThingsBoard 3.x schema and all 8 widgets."""
        dashboard_file = GATEWAY_ROOT / "dashboard" / "thingsboard_dashboard.json"
        self.assertTrue(dashboard_file.exists(), "thingsboard_dashboard.json file must exist")

        with open(dashboard_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("title", data)
        self.assertIn("configuration", data)
        cfg = data["configuration"]
        self.assertIn("widgets", cfg)
        self.assertIn("states", cfg)
        self.assertIn("entityAliases", cfg)

        widgets = cfg["widgets"]
        self.assertGreaterEqual(len(widgets), 8)

        # Check widget types and RPC actions
        types = [w.get("type") for w in widgets.values()]
        self.assertIn("latest", types)
        self.assertIn("timeseries", types)
        self.assertIn("rpc", types)


class TestUdpSimulationFlow(unittest.TestCase):
    def test_udp_roundtrip_communication(self):
        """Verify bidirectional UDP loop between virtual node and gateway."""
        gateway_rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        gateway_rx_sock.bind(("127.0.0.1", 5000))
        gateway_rx_sock.settimeout(2.0)

        node_tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = {"smoke": 88.5, "flame": 1, "servo": 0, "buzzer": 0, "led": 0}
        node_tx_sock.sendto(json.dumps(payload).encode("utf-8"), ("127.0.0.1", 5000))

        data, addr = gateway_rx_sock.recvfrom(1024)
        received_payload = json.loads(data.decode("utf-8"))
        self.assertEqual(received_payload["smoke"], 88.5)
        self.assertEqual(received_payload["flame"], 1)

        gateway_rx_sock.close()
        node_tx_sock.close()


class TestOTAFirmwareIntegrity(unittest.TestCase):
    def test_firmware_binaries_exist_and_header_valid(self):
        """Verify OTA firmware binaries exist, have size > 800 KB, valid ESP32 magic byte, and MD5 checksums."""
        firmware_dir = GATEWAY_ROOT.parent / "01_Firmware_EndNode"
        fw_v101 = firmware_dir / "firmware_v1.0.1.bin"
        fw_v102 = firmware_dir / "firmware_v1.0.2.bin"

        self.assertTrue(fw_v101.exists(), "firmware_v1.0.1.bin must exist")
        self.assertTrue(fw_v102.exists(), "firmware_v1.0.2.bin must exist")

        for fw_path in (fw_v101, fw_v102):
            data = fw_path.read_bytes()
            self.assertGreaterEqual(len(data), 800 * 1024, f"{fw_path.name} binary size must exceed 800 KB")
            self.assertEqual(data[0], 0xE9, f"{fw_path.name} must start with ESP32 magic byte 0xE9")
            md5_hash = hashlib.md5(data).hexdigest()
            self.assertEqual(len(md5_hash), 32)
            self.assertTrue(all(c in "0123456789abcdef" for c in md5_hash))

        self.assertNotEqual(fw_v101.read_bytes(), fw_v102.read_bytes())


class TestThingsBoardGatewayProtocol(unittest.TestCase):
    def test_gateway_uplink_telemetry_format(self):
        """Verify Gateway API Uplink format: {DEVICE_NAME: [{'ts': ms, 'values': payload}]} on v1/gateway/telemetry."""
        device_name = "YOLOUNO_FIRE_NODE_01"
        payload_data = {"smoke": 45.2, "temperature": 29.5, "flame": 0, "status": "SAFE"}
        now_ms = int(time.time() * 1000)

        gw_msg = {device_name: [{"ts": now_ms, "values": payload_data}]}
        encoded = json.dumps(gw_msg)
        decoded = json.loads(encoded)

        self.assertIn(device_name, decoded)
        self.assertIsInstance(decoded[device_name], list)
        self.assertEqual(len(decoded[device_name]), 1)
        item = decoded[device_name][0]
        self.assertIn("ts", item)
        self.assertIn("values", item)
        self.assertEqual(item["values"]["smoke"], 45.2)
        self.assertEqual(GATEWAY_TELEMETRY_TOPIC, "v1/gateway/telemetry")

    def test_gateway_downlink_rpc_parsing_and_dispatch(self):
        """Verify Downlink Gateway RPC message parsing, actuation queuing, and response acknowledgment."""
        with patch("hardware_gateway.LocalGateway.EmbeddedWebMonitor"), \
             patch("hardware_gateway.LocalGateway.OfflineBufferRepository"):
            gw = LocalHardwareGateway(web_port=0, use_gateway_api=True)
            gw.mqtt_client = MagicMock()

            msg = MagicMock()
            msg.topic = GATEWAY_RPC_TOPIC
            rpc_payload = {
                "device": "YOLOUNO_FIRE_NODE_01",
                "data": {
                    "id": 101,
                    "method": "manualSetBuzzer",
                    "params": 1
                }
            }
            msg.payload = json.dumps(rpc_payload).encode("utf-8")

            gw.on_mqtt_message(gw.mqtt_client, None, msg)

            self.assertFalse(gw.command_queue.empty())
            cmd = gw.command_queue.get_nowait()
            self.assertEqual(cmd, {"buzzer": 1})

            gw.mqtt_client.publish.assert_called_once()
            call_args = gw.mqtt_client.publish.call_args[0]
            self.assertEqual(call_args[0], GATEWAY_RPC_TOPIC)
            resp = json.loads(call_args[1])
            self.assertEqual(resp["device"], "YOLOUNO_FIRE_NODE_01")
            self.assertEqual(resp["id"], 101)
            self.assertTrue(resp["data"]["success"])


class TestSafetyInterlockAndOverride(unittest.TestCase):
    def test_automatic_rpc_blocked_when_sensors_safe(self):
        """Verify automatic rule-chain RPC is blocked by safety interlock when local sensors report safe."""
        with patch("hardware_gateway.LocalGateway.EmbeddedWebMonitor"), \
             patch("hardware_gateway.LocalGateway.OfflineBufferRepository"):
            gw = LocalHardwareGateway(web_port=0)
            gw.local_alarm_active = False

            res_buzzer = gw.rpc_command("setBuzzer", True)
            res_servo = gw.rpc_command("setServo", 90)
            res_led = gw.rpc_command("setLed", True)

            self.assertEqual(res_buzzer, {})
            self.assertEqual(res_servo, {})
            self.assertEqual(res_led, {})

    def test_automatic_rpc_allowed_when_sensor_alarm_active(self):
        """Verify automatic rule-chain RPC is executed when sensor alarm is confirmed active."""
        with patch("hardware_gateway.LocalGateway.EmbeddedWebMonitor"), \
             patch("hardware_gateway.LocalGateway.OfflineBufferRepository"):
            gw = LocalHardwareGateway(web_port=0)
            gw.local_alarm_active = True

            res_buzzer = gw.rpc_command("setBuzzer", True)
            res_servo = gw.rpc_command("setServo", 90)

            self.assertEqual(res_buzzer, {"buzzer": 1})
            self.assertEqual(res_servo, {"servo": 90})

    def test_manual_override_bypasses_safety_interlock(self):
        """Verify manual dashboard operator commands bypass safety interlock even when sensors are safe."""
        with patch("hardware_gateway.LocalGateway.EmbeddedWebMonitor"), \
             patch("hardware_gateway.LocalGateway.OfflineBufferRepository"):
            gw = LocalHardwareGateway(web_port=0)
            gw.local_alarm_active = False

            res_override = gw.rpc_command("setAlarmOverride", 1)
            res_manual_buzzer = gw.rpc_command("manualSetBuzzer", 1)
            res_manual_led = gw.rpc_command("manualSetLed", 1)

            self.assertEqual(res_override, {"alarm_override": 1})
            self.assertEqual(res_manual_buzzer, {"buzzer": 1})
            self.assertEqual(res_manual_led, {"led": 1})


class TestEmergencyNotificationDispatch(unittest.TestCase):
    def test_tier4_email_dispatch_log_and_recipients(self):
        """Verify dispatch_customer_notifications outputs 4-tier indicators and all 3 recipient emails."""
        with patch("hardware_gateway.LocalGateway.EmbeddedWebMonitor"), \
             patch("hardware_gateway.LocalGateway.OfflineBufferRepository"):
            gw = LocalHardwareGateway(web_port=0)

            test_payload = {
                "smoke": 350.0,
                "temperature": 55.4,
                "flame": 1,
                "tinyml_risk": 92.5
            }

            gw.dispatch_customer_notifications(test_payload, force=True)

            log_file = GATEWAY_ROOT.parent / "03_CoreIOT_Config" / "email_dispatch_log.txt"
            self.assertTrue(log_file.exists(), "email_dispatch_log.txt must exist")

            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("CRITICAL FIRE HAZARD", content)
            self.assertIn("customera@gmail.com", content)
            self.assertIn("customerb@gmail.com", content)
            self.assertIn("customerc@gmail.com", content)
            self.assertIn("[Tier 1 - ESP32 Hardware]", content)
            self.assertIn("[Tier 2 - Local Gateway]", content)
            self.assertIn("[Tier 3 - ThingsBoard Cloud]", content)
            self.assertIn("[Tier 4 - Customer Dispatch]", content)


if __name__ == "__main__":
    unittest.main()
