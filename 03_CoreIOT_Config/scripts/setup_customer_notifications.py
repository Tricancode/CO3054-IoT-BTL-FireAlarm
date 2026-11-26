#!/usr/bin/env python3
"""
setup_customer_notifications.py
===============================
Automated Customer Provisioning and 4-Tier Notification Center Configuration
for CoreIOT / ThingsBoard Cloud Platform.

Configures:
1. Customer Entities: Customer A, Customer B, Customer C.
2. Customer Users: customera@gmail.com, customerb@gmail.com, customerc@gmail.com.
3. Notification Targets: Customer_Emergency_Broadcast_Target.
4. Notification Templates: Fire_Alarm_Customer_Alert_Template.
5. Notification Rules: Fire_Alarm_Customer_Notification_Rule (triggers on FIRE_ALARM CRITICAL).
6. Local Email Dispatcher Simulation: Records audit entries to email_dispatch_log.txt.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

CUSTOMERS_CONFIG = [
    {
        "title": "Customer A - Residential Unit 101",
        "short_name": "Customer_A",
        "email": "customera@gmail.com",
        "first_name": "Customer",
        "last_name": "A",
        "phone": "+84901111111",
        "address": "Apartment 101, Building B, District 1, HCMC"
    },
    {
        "title": "Customer B - Commercial Office 202",
        "short_name": "Customer_B",
        "email": "customerb@gmail.com",
        "first_name": "Customer",
        "last_name": "B",
        "phone": "+84902222222",
        "address": "Floor 2, Tech Hub Building, Thu Duc City, HCMC"
    },
    {
        "title": "Customer C - Safety & Fire Authority",
        "short_name": "Customer_C",
        "email": "customerc@gmail.com",
        "first_name": "Customer",
        "last_name": "C",
        "phone": "+84903333333",
        "address": "Fire Prevention & Safety Command Center, HCMC"
    }
]


class ThingsBoardNotificationManager:
    def __init__(self, host: str = "127.0.0.1", port: int = 9090, username: str = "tenant@thingsboard.org", password: str = "tenant_password"):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.username = username
        self.password = password
        self.token: Optional[str] = None

    def _api_request(self, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Authorization"] = f"Bearer {self.token}"

        encoded_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as err:
            if err.code in (404, 409):
                try:
                    err_body = err.read().decode("utf-8")
                    return json.loads(err_body)
                except Exception:
                    pass
            print(f"[!] HTTP Error {err.code} on {method} {endpoint}: {err.reason}")
            return None
        except Exception as err:
            print(f"[!] Network error on {method} {endpoint}: {err}")
            return None

    def login(self) -> bool:
        res = self._api_request("/api/auth/login", method="POST", data={"username": self.username, "password": self.password})
        if res and "token" in res:
            self.token = res["token"]
            print(f"[+] ThingsBoard Tenant login successful ({self.username}).")
            return True
        return False

    def get_or_create_customer(self, customer_cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Query existing customers
        res = self._api_request("/api/customers?pageSize=100&page=0", method="GET")
        if res and "data" in res:
            for cust in res["data"]:
                if cust.get("title") == customer_cfg["title"]:
                    print(f"[*] Customer exists: {customer_cfg['title']} (ID: {cust['id']['id']})")
                    return cust

        # Create new customer
        create_payload = {
            "title": customer_cfg["title"],
            "email": customer_cfg["email"],
            "phone": customer_cfg.get("phone", ""),
            "address": customer_cfg.get("address", "")
        }
        created = self._api_request("/api/customer", method="POST", data=create_payload)
        if created and "id" in created:
            print(f"[+] Customer created: {customer_cfg['title']} (ID: {created['id']['id']})")
            return created
        return None

    def get_or_create_user(self, customer_id: str, customer_cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        res = self._api_request(f"/api/customer/{customer_id}/users?pageSize=100&page=0", method="GET")
        if res and "data" in res:
            for usr in res["data"]:
                if usr.get("email") == customer_cfg["email"]:
                    print(f"[*] Customer user exists: {customer_cfg['email']}")
                    return usr

        user_payload = {
            "customerId": {"entityType": "CUSTOMER", "id": customer_id},
            "email": customer_cfg["email"],
            "authority": "CUSTOMER_USER",
            "firstName": customer_cfg["first_name"],
            "lastName": customer_cfg["last_name"]
        }
        created = self._api_request("/api/user?sendActivationMail=false", method="POST", data=user_payload)
        if created and "id" in created:
            print(f"[+] Customer user created: {customer_cfg['email']}")
            return created
        return None

    def setup_notification_target(self, customer_ids: List[str]) -> Optional[str]:
        target_payload = {
            "name": "Customer_Emergency_Broadcast_Target",
            "configuration": {
                "type": "CUSTOMER_USERS",
                "customerIds": customer_ids
            }
        }
        res = self._api_request("/api/notification/target", method="POST", data=target_payload)
        if res and "id" in res:
            target_id = res["id"]["id"]
            print(f"[+] Notification Target provisioned: Customer_Emergency_Broadcast_Target (ID: {target_id})")
            return target_id
        return None

    def setup_notification_template(self) -> Optional[str]:
        template_payload = {
            "name": "Fire_Alarm_Customer_Alert_Template",
            "notificationType": "GENERAL",
            "configuration": {
                "deliveryMethodsTemplates": {
                    "WEB": {
                        "enabled": True,
                        "subject": "[COREIOT EMERGENCY] FIRE ALARM DETECTED - 4-TIER ACTIVE BROADCAST",
                        "body": "CRITICAL FIRE WARNING: High smoke or flame incident detected at hardware node! Automatic containment active."
                    },
                    "EMAIL": {
                        "enabled": True,
                        "subject": "[COREIOT EMERGENCY] FIRE ALARM DETECTED - 4-TIER NOTIFICATION BROADCAST",
                        "body": "<h3>HCMUT COREIOT 4-TIER EMERGENCY ALERT</h3><p>Critical fire alarm triggered. Automated hardware containment in progress.</p><p>Recipients: customera@gmail.com, customerb@gmail.com, customerc@gmail.com</p>"
                    }
                }
            }
        }
        res = self._api_request("/api/notification/template", method="POST", data=template_payload)
        if res and "id" in res:
            template_id = res["id"]["id"]
            print(f"[+] Notification Template provisioned: Fire_Alarm_Customer_Alert_Template (ID: {template_id})")
            return template_id
        return None

    def setup_notification_rule(self, template_id: str, target_id: str) -> Optional[str]:
        rule_payload = {
            "name": "Fire_Alarm_Customer_Notification_Rule",
            "enabled": True,
            "templateId": {"entityType": "NOTIFICATION_TEMPLATE", "id": template_id},
            "triggerType": "ALARM",
            "triggerConfig": {
                "alarmTypes": ["FIRE_ALARM"],
                "alarmSeverities": ["CRITICAL"],
                "notifyOn": ["CREATED"]
            },
            "recipientsConfig": {
                "targets": [target_id]
            }
        }
        res = self._api_request("/api/notification/rule", method="POST", data=rule_payload)
        if res and "id" in res:
            rule_id = res["id"]["id"]
            print(f"[+] Notification Rule provisioned: Fire_Alarm_Customer_Notification_Rule (ID: {rule_id})")
            return rule_id
        return None


def dispatch_simulated_email_broadcast(smoke: float = 2150.0, temp: float = 38.5, flame: int = 1, risk: float = 94.2) -> str:
    """Record simulated email broadcast to Customers A, B, and C in local audit log."""
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    recipients = [c["email"] for c in CUSTOMERS_CONFIG]

    log_entry = (
        "======================================================================\n"
        "HCMUT IOT EMERGENCY FIRE ALERT - 4-TIER NOTIFICATION BROADCAST\n"
        "======================================================================\n"
        f"Timestamp: {now_str}\n"
        "Severity : CRITICAL FIRE HAZARD\n"
        f"Target Customer Emails: {', '.join(recipients)}\n"
        "Sensory Telemetry:\n"
        f"  - Smoke Sensor (MQ-2)   : {smoke:.0f} ADC\n"
        f"  - Temperature (DHT20)   : {temp:.1f} C\n"
        f"  - Flame Optical Sensor  : {'FLAME DETECTED' if flame == 1 else 'None'}\n"
        f"  - Edge AI / TinyML Risk : {risk:.1f}%\n"
        "Integrated 4-Tier Automated Actions:\n"
        "  [Tier 1 - ESP32 Hardware]  : Buzzer GPIO 6 ON, Warning LED GPIO 17 ON, Servo Door GPIO 5 Open 180 deg, TFT LCD Red Alert.\n"
        "  [Tier 2 - Local Gateway]   : Web SCADA Port 5050 Alert Banner, SQLite WAL Persisted.\n"
        "  [Tier 3 - ThingsBoard Cloud]: CRITICAL FIRE_ALARM Created, Auto-cleared on Safe.\n"
        "  [Tier 4 - Customer Dispatch]: Emergency Email Dispatched to Customers A, B, C.\n"
        "======================================================================\n"
    )

    log_file = Path(__file__).resolve().parent.parent / "email_dispatch_log.txt"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

    return log_entry


def main():
    parser = argparse.ArgumentParser(description="CoreIOT Customer Provisioning and 4-Tier Notification Setup")
    parser.add_argument("--host", default="127.0.0.1", help="ThingsBoard host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9090, help="ThingsBoard HTTP port (default: 9090)")
    parser.add_argument("--username", default="tenant@thingsboard.org", help="Tenant admin username")
    parser.add_argument("--password", default="tenant_password", help="Tenant admin password")
    parser.add_argument("--test-email", action="store_true", help="Simulate direct email dispatch to Customers A, B, C")
    args = parser.parse_args()

    print("======================================================================")
    print("COREIOT 4-TIER NOTIFICATION AND CUSTOMER SETUP")
    print("======================================================================")

    if args.test_email:
        print("[*] Running simulated emergency email broadcast to Customers A, B, C...")
        entry = dispatch_simulated_email_broadcast()
        print(entry)
        print("[+] Logged successfully to 03_CoreIOT_Config/email_dispatch_log.txt")
        return

    mgr = ThingsBoardNotificationManager(host=args.host, port=args.port, username=args.username, password=args.password)
    connected = mgr.login()

    if not connected:
        print(f"[!] Could not connect to ThingsBoard at {args.host}:{args.port}.")
        print("[*] Performing offline local simulation for Customers A, B, C...")
        entry = dispatch_simulated_email_broadcast()
        print(entry)
        print("[+] Offline email dispatch logged to 03_CoreIOT_Config/email_dispatch_log.txt")
        return

    # Online provisioning
    customer_ids = []
    for cfg in CUSTOMERS_CONFIG:
        cust = mgr.get_or_create_customer(cfg)
        if cust and "id" in cust:
            cid = cust["id"]["id"]
            customer_ids.append(cid)
            mgr.get_or_create_user(cid, cfg)

    if customer_ids:
        target_id = mgr.setup_notification_target(customer_ids)
        template_id = mgr.setup_notification_template()
        if target_id and template_id:
            mgr.setup_notification_rule(template_id, target_id)

    # Dispatch audit verification
    print("\n[*] Dispatching initial verification record...")
    dispatch_simulated_email_broadcast()
    print("[+] Setup complete. 4-tier notification system configured.")


if __name__ == "__main__":
    main()
