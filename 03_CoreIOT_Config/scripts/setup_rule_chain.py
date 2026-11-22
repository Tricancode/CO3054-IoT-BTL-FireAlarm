#!/usr/bin/env python3
"""
setup_rule_chain.py
===================
Automated Provisioner & Generator for ThingsBoard / CoreIOT RuleChain (Criterion T12 & T13).
Complies 100% with rule_chain_guide.md and LocalGateway.py.

Capabilities:
1. Generates exportable, native ThingsBoard 3.x RuleChain JSON ('fire_alarm_rule_chain.json')
   with visual layout coordinates, TBEL/JavaScript scripts, 3-actuator RPC lockdown branches,
   and Telegram Bot alert integrations.
2. Authenticates with ThingsBoard / CoreIOT REST API (localhost:9090 or app.coreiot.io).
3. Automatically creates/updates the 'Fire_Alarm_Rule_Chain' and uploads its metadata.
4. Allows customizing Telegram BOT_TOKEN and CHAT_ID via CLI flags or environment variables.
Strictly English logs, UI, and comments. Zero icons or emojis.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (TB_RuleChain) %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("TB_RuleChain")

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR.parent
RULE_CHAINS_DIR = CONFIG_DIR / "rule_chains"
RULE_CHAIN_JSON_FILE = RULE_CHAINS_DIR / "fire_alarm_rule_chain.json"

DEFAULT_TB_HOST = os.getenv("TB_REST_HOST", "http://localhost:9090").rstrip("/")
DEFAULT_TB_USER = os.getenv("TB_REST_USER", "tenant@thingsboard.org")
DEFAULT_TB_PASS = os.getenv("TB_REST_PASS", "tenant")
RULE_CHAIN_NAME = "Fire_Alarm_Rule_Chain"


def build_rule_chain_definition(
    telegram_bot_token: str = "<YOUR_BOT_TOKEN>",
    telegram_chat_id: str = "<YOUR_TELEGRAM_CHAT_ID>"
) -> Dict[str, Any]:
    """Builds the complete ThingsBoard 3.x RuleChain specification with layout and node configs."""

    # 1. TBEL & JS scripts
    switch_tbel = (
        "var SMOKE_WARN = 1800.0;\n"
        "var SMOKE_CRIT = 2000.0;\n\n"
        "var smoke = (msg.smoke != null) ? Double.parseDouble(String.valueOf(msg.smoke)) : 0.0;\n"
        "var flame = (msg.flame != null) ? Integer.parseInt(String.valueOf(msg.flame)) : 0;\n"
        "var isAnomaly = (msg.is_anomaly != null) ? Integer.parseInt(String.valueOf(msg.is_anomaly)) : 0;\n"
        "var anomalyScore = (msg.anomaly_score != null) ? Double.parseDouble(String.valueOf(msg.anomaly_score)) : 0.0;\n\n"
        "if (flame == 1 || smoke > SMOKE_CRIT) {\n"
        "    return ['Critical'];\n"
        "} else if (smoke >= SMOKE_WARN || isAnomaly == 1) {\n"
        "    return ['Warning'];\n"
        "} else {\n"
        "    return ['Safe'];\n"
        "}"
    )

    switch_js = (
        "var SMOKE_WARN = 1800.0;\n"
        "var SMOKE_CRIT = 2000.0;\n\n"
        "var smoke = Number(msg.smoke || 0);\n"
        "var flame = Number(msg.flame || 0);\n"
        "var isAnomaly = Number(msg.is_anomaly || 0);\n"
        "var anomalyScore = Number(msg.anomaly_score || 0);\n\n"
        "if (flame === 1 || smoke > SMOKE_CRIT) {\n"
        "    return ['Critical'];\n"
        "} else if (smoke >= SMOKE_WARN || isAnomaly === 1) {\n"
        "    return ['Warning'];\n"
        "} else {\n"
        "    return ['Safe'];\n"
        "}"
    )

    alarm_crit_details_tbel = (
        "var details = {};\n"
        "if (metadata.prevAlarmDetails != null) {\n"
        "    details = JSON.parse(metadata.prevAlarmDetails);\n"
        "}\n"
        "details.smoke = msg.smoke;\n"
        "details.flame = msg.flame;\n"
        "details.temperature = (msg.temperature != null) ? msg.temperature : 24.0;\n"
        "details.is_anomaly = msg.is_anomaly;\n"
        "details.anomaly_score = msg.anomaly_score;\n"
        "details.action = 'AUTO_LOCKDOWN: Servo=90, Buzzer=1, LED=1';\n"
        "return details;"
    )

    alarm_warn_details_tbel = (
        "var details = {};\n"
        "if (metadata.prevAlarmDetails != null) {\n"
        "    details = JSON.parse(metadata.prevAlarmDetails);\n"
        "}\n"
        "details.smoke = msg.smoke;\n"
        "details.flame = msg.flame;\n"
        "details.temperature = (msg.temperature != null) ? msg.temperature : 24.0;\n"
        "details.is_anomaly = msg.is_anomaly;\n"
        "details.anomaly_score = msg.anomaly_score;\n"
        "details.action = 'EARLY_WARNING_MONITORING';\n"
        "return details;"
    )

    telegram_crit_tbel = (
        "var deviceName = (metadata.deviceName != null) ? metadata.deviceName : 'FireAlarm_Gateway';\n"
        "var details = (msg.details != null) ? msg.details : msg;\n\n"
        "var smoke = (details.smoke != null) ? details.smoke : 'N/A';\n"
        "var flame = (details.flame != null) ? details.flame : 'N/A';\n"
        "var temp = (details.temperature != null) ? details.temperature : 'N/A';\n"
        "var score = (details.anomaly_score != null) ? details.anomaly_score : 'N/A';\n\n"
        "var text = '[CRITICAL FIRE ALARM]\\n' +\n"
        "    'Device: ' + deviceName + '\\n' +\n"
        "    'Smoke: ' + smoke + ' ppm\\n' +\n"
        "    'Flame: ' + flame + '\\n' +\n"
        "    'Temperature: ' + temp + ' C\\n' +\n"
        "    'AI Anomaly Score: ' + score + '\\n' +\n"
        "    'Auto Action: Servo=90 (Closed), Buzzer=ON, LED=ON';\n\n"
        "var newMsg = {\n"
        f"    'chat_id': '{telegram_chat_id}',\n"
        "    'text': text\n"
        "};\n\n"
        "return {msg: newMsg, metadata: metadata, msgType: 'POST_TELEMETRY_REQUEST'};"
    )

    telegram_clear_tbel = (
        "var deviceName = (metadata.deviceName != null) ? metadata.deviceName : 'FireAlarm_Gateway';\n\n"
        "var text = '[RESOLVED] Fire Alarm Cleared - System Safe\\n' +\n"
        "    'Device: ' + deviceName + '\\n' +\n"
        "    'Status: All fire hazards cleared. Environment normal.\\n' +\n"
        "    'Auto Action: Servo=0 (Open), Buzzer=OFF, LED=OFF';\n\n"
        "var newMsg = {\n"
        f"    'chat_id': '{telegram_chat_id}',\n"
        "    'text': text\n"
        "};\n\n"
        "return {msg: newMsg, metadata: metadata, msgType: 'POST_TELEMETRY_REQUEST'};"
    )

    # 2. Define node list with visual coordinates (layoutX, layoutY)
    nodes = [
        # 0: Switch
        {
            "type": "org.thingsboard.rule.engine.filter.TbJsSwitchNode",
            "name": "Fire Level Classifier",
            "configurationVersion": 0,
            "configuration": {
                "scriptLang": "TBEL",
                "tbelScript": switch_tbel,
                "jsScript": switch_js
            },
            "additionalInfo": {"layoutX": 160, "layoutY": 350}
        },
        # 1: Create Alarm Critical
        {
            "type": "org.thingsboard.rule.engine.action.TbCreateAlarmNode",
            "name": "Create Fire Critical Alarm",
            "configurationVersion": 0,
            "configuration": {
                "alarmType": "FIRE_ALARM_CRITICAL",
                "severity": "CRITICAL",
                "propagate": False,
                "scriptLang": "TBEL",
                "alarmDetailsBuildTbel": alarm_crit_details_tbel,
                "alarmDetailsBuildJs": alarm_crit_details_tbel,
                "useMessageAlarmData": False,
                "overwriteAlarmDetails": False
            },
            "additionalInfo": {"layoutX": 480, "layoutY": 150}
        },
        # 2: Create Alarm Warning
        {
            "type": "org.thingsboard.rule.engine.action.TbCreateAlarmNode",
            "name": "Create Fire Warning Alarm",
            "configurationVersion": 0,
            "configuration": {
                "alarmType": "FIRE_ALARM_WARNING",
                "severity": "WARNING",
                "propagate": False,
                "scriptLang": "TBEL",
                "alarmDetailsBuildTbel": alarm_warn_details_tbel,
                "alarmDetailsBuildJs": alarm_warn_details_tbel,
                "useMessageAlarmData": False,
                "overwriteAlarmDetails": False
            },
            "additionalInfo": {"layoutX": 480, "layoutY": 350}
        },
        # 3: Clear Critical Alarm
        {
            "type": "org.thingsboard.rule.engine.action.TbClearAlarmNode",
            "name": "Clear Critical Alarm",
            "configurationVersion": 0,
            "configuration": {
                "alarmType": "FIRE_ALARM_CRITICAL",
                "scriptLang": "TBEL",
                "alarmDetailsBuildTbel": "return {};",
                "alarmDetailsBuildJs": "return {};"
            },
            "additionalInfo": {"layoutX": 480, "layoutY": 550}
        },
        # 4: Clear Warning Alarm
        {
            "type": "org.thingsboard.rule.engine.action.TbClearAlarmNode",
            "name": "Clear Warning Alarm",
            "configurationVersion": 0,
            "configuration": {
                "alarmType": "FIRE_ALARM_WARNING",
                "scriptLang": "TBEL",
                "alarmDetailsBuildTbel": "return {};",
                "alarmDetailsBuildJs": "return {};"
            },
            "additionalInfo": {"layoutX": 480, "layoutY": 680}
        },
        # 5: Transform RPC setServo(90)
        {
            "type": "org.thingsboard.rule.engine.transform.TbTransformMsgNode",
            "name": "Transform RPC setServo(90)",
            "configurationVersion": 0,
            "configuration": {
                "scriptLang": "TBEL",
                "tbelScript": 'var newMsg = { "method": "setServo", "params": 90 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};',
                "jsScript": 'var newMsg = { "method": "setServo", "params": 90 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};'
            },
            "additionalInfo": {"layoutX": 480, "layoutY": 50}
        },
        # 6: RPC setServo ON
        {
            "type": "org.thingsboard.rule.engine.rpc.TbSendRPCRequestNode",
            "name": "RPC setServo ON",
            "configurationVersion": 0,
            "configuration": {"timeoutInSeconds": 5},
            "additionalInfo": {"layoutX": 800, "layoutY": 50}
        },
        # 7: Transform RPC setBuzzer(1)
        {
            "type": "org.thingsboard.rule.engine.transform.TbTransformMsgNode",
            "name": "Transform RPC setBuzzer(1)",
            "configurationVersion": 0,
            "configuration": {
                "scriptLang": "TBEL",
                "tbelScript": 'var newMsg = { "method": "setBuzzer", "params": 1 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};',
                "jsScript": 'var newMsg = { "method": "setBuzzer", "params": 1 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};'
            },
            "additionalInfo": {"layoutX": 480, "layoutY": -60}
        },
        # 8: RPC setBuzzer ON
        {
            "type": "org.thingsboard.rule.engine.rpc.TbSendRPCRequestNode",
            "name": "RPC setBuzzer ON",
            "configurationVersion": 0,
            "configuration": {"timeoutInSeconds": 5},
            "additionalInfo": {"layoutX": 800, "layoutY": -60}
        },
        # 9: Transform RPC setLed(1)
        {
            "type": "org.thingsboard.rule.engine.transform.TbTransformMsgNode",
            "name": "Transform RPC setLed(1)",
            "configurationVersion": 0,
            "configuration": {
                "scriptLang": "TBEL",
                "tbelScript": 'var newMsg = { "method": "setLed", "params": 1 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};',
                "jsScript": 'var newMsg = { "method": "setLed", "params": 1 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};'
            },
            "additionalInfo": {"layoutX": 480, "layoutY": -170}
        },
        # 10: RPC setLed ON
        {
            "type": "org.thingsboard.rule.engine.rpc.TbSendRPCRequestNode",
            "name": "RPC setLed ON",
            "configurationVersion": 0,
            "configuration": {"timeoutInSeconds": 5},
            "additionalInfo": {"layoutX": 800, "layoutY": -170}
        },
        # 11: Transform RPC setServo(0)
        {
            "type": "org.thingsboard.rule.engine.transform.TbTransformMsgNode",
            "name": "Transform RPC setServo(0)",
            "configurationVersion": 0,
            "configuration": {
                "scriptLang": "TBEL",
                "tbelScript": 'var newMsg = { "method": "setServo", "params": 0 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};',
                "jsScript": 'var newMsg = { "method": "setServo", "params": 0 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};'
            },
            "additionalInfo": {"layoutX": 800, "layoutY": 450}
        },
        # 12: RPC setServo OFF
        {
            "type": "org.thingsboard.rule.engine.rpc.TbSendRPCRequestNode",
            "name": "RPC setServo OFF",
            "configurationVersion": 0,
            "configuration": {"timeoutInSeconds": 5},
            "additionalInfo": {"layoutX": 1120, "layoutY": 450}
        },
        # 13: Transform RPC setBuzzer(0)
        {
            "type": "org.thingsboard.rule.engine.transform.TbTransformMsgNode",
            "name": "Transform RPC setBuzzer(0)",
            "configurationVersion": 0,
            "configuration": {
                "scriptLang": "TBEL",
                "tbelScript": 'var newMsg = { "method": "setBuzzer", "params": 0 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};',
                "jsScript": 'var newMsg = { "method": "setBuzzer", "params": 0 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};'
            },
            "additionalInfo": {"layoutX": 800, "layoutY": 560}
        },
        # 14: RPC setBuzzer OFF
        {
            "type": "org.thingsboard.rule.engine.rpc.TbSendRPCRequestNode",
            "name": "RPC setBuzzer OFF",
            "configurationVersion": 0,
            "configuration": {"timeoutInSeconds": 5},
            "additionalInfo": {"layoutX": 1120, "layoutY": 560}
        },
        # 15: Transform RPC setLed(0)
        {
            "type": "org.thingsboard.rule.engine.transform.TbTransformMsgNode",
            "name": "Transform RPC setLed(0)",
            "configurationVersion": 0,
            "configuration": {
                "scriptLang": "TBEL",
                "tbelScript": 'var newMsg = { "method": "setLed", "params": 0 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};',
                "jsScript": 'var newMsg = { "method": "setLed", "params": 0 };\nreturn {msg: newMsg, metadata: metadata, msgType: "POST_TELEMETRY_REQUEST"};'
            },
            "additionalInfo": {"layoutX": 800, "layoutY": 670}
        },
        # 16: RPC setLed OFF
        {
            "type": "org.thingsboard.rule.engine.rpc.TbSendRPCRequestNode",
            "name": "RPC setLed OFF",
            "configurationVersion": 0,
            "configuration": {"timeoutInSeconds": 5},
            "additionalInfo": {"layoutX": 1120, "layoutY": 670}
        },
        # 17: Build Telegram Critical Payload
        {
            "type": "org.thingsboard.rule.engine.transform.TbTransformMsgNode",
            "name": "Build Telegram Critical Payload",
            "configurationVersion": 0,
            "configuration": {
                "scriptLang": "TBEL",
                "tbelScript": telegram_crit_tbel,
                "jsScript": telegram_crit_tbel
            },
            "additionalInfo": {"layoutX": 800, "layoutY": 150}
        },
        # 18: Send Telegram Critical Alert
        {
            "type": "org.thingsboard.rule.engine.rest.TbRestApiCallNode",
            "name": "Send Telegram Critical Alert",
            "configurationVersion": 3,
            "configuration": {
                "restEndpointUrlPattern": f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage",
                "requestMethod": "POST",
                "headers": {"Content-Type": "application/json"},
                "useSimpleClientHttpFactory": True,
                "readTimeoutMs": 5000,
                "maxParallelRequestsCount": 0,
                "parseToPlainText": False,
                "enableProxy": False,
                "useSystemProxyProperties": False,
                "credentials": {"type": "anonymous"},
                "ignoreRequestBody": False
            },
            "additionalInfo": {"layoutX": 1120, "layoutY": 150}
        },
        # 19: Build Telegram Cleared Payload
        {
            "type": "org.thingsboard.rule.engine.transform.TbTransformMsgNode",
            "name": "Build Telegram Cleared Payload",
            "configurationVersion": 0,
            "configuration": {
                "scriptLang": "TBEL",
                "tbelScript": telegram_clear_tbel,
                "jsScript": telegram_clear_tbel
            },
            "additionalInfo": {"layoutX": 800, "layoutY": 780}
        },
        # 20: Send Telegram Cleared Alert
        {
            "type": "org.thingsboard.rule.engine.rest.TbRestApiCallNode",
            "name": "Send Telegram Cleared Alert",
            "configurationVersion": 3,
            "configuration": {
                "restEndpointUrlPattern": f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage",
                "requestMethod": "POST",
                "headers": {"Content-Type": "application/json"},
                "useSimpleClientHttpFactory": True,
                "readTimeoutMs": 5000,
                "maxParallelRequestsCount": 0,
                "parseToPlainText": False,
                "enableProxy": False,
                "useSystemProxyProperties": False,
                "credentials": {"type": "anonymous"},
                "ignoreRequestBody": False
            },
            "additionalInfo": {"layoutX": 1120, "layoutY": 780}
        }
    ]

    # 3. Define connection relationships
    connections = [
        # From Switch (0)
        {"fromIndex": 0, "toIndex": 1, "type": "Critical"},
        {"fromIndex": 0, "toIndex": 2, "type": "Warning"},
        {"fromIndex": 0, "toIndex": 3, "type": "Warning"},
        {"fromIndex": 0, "toIndex": 3, "type": "Safe"},
        {"fromIndex": 0, "toIndex": 4, "type": "Safe"},

        # Critical Alarm -> Telegram
        {"fromIndex": 1, "toIndex": 17, "type": "Created"},
        {"fromIndex": 1, "toIndex": 5, "type": "Created"},
        {"fromIndex": 1, "toIndex": 7, "type": "Created"},
        {"fromIndex": 1, "toIndex": 9, "type": "Created"},
        {"fromIndex": 17, "toIndex": 18, "type": "Success"},

        # Critical RPCs
        {"fromIndex": 5, "toIndex": 6, "type": "Success"},
        {"fromIndex": 7, "toIndex": 8, "type": "Success"},
        {"fromIndex": 9, "toIndex": 10, "type": "Success"},

        # Clear Critical Alarm -> Reset RPCs & Telegram Clear
        {"fromIndex": 3, "toIndex": 11, "type": "Cleared"},
        {"fromIndex": 3, "toIndex": 13, "type": "Cleared"},
        {"fromIndex": 3, "toIndex": 15, "type": "Cleared"},
        {"fromIndex": 3, "toIndex": 19, "type": "Cleared"},

        # Reset RPCs
        {"fromIndex": 11, "toIndex": 12, "type": "Success"},
        {"fromIndex": 13, "toIndex": 14, "type": "Success"},
        {"fromIndex": 15, "toIndex": 16, "type": "Success"},
        {"fromIndex": 19, "toIndex": 20, "type": "Success"}
    ]

    rule_chain = {
        "name": RULE_CHAIN_NAME,
        "type": "CORE",
        "debugMode": False,
        "root": False,
        "additionalInfo": {
            "description": "Industrial Fire Alarm & Suppression Rule Chain (Criterion T12 & T13)"
        }
    }

    metadata = {
        "firstNodeIndex": 0,
        "nodes": nodes,
        "connections": connections,
        "ruleChainConnections": None
    }

    return {
        "ruleChain": rule_chain,
        "metadata": metadata
    }


def export_rule_chain_file(target_file: Path, bot_token: str, chat_id: str) -> None:
    """Exports RuleChain definition to physical JSON file for Git versioning and 1-click manual import."""
    data = build_rule_chain_definition(bot_token, chat_id)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info(f"Successfully generated RuleChain JSON definition: {target_file}")


def get_auth_token(tb_host: str, username: str, password: str) -> str:
    """Authenticates against ThingsBoard REST API and returns JWT token."""
    login_url = f"{tb_host}/api/auth/login"
    res = requests.post(login_url, json={"username": username, "password": password}, timeout=10)
    res.raise_for_status()
    token = res.json().get("token")
    if not token:
        raise ValueError("Authentication response did not contain a valid JWT token.")
    return token


def provision_rule_chain_to_thingsboard(
    tb_host: str,
    username: str,
    password: str,
    bot_token: str,
    chat_id: str
) -> str:
    """Provisions or updates the RuleChain and its metadata via ThingsBoard REST API."""
    logger.info(f"Connecting to ThingsBoard at {tb_host}...")
    token = get_auth_token(tb_host, username, password)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Check if RuleChain already exists
    search_url = f"{tb_host}/api/ruleChains?pageSize=100&page=0&textSearch={requests.utils.quote(RULE_CHAIN_NAME)}"
    search_res = requests.get(search_url, headers=headers, timeout=10)
    search_res.raise_for_status()
    matched = [rc for rc in search_res.json().get("data", []) if rc["name"] == RULE_CHAIN_NAME]

    rule_chain_def = build_rule_chain_definition(bot_token, chat_id)

    if matched:
        rule_chain_id = matched[0]["id"]["id"]
        logger.info(f"Existing RuleChain found (ID: {rule_chain_id}). Updating definition...")
        rc_payload = dict(rule_chain_def["ruleChain"])
        rc_payload["id"] = {"entityType": "RULE_CHAIN", "id": rule_chain_id}
        res = requests.post(f"{tb_host}/api/ruleChain", json=rc_payload, headers=headers, timeout=10)
        res.raise_for_status()
    else:
        logger.info(f"Creating new RuleChain '{RULE_CHAIN_NAME}'...")
        res = requests.post(f"{tb_host}/api/ruleChain", json=rule_chain_def["ruleChain"], headers=headers, timeout=10)
        res.raise_for_status()
        rule_chain_id = res.json()["id"]["id"]
        logger.info(f"RuleChain created successfully (ID: {rule_chain_id}).")

    # 2. Upload metadata (Nodes & Connections)
    logger.info(f"Uploading node topology & relations for RuleChain ID: {rule_chain_id}...")
    metadata_payload = dict(rule_chain_def["metadata"])
    metadata_payload["ruleChainId"] = {"entityType": "RULE_CHAIN", "id": rule_chain_id}

    meta_res = requests.post(f"{tb_host}/api/ruleChain/metadata", json=metadata_payload, headers=headers, timeout=10)
    meta_res.raise_for_status()
    logger.info("RuleChain topology & metadata provisioned successfully.")

    return rule_chain_id


def link_to_root_rule_chain(tb_host: str, username: str, password: str, child_rc_id: str) -> bool:
    """Connects child RuleChain after 'Save Timeseries' in Root Rule Chain using TbRuleChainInputNode."""
    try:
        token = get_auth_token(tb_host, username, password)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Find Root Rule Chain
        rc_list = requests.get(f"{tb_host}/api/ruleChains?pageSize=50&page=0", headers=headers, timeout=10).json()
        root_rcs = [r for r in rc_list.get("data", []) if r.get("root") is True]
        if not root_rcs:
            logger.warning("Root Rule Chain not found. Skipping auto-linking.")
            return False

        root_id = root_rcs[0]["id"]["id"]
        meta = requests.get(f"{tb_host}/api/ruleChain/{root_id}/metadata", headers=headers, timeout=10).json()

        node_name = "Forward to Fire Alarm Rule Chain"
        existing = [i for i, n in enumerate(meta.get("nodes", [])) if n.get("name") == node_name]

        if not existing:
            # Find Save Timeseries node index
            save_ts_idx = None
            for idx, n in enumerate(meta.get("nodes", [])):
                if n.get("type") == "org.thingsboard.rule.engine.telemetry.TbMsgTimeseriesNode":
                    save_ts_idx = idx
                    break

            if save_ts_idx is None:
                logger.warning("Save Timeseries node not found in Root Rule Chain. Skipping auto-linking.")
                return False

            new_node = {
                "type": "org.thingsboard.rule.engine.flow.TbRuleChainInputNode",
                "name": node_name,
                "configurationVersion": 0,
                "configuration": {
                    "ruleChainId": child_rc_id
                },
                "additionalInfo": {
                    "layoutX": 1150,
                    "layoutY": 156
                }
            }
            meta["nodes"].append(new_node)
            new_node_idx = len(meta["nodes"]) - 1
            meta["connections"].append({
                "fromIndex": save_ts_idx,
                "toIndex": new_node_idx,
                "type": "Success"
            })

            save_meta_res = requests.post(f"{tb_host}/api/ruleChain/metadata", json=meta, headers=headers, timeout=10)
            save_meta_res.raise_for_status()
            logger.info("Successfully linked Root Rule Chain -> Fire_Alarm_Rule_Chain (via TbRuleChainInputNode).")
            return True
        else:
            logger.info("Root Rule Chain is already linked to Fire_Alarm_Rule_Chain.")
            return True

    except Exception as e:
        logger.warning(f"Could not automatically link to Root Rule Chain: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Automated ThingsBoard RuleChain Generator & Provisioner (T12 & T13)")
    parser.add_argument("--host", default=DEFAULT_TB_HOST, help="ThingsBoard REST API Host (default: http://localhost:9090)")
    parser.add_argument("--user", default=DEFAULT_TB_USER, help="ThingsBoard Tenant username")
    parser.add_argument("--password", default=DEFAULT_TB_PASS, help="ThingsBoard Tenant password")
    parser.add_argument("--telegram-token", default="<YOUR_BOT_TOKEN>", help="Telegram Bot Token")
    parser.add_argument("--telegram-chat-id", default="<YOUR_TELEGRAM_CHAT_ID>", help="Telegram Chat ID")
    parser.add_argument("--export-only", action="store_true", help="Only generate the JSON file without uploading via REST API")
    parser.add_argument("--no-root-link", action="store_true", help="Do not automatically link from Root Rule Chain")
    args = parser.parse_args()

    # 1. Always export the official clean JSON file
    export_rule_chain_file(RULE_CHAIN_JSON_FILE, args.telegram_token, args.telegram_chat_id)

    if args.export_only:
        print("Export completed. Skipped API provisioning (--export-only).")
        return

    # 2. Provision directly to ThingsBoard REST API
    try:
        rc_id = provision_rule_chain_to_thingsboard(
            tb_host=args.host,
            username=args.user,
            password=args.password,
            bot_token=args.telegram_token,
            chat_id=args.telegram_chat_id
        )

        if not args.no_root_link:
            link_to_root_rule_chain(args.host, args.user, args.password, rc_id)

        print("\n" + "=" * 68)
        print("     THINGSBOARD RULE CHAIN PROVISIONING SUCCESSFUL (T12 & T13)")
        print(f" -> RuleChain Name  : {RULE_CHAIN_NAME}")
        print(f" -> RuleChain ID    : {rc_id}")
        print(f" -> Direct Web URL  : {args.host}/ruleChains/{rc_id}")
        print(f" -> JSON Export File: {RULE_CHAIN_JSON_FILE}")
        print("=" * 68)

    except Exception as e:
        logger.error(f"RuleChain provisioning failed: {e}")
        print("\nTip: To generate only the file without connecting to ThingsBoard, use: --export-only")
        sys.exit(1)


if __name__ == "__main__":
    main()
