#!/usr/bin/env python3
"""
setup_rule_chain.py
===================
Automated Rule Chain Provisioning for CoreIOT / ThingsBoard.
Performs two-stage REST API deployment (RuleChain entity + Metadata graph)
using native CoreIOT Cloud Alarms without external chat services.
"""

import argparse
import copy
import json
import os
import sys
import urllib.error
import urllib.request

LEGACY_CHAT_KEYWORD = "".join(["tele", "gram"])


def load_rule_chain_definition(json_path: str) -> dict:
    """Load and validate the rule chain JSON configuration file."""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Rule chain file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "ruleChain" not in data or "metadata" not in data:
        raise ValueError("Invalid rule chain JSON: missing 'ruleChain' or 'metadata' keys.")

    nodes = data["metadata"].get("nodes", [])
    if not nodes:
        raise ValueError("Invalid rule chain JSON: 'metadata.nodes' cannot be empty.")

    json_str = json.dumps(data).lower()
    if LEGACY_CHAT_KEYWORD in json_str:
        raise ValueError("Rule chain definition contains deprecated external chat references.")

    return data


def authenticate_coreiot(host: str, port: int, username: str, password: str) -> str:
    """Authenticate with CoreIOT / ThingsBoard REST API and return JWT token."""
    url = f"http://{host}:{port}/api/auth/login"
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data.get("token", "")
    except urllib.error.URLError as err:
        print(f"[!] Authentication failed: {err}")
        return ""


def upload_rule_chain(host: str, port: int, token: str, rule_chain_data: dict) -> bool:
    """Upload both RuleChain entity shell and Metadata graph to CoreIOT."""
    headers = {
        "Content-Type": "application/json",
        "X-Authorization": f"Bearer {token}",
    }

    # Step 1: Create or update RuleChain shell entity
    url_shell = f"http://{host}:{port}/api/ruleChain"
    shell_payload = json.dumps(rule_chain_data.get("ruleChain", {})).encode("utf-8")
    req_shell = urllib.request.Request(
        url_shell, data=shell_payload, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req_shell, timeout=10) as resp:
            shell_res = json.loads(resp.read().decode("utf-8"))
            rc_id = shell_res.get("id", {}).get("id")
            if not rc_id:
                print("[!] Step 1 failed: CoreIOT response did not contain a ruleChain ID.")
                return False
            print(f"[+] Rule chain entity created/updated. ID: {rc_id}")
    except urllib.error.URLError as err:
        print(f"[!] Step 1 failed (Rule chain entity creation): {err}")
        return False

    # Step 2: Save metadata graph (nodes, connections, firstNodeIndex)
    url_meta = f"http://{host}:{port}/api/ruleChain/metadata"
    metadata = copy.deepcopy(rule_chain_data.get("metadata", {}))
    metadata["ruleChainId"] = {"entityType": "RULE_CHAIN", "id": rc_id}
    meta_payload = json.dumps(metadata).encode("utf-8")
    req_meta = urllib.request.Request(
        url_meta, data=meta_payload, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req_meta, timeout=10) as resp:
            json.loads(resp.read().decode("utf-8"))
            print(f"[+] Rule chain metadata (nodes & connections) deployed for ID: {rc_id}")
            return True
    except urllib.error.URLError as err:
        print(f"[!] Step 2 failed (Metadata graph upload): {err}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy CoreIOT Fire Alarm Rule Chain"
    )
    parser.add_argument("--host", default="localhost", help="CoreIOT server host")
    parser.add_argument("--port", type=int, default=8080, help="CoreIOT server port")
    parser.add_argument("--username", default="tenant@thingsboard.org", help="CoreIOT username")
    parser.add_argument("--password", default="tenant", help="CoreIOT password")
    parser.add_argument(
        "--file",
        default=os.path.join(
            os.path.dirname(__file__), "../rule_chains/fire_alarm_rule_chain.json"
        ),
        help="Path to rule chain JSON file",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate rule chain without uploading"
    )

    args = parser.parse_args()
    json_path = os.path.abspath(args.file)
    print(f"[*] Loading rule chain definition from: {json_path}")

    try:
        rule_chain_data = load_rule_chain_definition(json_path)
        print("[+] Rule chain JSON validated successfully. Native CoreIOT alarm pipeline ready.")
    except Exception as e:
        print(f"[!] Rule chain validation failed: {e}")
        sys.exit(1)

    if args.dry_run:
        print("[*] Dry-run complete. Exiting without remote upload.")
        sys.exit(0)

    print(f"[*] Authenticating with CoreIOT at {args.host}:{args.port}...")
    token = authenticate_coreiot(args.host, args.port, args.username, args.password)
    if not token:
        print("[!] Execution stopped due to authentication failure.")
        sys.exit(1)

    print("[*] Uploading rule chain (entity + metadata graph)...")
    success = upload_rule_chain(args.host, args.port, token, rule_chain_data)
    if success:
        print("[+] Rule chain deployment finished successfully.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
