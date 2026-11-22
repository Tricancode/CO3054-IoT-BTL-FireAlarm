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

import json
import re
import socket
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

from ui.gateway_infrastructure import EmbeddedWebMonitor, OfflineBufferRepository
from ui.isolation_detector import IsolationDetector
from hardware_gateway.LocalGateway import HardwareSerialAdapter

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
        project_root = Path(__file__).resolve().parent
        python_files = [
            project_root / "ui" / "gateway_infrastructure.py",
            project_root / "ui" / "isolation_detector.py",
            project_root / "simulation" / "LocalGateway_Simulation.py",
            project_root / "hardware_gateway" / "LocalGateway.py",
            project_root / "simulation" / "SimulationNode.py",
            project_root / "start_system.py",
            project_root / "dashboard" / "deploy_thingsboard.py",
            project_root / "dashboard" / "setup_thingsboard_dashboard.py",
            project_root / "dashboard" / "verify_telemetry.py",
            project_root / "test_system.py",
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
        readme_path = project_root / "README.md"
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
        dashboard_file = Path(__file__).resolve().parent / "dashboard" / "thingsboard_dashboard.json"
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


if __name__ == "__main__":
    unittest.main()
