#!/usr/bin/env python3
"""
setup_thingsboard_dashboard.py

Automated provisioner for ThingsBoard IoT Fire Alarm Gateway and Industrial Dashboard.
Authenticates with local ThingsBoard REST API, ensures 'FireAlarm_Gateway' device is registered
with the fixed access token ('i2tchqq1390qcxhun4zr'), provisions the industrial telemetry & RPC
dashboard with native ThingsBoard 3.x widget configurations, and exports to 'thingsboard_dashboard.json'.
"""

import os
import sys
import copy
import json
import time
import logging
from pathlib import Path
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("TB_Setup")

# Configuration via Environment Variables with Defaults
TB_HOST = os.getenv("TB_REST_HOST", "http://localhost:9090").rstrip("/")
REST_USER = os.getenv("TB_REST_USER", "tenant@thingsboard.org")
REST_PASS = os.getenv("TB_REST_PASS", "tenant")
DEVICE_NAME = os.getenv("TB_DEVICE_NAME", "FireAlarm_Gateway")
DEVICE_TOKEN = os.getenv("TB_DEVICE_TOKEN", "i2tchqq1390qcxhun4zr")
DASHBOARD_TITLE = "Industrial Fire Alarm & Suppression System"
DASHBOARD_FILE = Path(__file__).parent / "thingsboard_dashboard.json"


def wait_for_thingsboard(timeout: int = 180, interval: int = 3) -> bool:
    """Waits for the ThingsBoard REST service and Spring Security context to fully initialize."""
    logger.info(f"Checking connectivity to ThingsBoard instance at {TB_HOST} (Timeout: {timeout}s)...")
    start = time.time()
    login_url = f"{TB_HOST}/api/auth/login"
    
    while time.time() - start < timeout:
        try:
            # When Spring Boot is ready, POST /api/auth/login returns 401 or 200 (never 404 or ConnectionRefused)
            res = requests.post(login_url, json={"username": "probe", "password": "probe"}, timeout=5)
            if res.status_code in (200, 401):
                logger.info("ThingsBoard REST API is fully initialized and reachable.")
                return True
        except requests.RequestException:
            pass
        logger.info(f"Waiting for ThingsBoard container Spring Boot initialization... ({int(time.time() - start)}s elapsed)")
        time.sleep(interval)
    
    logger.error("ThingsBoard connection check timed out after %ds.", timeout)
    raise TimeoutError(f"ThingsBoard at {TB_HOST} did not become ready within {timeout}s. Please check Docker logs.")


def get_auth_token() -> str:
    """Authenticates with ThingsBoard and returns the JWT Bearer token."""
    login_url = f"{TB_HOST}/api/auth/login"
    payload = {"username": REST_USER, "password": REST_PASS}
    
    logger.info(f"Authenticating as '{REST_USER}'...")
    res = requests.post(login_url, json=payload, timeout=10)
    res.raise_for_status()
    token = res.json().get("token")
    if not token:
        raise ValueError("Failed to obtain JWT token from response.")
    logger.info("Authentication successful.")
    return token


def get_or_create_device(token: str) -> str:
    """
    Fetches the device ID if 'FireAlarm_Gateway' exists, otherwise creates it.
    Ensures the device access token matches DEVICE_TOKEN.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 1. Search for existing device
    search_url = f"{TB_HOST}/api/tenant/devices?deviceName={DEVICE_NAME}"
    logger.info(f"Checking for existing device '{DEVICE_NAME}'...")
    res = requests.get(search_url, headers=headers, timeout=10)
    
    if res.status_code == 200:
        device_data = res.json()
        device_id = device_data["id"]["id"]
        logger.info(f"Device '{DEVICE_NAME}' exists with ID: {device_id}")
    elif res.status_code == 404:
        # Create device
        create_url = f"{TB_HOST}/api/device"
        payload = {
            "name": DEVICE_NAME,
            "type": "Gateway",
            "label": "Fire Alarm Gateway Node",
            "additionalInfo": {"gateway": True, "description": "ThingsBoard IoT Gateway Node"}
        }
        logger.info(f"Creating device '{DEVICE_NAME}'...")
        create_res = requests.post(create_url, json=payload, headers=headers, timeout=10)
        create_res.raise_for_status()
        device_id = create_res.json()["id"]["id"]
        logger.info(f"Created device '{DEVICE_NAME}' (ID: {device_id})")
    else:
        res.raise_for_status()

    # 2. Update Access Token Credentials if required
    cred_url = f"{TB_HOST}/api/device/{device_id}/credentials"
    cred_res = requests.get(cred_url, headers=headers, timeout=10)
    cred_res.raise_for_status()
    creds = cred_res.json()

    if creds.get("credentialsId") != DEVICE_TOKEN:
        logger.info(f"Configuring device access token to '{DEVICE_TOKEN}'...")
        cred_payload = {
            "id": creds.get("id"),
            "deviceId": {"id": device_id, "entityType": "DEVICE"},
            "credentialsType": "ACCESS_TOKEN",
            "credentialsId": DEVICE_TOKEN
        }
        post_cred_url = f"{TB_HOST}/api/device/credentials"
        requests.post(post_cred_url, json=cred_payload, headers=headers, timeout=10).raise_for_status()
        logger.info("Device access token successfully set.")
    else:
        logger.info("Device access token is already up to date.")

    return device_id


def fetch_system_widget_templates(token: str) -> dict:
    """Fetches native widget default configurations to guarantee 100% ThingsBoard 3.x schema compliance."""
    headers = {"Authorization": f"Bearer {token}"}
    templates = {}

    # 1. Analogue Radial Gauge
    res = requests.get(f"{TB_HOST}/api/widgetTypes?isSystem=true&bundleAlias=analogue_gauges", headers=headers, timeout=10)
    if res.status_code == 200:
        for w in res.json():
            if w.get("fqn") == "analogue_gauges.radial_gauge_canvas_gauges":
                templates["radial_gauge"] = json.loads(w["descriptor"]["defaultConfig"])
                break

    # 2. Digital Simple Gauge
    res = requests.get(f"{TB_HOST}/api/widgetTypes?isSystem=true&bundleAlias=digital_gauges", headers=headers, timeout=10)
    if res.status_code == 200:
        for w in res.json():
            if w.get("fqn") == "digital_gauges.simple_gauge_justgage":
                templates["digital_gauge"] = json.loads(w["descriptor"]["defaultConfig"])
                break

    # 3. Control Switches
    res = requests.get(f"{TB_HOST}/api/widgetTypes?isSystem=true&bundleAlias=control_widgets", headers=headers, timeout=10)
    if res.status_code == 200:
        for w in res.json():
            if w.get("fqn") == "control_widgets.round_switch":
                templates["round_switch"] = json.loads(w["descriptor"]["defaultConfig"])
            elif w.get("fqn") == "control_widgets.switch_control":
                templates["switch_control"] = json.loads(w["descriptor"]["defaultConfig"])

    # 4. Timeseries Chart template from sample Thermostats dashboard
    res = requests.get(f"{TB_HOST}/api/tenant/dashboards?pageSize=10&page=0", headers=headers, timeout=10)
    if res.status_code == 200:
        for item in res.json().get("data", []):
            if item.get("title") == "Thermostats":
                db_id = item["id"]["id"]
                db_detail = requests.get(f"{TB_HOST}/api/dashboard/{db_id}", headers=headers, timeout=10).json()
                for wid, w in db_detail.get("configuration", {}).get("widgets", {}).items():
                    if w.get("typeFullFqn") == "system.time_series_chart":
                        templates["time_series_chart"] = copy.deepcopy(w.get("config", {}))
                        break
                break

    # 5. Value Card (cards.value_card)
    res = requests.get(f"{TB_HOST}/api/widgetTypes?isSystem=true&bundleAlias=cards", headers=headers, timeout=10)
    if res.status_code == 200:
        for w in res.json():
            if w.get("fqn") == "cards.value_card":
                templates["value_card"] = json.loads(w["descriptor"]["defaultConfig"])
                break

    return templates


def generate_dashboard_json(device_id: str, templates: dict) -> dict:
    """Generates the ThingsBoard 3.x UI Dashboard Schema for Fire Alarm Gateway."""
    alias_id = "11111111-2222-3333-4444-555555555555"
    
    # Pre-defined deterministic UUIDs for widgets
    id_smoke_gauge = "a1111111-0000-0000-0000-000000000001"
    id_flame_status = "a1111111-0000-0000-0000-000000000002"
    id_chart = "a1111111-0000-0000-0000-000000000003"
    id_servo = "a1111111-0000-0000-0000-000000000004"
    id_buzzer = "a1111111-0000-0000-0000-000000000005"
    id_led = "a1111111-0000-0000-0000-000000000006"
    id_anom_status = "a1111111-0000-0000-0000-000000000007"
    id_anom_score = "a1111111-0000-0000-0000-000000000008"
    id_temp_card = "a1111111-0000-0000-0000-000000000009"

    # --- 1. Smoke Radial Gauge ---
    smoke_cfg = copy.deepcopy(templates.get("radial_gauge", {}))
    smoke_cfg["title"] = "MQ-2 Raw ADC"
    smoke_cfg["showTitle"] = True
    smoke_cfg["units"] = "ADC"
    smoke_cfg.setdefault("settings", {})
    smoke_cfg["settings"]["minValue"] = 0
    smoke_cfg["settings"]["maxValue"] = 4095
    smoke_cfg["settings"]["highlights"] = [
        {"from": 0, "to": 1800, "color": "#4caf50"},
        {"from": 1800, "to": 2000, "color": "#ff9800"},
        {"from": 2000, "to": 4095, "color": "#f44336"}
    ]
    smoke_cfg["datasources"] = [
        {
            "type": "entity",
            "entityAliasId": alias_id,
            "dataKeys": [
                {
                    "name": "smoke",
                    "type": "timeseries",
                    "label": "Smoke PPM",
                    "color": "#d32f2f",
                    "settings": {},
                    "_hash": 0.11
                }
            ]
        }
    ]

    # --- 2. Flame Detector Status ---
    flame_cfg = copy.deepcopy(templates.get("digital_gauge", {}))
    flame_cfg["title"] = "Flame Detector Status"
    flame_cfg["showTitle"] = True
    flame_cfg["units"] = ""
    flame_cfg.setdefault("settings", {})
    flame_cfg["settings"]["minValue"] = 0
    flame_cfg["settings"]["maxValue"] = 1
    flame_cfg["settings"]["levelColors"] = ["#4caf50", "#f44336"]
    flame_cfg["datasources"] = [
        {
            "type": "entity",
            "entityAliasId": alias_id,
            "dataKeys": [
                {
                    "name": "flame",
                    "type": "timeseries",
                    "label": "Flame Active",
                    "color": "#ff9800",
                    "settings": {},
                    "_hash": 0.22
                }
            ]
        }
    ]

    # --- 3. Timeseries Chart (Environmental History) ---
    chart_cfg = copy.deepcopy(templates.get("time_series_chart", {}))
    chart_cfg["title"] = "Environmental Telemetry History"
    chart_cfg["showTitle"] = True
    chart_cfg["useDashboardTimewindow"] = False
    chart_cfg["displayTimewindow"] = True
    chart_cfg["timewindow"] = {
        "realtime": {
            "timewindowMs": 300000,
            "interval": 1000
        }
    }
    
    # Template datakey settings for line chart
    base_key_settings = {
        "yAxisId": "default",
        "showInLegend": True,
        "dataHiddenByDefault": False,
        "type": "line",
        "lineSettings": {
            "showLine": True,
            "step": False,
            "smooth": True,
            "lineType": "solid",
            "lineWidth": 2.5
        }
    }

    chart_cfg["datasources"] = [
        {
            "type": "entity",
            "entityAliasId": alias_id,
            "dataKeys": [
                {
                    "name": "smoke",
                    "type": "timeseries",
                    "label": "MQ-2 ADC",
                    "color": "#f44336",
                    "settings": copy.deepcopy(base_key_settings),
                    "_hash": 0.31
                },
                {
                    "name": "temperature",
                    "type": "timeseries",
                    "label": "Temperature (C)",
                    "color": "#2196f3",
                    "settings": copy.deepcopy(base_key_settings),
                    "_hash": 0.32
                },
                {
                    "name": "flame",
                    "type": "timeseries",
                    "label": "Flame Status",
                    "color": "#ff9800",
                    "settings": copy.deepcopy(base_key_settings),
                    "_hash": 0.33
                },
                {
                    "name": "anomaly_score",
                    "type": "timeseries",
                    "label": "Anomaly Score",
                    "color": "#9c27b0",
                    "settings": copy.deepcopy(base_key_settings),
                    "_hash": 0.34
                }
            ]
        }
    ]

    # --- 4. Isolation Forest Anomaly Status ---
    anom_status_cfg = copy.deepcopy(templates.get("digital_gauge", {}))
    anom_status_cfg["title"] = "AI Anomaly Status"
    anom_status_cfg["showTitle"] = True
    anom_status_cfg["units"] = ""
    anom_status_cfg.setdefault("settings", {})
    anom_status_cfg["settings"]["minValue"] = 0
    anom_status_cfg["settings"]["maxValue"] = 1
    anom_status_cfg["settings"]["levelColors"] = ["#4caf50", "#f44336"]
    anom_status_cfg["datasources"] = [
        {
            "type": "entity",
            "entityAliasId": alias_id,
            "dataKeys": [
                {
                    "name": "is_anomaly",
                    "type": "timeseries",
                    "label": "Anomaly Flag",
                    "color": "#e91e63",
                    "settings": {},
                    "_hash": 0.41
                }
            ]
        }
    ]

    # --- 5. Isolation Forest Anomaly Score ---
    anom_score_cfg = copy.deepcopy(templates.get("digital_gauge", {}))
    anom_score_cfg["title"] = "Isolation Forest Anomaly Score"
    anom_score_cfg["showTitle"] = True
    anom_score_cfg["units"] = ""
    anom_score_cfg["decimals"] = 2
    anom_score_cfg.setdefault("settings", {})
    anom_score_cfg["settings"]["minValue"] = 0.0
    anom_score_cfg["settings"]["maxValue"] = 1.0
    anom_score_cfg["settings"]["decimals"] = 2
    anom_score_cfg["settings"]["levelColors"] = ["#4caf50", "#ff9800", "#f44336"]
    anom_score_cfg["datasources"] = [
        {
            "type": "entity",
            "entityAliasId": alias_id,
            "dataKeys": [
                {
                    "name": "anomaly_score",
                    "type": "timeseries",
                    "label": "Anomaly Score",
                    "color": "#9c27b0",
                    "settings": {},
                    "_hash": 0.42
                }
            ]
        }
    ]

    # --- 6. Fire Door Servo Switch ---
    servo_cfg = copy.deepcopy(templates.get("round_switch", {}))
    servo_cfg["title"] = "Master Alarm Override (ON=Force, OFF=Auto)"
    servo_cfg["showTitle"] = True
    servo_cfg["targetDeviceAliasIds"] = [alias_id]
    servo_cfg.setdefault("settings", {})
    servo_cfg["settings"]["requestTimeout"] = 1000
    servo_cfg["settings"]["initialValue"] = False
    servo_cfg["settings"]["getValueMethod"] = "getAlarmOverride"
    servo_cfg["settings"]["setValueMethod"] = "setAlarmOverride"
    servo_cfg["settings"]["valueKey"] = "alarm_override"
    servo_cfg["settings"]["parseValueFunction"] = "return data && (data.alarm_override === true || data.alarm_override === 1);"
    servo_cfg["settings"]["convertValueFunction"] = "return value ? true : false;"

    # --- 7. Alarm Buzzer Switch ---
    buzzer_cfg = copy.deepcopy(templates.get("switch_control", {}))
    buzzer_cfg["title"] = "Alarm Siren Buzzer"
    buzzer_cfg["showTitle"] = True
    buzzer_cfg["targetDeviceAliasIds"] = [alias_id]
    buzzer_cfg.setdefault("settings", {})
    buzzer_cfg["settings"]["requestTimeout"] = 1000
    buzzer_cfg["settings"]["initialValue"] = False
    buzzer_cfg["settings"]["getValueMethod"] = "getBuzzer"
    buzzer_cfg["settings"]["setValueMethod"] = "manualSetBuzzer"
    buzzer_cfg["settings"]["valueKey"] = "buzzer"
    buzzer_cfg["settings"]["parseValueFunction"] = "return data && (data.buzzer === true || data.buzzer === 1);"
    buzzer_cfg["settings"]["convertValueFunction"] = "return value ? 1 : 0;"

    # --- 8. Strobe LED Switch ---
    led_cfg = copy.deepcopy(templates.get("switch_control", {}))
    led_cfg["title"] = "Strobe LED Beacon"
    led_cfg["showTitle"] = True
    led_cfg["targetDeviceAliasIds"] = [alias_id]
    led_cfg.setdefault("settings", {})
    led_cfg["settings"]["requestTimeout"] = 1000
    led_cfg["settings"]["initialValue"] = False
    led_cfg["settings"]["getValueMethod"] = "getLed"
    led_cfg["settings"]["setValueMethod"] = "manualSetLed"
    led_cfg["settings"]["valueKey"] = "led"
    led_cfg["settings"]["parseValueFunction"] = "return data && (data.led === true || data.led === 1);"
    led_cfg["settings"]["convertValueFunction"] = "return value ? 1 : 0;"

    # --- 9. Ambient Temperature Value Card ---
    temp_cfg = copy.deepcopy(templates.get("value_card", {}))
    temp_cfg["title"] = "Ambient Temperature"
    temp_cfg["showTitle"] = True
    temp_cfg["units"] = "°C"
    temp_cfg["decimals"] = 1
    temp_cfg.setdefault("settings", {})
    temp_cfg["settings"]["showIcon"] = True
    temp_cfg["settings"]["icon"] = "thermostat"
    temp_cfg["settings"]["layout"] = "square"
    temp_cfg["settings"]["showLabel"] = True
    temp_cfg["settings"]["labelPosition"] = "top"
    temp_cfg["datasources"] = [
        {
            "type": "entity",
            "entityAliasId": alias_id,
            "dataKeys": [
                {
                    "name": "temperature",
                    "type": "timeseries",
                    "label": "Temperature",
                    "color": "#2196f3",
                    "settings": {},
                    "_hash": 0.51
                }
            ]
        }
    ]

    # Widgets definition
    widgets = {
        id_smoke_gauge: {
            "id": id_smoke_gauge,
            "type": "latest",
            "typeFullFqn": "system.analogue_gauges.radial_gauge_canvas_gauges",
            "sizeX": 5,
            "sizeY": 6,
            "row": 0,
            "col": 0,
            "config": smoke_cfg
        },
        id_flame_status: {
            "id": id_flame_status,
            "type": "latest",
            "typeFullFqn": "system.digital_gauges.simple_gauge_justgage",
            "sizeX": 5,
            "sizeY": 6,
            "row": 0,
            "col": 5,
            "config": flame_cfg
        },
        id_temp_card: {
            "id": id_temp_card,
            "type": "latest",
            "typeFullFqn": "system.cards.value_card",
            "sizeX": 4,
            "sizeY": 6,
            "row": 0,
            "col": 10,
            "config": temp_cfg
        },
        id_anom_status: {
            "id": id_anom_status,
            "type": "latest",
            "typeFullFqn": "system.digital_gauges.simple_gauge_justgage",
            "sizeX": 5,
            "sizeY": 6,
            "row": 0,
            "col": 14,
            "config": anom_status_cfg
        },
        id_anom_score: {
            "id": id_anom_score,
            "type": "latest",
            "typeFullFqn": "system.digital_gauges.simple_gauge_justgage",
            "sizeX": 5,
            "sizeY": 6,
            "row": 0,
            "col": 19,
            "config": anom_score_cfg
        },
        id_chart: {
            "id": id_chart,
            "type": "timeseries",
            "typeFullFqn": "system.time_series_chart",
            "sizeX": 15,
            "sizeY": 7,
            "row": 6,
            "col": 0,
            "config": chart_cfg
        },
        id_servo: {
            "id": id_servo,
            "type": "rpc",
            "typeFullFqn": "system.control_widgets.round_switch",
            "sizeX": 3,
            "sizeY": 7,
            "row": 6,
            "col": 15,
            "config": servo_cfg
        },
        id_buzzer: {
            "id": id_buzzer,
            "type": "rpc",
            "typeFullFqn": "system.control_widgets.switch_control",
            "sizeX": 3,
            "sizeY": 7,
            "row": 6,
            "col": 18,
            "config": buzzer_cfg
        },
        id_led: {
            "id": id_led,
            "type": "rpc",
            "typeFullFqn": "system.control_widgets.switch_control",
            "sizeX": 3,
            "sizeY": 7,
            "row": 6,
            "col": 21,
            "config": led_cfg
        }
    }

    # Layout mapping inside states.default.layouts.main
    layout_widgets = {
        wid: {
            "sizeX": w["sizeX"],
            "sizeY": w["sizeY"],
            "row": w["row"],
            "col": w["col"]
        }
        for wid, w in widgets.items()
    }

    return {
        "title": DASHBOARD_TITLE,
        "configuration": {
            "description": "Industrial Fire Alarm Telemetry and Remote Actuator Control Dashboard",
            "widgets": widgets,
            "states": {
                "default": {
                    "name": DASHBOARD_TITLE,
                    "root": True,
                    "layouts": {
                        "main": {
                            "widgets": layout_widgets,
                            "gridSettings": {
                                "columns": 24,
                                "margins": [10, 10],
                                "backgroundColor": "#f4f6f8"
                            }
                        }
                    }
                }
            },
            "entityAliases": {
                alias_id: {
                    "id": alias_id,
                    "alias": "FireAlarm_Gateway",
                    "filter": {
                        "type": "singleEntity",
                        "singleEntity": {
                            "entityType": "DEVICE",
                            "id": device_id
                        },
                        "resolveMultiple": False
                    }
                }
            },
            "timewindow": {
                "realtime": {
                    "timewindowMs": 300000,
                    "interval": 1000
                }
            },
            "settings": {
                "stateControllerId": "entity",
                "showTitle": True,
                "showDashboardsSelect": True,
                "showEntitiesSelect": False,
                "showDashboardTimewindow": True
            }
        }
    }


def provision_and_export_dashboard(token: str, device_id: str, templates: dict) -> str:
    """Creates or updates the ThingsBoard dashboard and exports JSON to disk."""
    dashboard_data = generate_dashboard_json(device_id, templates)
    
    # Save local JSON file
    logger.info(f"Writing dashboard definition to '{DASHBOARD_FILE}'...")
    DASHBOARD_FILE.write_text(json.dumps(dashboard_data, indent=2), encoding="utf-8")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Search for existing dashboard with pagination params
    search_url = f"{TB_HOST}/api/tenant/dashboards?pageSize=10&page=0&textSearch={requests.utils.quote(DASHBOARD_TITLE)}"
    res = requests.get(search_url, headers=headers, timeout=10)
    res.raise_for_status()
    
    data = res.json().get("data", [])
    tb_payload = {
        "title": dashboard_data["title"],
        "configuration": dashboard_data["configuration"]
    }

    if data:
        dashboard_id = data[0]["id"]["id"]
        tb_payload["id"] = {"id": dashboard_id, "entityType": "DASHBOARD"}
        logger.info(f"Updating existing dashboard ID: {dashboard_id}...")
        update_res = requests.post(f"{TB_HOST}/api/dashboard", json=tb_payload, headers=headers, timeout=10)
        update_res.raise_for_status()
        logger.info("Dashboard updated successfully.")
    else:
        logger.info("Creating new dashboard in ThingsBoard...")
        create_res = requests.post(f"{TB_HOST}/api/dashboard", json=tb_payload, headers=headers, timeout=10)
        create_res.raise_for_status()
        dashboard_id = create_res.json()["id"]["id"]
        logger.info(f"Dashboard created successfully with ID: {dashboard_id}")

    return dashboard_id


def main():
    logger.info("Starting ThingsBoard Dashboard Setup Script...")
    wait_for_thingsboard()
    
    try:
        token = get_auth_token()
        device_id = get_or_create_device(token)
        templates = fetch_system_widget_templates(token)
        dashboard_id = provision_and_export_dashboard(token, device_id, templates)
        
        dashboard_url = f"{TB_HOST}/dashboards/{dashboard_id}"
        logger.info("==================================================================")
        logger.info("SUCCESS: Industrial Fire Alarm Dashboard provisioned successfully!")
        logger.info(f"ThingsBoard Web UI:  {TB_HOST}")
        logger.info(f"Direct Dashboard URL: {dashboard_url}")
        logger.info(f"Device Name:          {DEVICE_NAME} (ID: {device_id})")
        logger.info(f"Device Access Token:  {DEVICE_TOKEN}")
        logger.info(f"Exported JSON File:   {DASHBOARD_FILE}")
        logger.info("==================================================================")
    except Exception as e:
        logger.error(f"Setup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
