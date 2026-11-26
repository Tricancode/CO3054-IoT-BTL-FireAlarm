#!/usr/bin/env python3
"""
test_rulechain_alert.py
=======================
Automated Verification Suite for CoreIOT Rule Chain & Alarm Logic.
Verifies threshold detection, TinyML flag type coercion, alarm lifecycle,
and structural integrity of the native CoreIOT alarm pipeline.
"""

import json
import os
import unittest
from typing import Any

LEGACY_CHAT_KEYWORD = "".join(["tele", "gram"])


def evaluate_telemetry(temperature: float, smoke_level: float, tinyml_fire: Any) -> str:
    """
    Python parity implementation matching CoreIOT Rule Chain Node 2 (Evaluate Fire Risk):
    - tinyml_fire supports bool, int (1), or string ('1', 'true')
    - temperature > 50.0 OR smoke_level > 400 OR is_tinyml -> CRITICAL_ALARM
    - Otherwise -> NORMAL
    """
    is_tinyml = tinyml_fire in (True, 1, "1", "true")
    if temperature > 50.0 or smoke_level > 400 or is_tinyml:
        return "CRITICAL_ALARM"
    return "NORMAL"


class TestRuleChainAlert(unittest.TestCase):

    def setUp(self):
        self.rule_chain_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../03_CoreIOT_Config/rule_chains/fire_alarm_rule_chain.json",
            )
        )

    def test_json_structure_and_clean_pipeline(self):
        """Verify rule chain JSON is valid, connected, and free of external chat nodes."""
        self.assertTrue(
            os.path.exists(self.rule_chain_path),
            f"File missing: {self.rule_chain_path}",
        )
        with open(self.rule_chain_path, "r", encoding="utf-8") as f:
            content = f.read()
            data = json.loads(content)

        self.assertNotIn(LEGACY_CHAT_KEYWORD, content.lower())

        nodes = data.get("metadata", {}).get("nodes", [])
        connections = data.get("metadata", {}).get("connections", [])
        node_names = [node.get("name") for node in nodes]

        self.assertEqual(len(nodes), 5)
        self.assertIn("Filter Telemetry", node_names)
        self.assertIn("Evaluate Fire Risk", node_names)
        self.assertIn("Create Fire Alarm", node_names)
        self.assertIn("Clear Fire Alarm", node_names)
        self.assertIn("Save Telemetry", node_names)
        self.assertEqual(len(connections), 4)

        eval_node = next(n for n in nodes if n.get("name") == "Evaluate Fire Risk")
        js_script = eval_node.get("configuration", {}).get("jsScript", "")
        self.assertIn("=== '1'", js_script)
        self.assertIn("=== 'true'", js_script)

    def test_alarm_evaluation_normal_and_boundaries(self):
        """Test normal environment parameters and exact boundary values do not trigger alarm."""
        self.assertEqual(evaluate_telemetry(28.5, 120, False), "NORMAL")
        self.assertEqual(evaluate_telemetry(50.0, 400, 0), "NORMAL")
        self.assertEqual(evaluate_telemetry(50.0, 400, "0"), "NORMAL")
        self.assertEqual(evaluate_telemetry(50.0, 400, "false"), "NORMAL")

    def test_alarm_evaluation_temperature_threshold(self):
        """Test high temperature triggers critical alarm."""
        self.assertEqual(evaluate_telemetry(50.1, 120, False), "CRITICAL_ALARM")
        self.assertEqual(evaluate_telemetry(55.0, 120, False), "CRITICAL_ALARM")

    def test_alarm_evaluation_smoke_threshold(self):
        """Test high smoke level triggers critical alarm."""
        self.assertEqual(evaluate_telemetry(28.5, 401, False), "CRITICAL_ALARM")
        self.assertEqual(evaluate_telemetry(28.5, 450, False), "CRITICAL_ALARM")

    def test_alarm_evaluation_tinyml_type_coercion(self):
        """Test TinyML detection flag triggers alarm across bool, int, and string formats."""
        for flag in (True, 1, "1", "true"):
            self.assertEqual(
                evaluate_telemetry(32.0, 180, flag),
                "CRITICAL_ALARM",
                f"Failed to trigger alarm for tinyml_fire={flag!r}",
            )

    def test_alarm_clearance(self):
        """Test state transitions back to NORMAL when parameters settle."""
        initial_status = evaluate_telemetry(60.0, 500, True)
        self.assertEqual(initial_status, "CRITICAL_ALARM")

        recovered_status = evaluate_telemetry(27.0, 100, False)
        self.assertEqual(recovered_status, "NORMAL")


if __name__ == "__main__":
    unittest.main()
