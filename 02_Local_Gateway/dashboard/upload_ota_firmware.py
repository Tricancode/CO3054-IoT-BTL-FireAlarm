#!/usr/bin/env python3
"""
upload_ota_firmware.py
======================
Automated OTA Firmware Upload and Assignment Tool for CoreIOT / ThingsBoard.
Complies with HCMUT IoT Course Criterion T14 (Firmware OTA Update).

Workflow:
1. Authenticates with ThingsBoard / CoreIOT REST API.
2. Locates the device 'FireAlarm_Gateway' and its Device Profile.
3. Creates or updates an OTA Package (Type: FIRMWARE).
4. Uploads 'firmware.bin' with SHA256 checksum verification.
5. Assigns the firmware package to the device 'FireAlarm_Gateway'.
6. ThingsBoard pushes shared attributes over MQTT, triggering the device update.

Strictly English logs and comments. Zero emojis.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("TB_OTA_Uploader")

# Defaults matching project architecture
DEFAULT_HOST = os.getenv("TB_REST_HOST", "http://localhost:9090").rstrip("/")
DEFAULT_USER = os.getenv("TB_REST_USER", "tenant@thingsboard.org")
DEFAULT_PASS = os.getenv("TB_REST_PASS", "tenant")
DEFAULT_DEVICE_NAME = os.getenv("TB_DEVICE_NAME", "FireAlarm_Gateway")
DEFAULT_TITLE = "yolo_firmware"
DEFAULT_VERSION = "1.0.1"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_BIN_PATH = PROJECT_ROOT / "01_Firmware_EndNode" / ".pio" / "build" / "yolo_uno" / "firmware.bin"


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def authenticate(host: str, username: str, password: str) -> str:
    """Authenticate with ThingsBoard REST API and return Bearer token."""
    login_url = f"{host}/api/auth/login"
    logger.info("Authenticating with ThingsBoard REST API at %s as %s...", host, username)
    res = requests.post(login_url, json={"username": username, "password": password}, timeout=15)
    if res.status_code != 200:
        logger.error("Authentication failed (HTTP %d): %s", res.status_code, res.text)
        sys.exit(1)
    return res.json()["token"]


def get_device_info(host: str, token: str, device_name: str) -> dict:
    """Retrieve device entity and deviceProfileId."""
    headers = {"X-Authorization": f"Bearer {token}"}
    url = f"{host}/api/tenant/devices?deviceName={device_name}"
    res = requests.get(url, headers=headers, timeout=15)
    if res.status_code != 200:
        logger.error("Failed to find device '%s' (HTTP %d): %s", device_name, res.status_code, res.text)
        sys.exit(1)
    dev = res.json()
    logger.info("Located device '%s' (ID: %s, Profile ID: %s)",
                device_name, dev["id"]["id"], dev.get("deviceProfileId", {}).get("id"))
    return dev


def find_or_create_ota_package(host: str, token: str, title: str, version: str, profile_id: dict, device: dict) -> str:
    """Check if an OTA package exists; if it has data, delete to replace, then create fresh."""
    headers = {"X-Authorization": f"Bearer {token}"}
    
    # Query existing packages
    list_url = f"{host}/api/otaPackages?pageSize=50&page=0&sortProperty=createdTime&sortOrder=DESC"
    res = requests.get(list_url, headers=headers, timeout=15)
    if res.status_code == 200:
        for pkg in res.json().get("data", []):
            if pkg.get("title") == title and pkg.get("version") == version:
                pkg_id = pkg["id"]["id"]
                logger.info("Found existing OTA package '%s' v%s (ID: %s).", title, version, pkg_id)
                if (device.get("firmwareId") or {}).get("id") == pkg_id:
                    logger.info("Temporarily unassigning firmware from device '%s' to allow clean recreation...", device.get("name"))
                    dev_unassign = dict(device)
                    dev_unassign["firmwareId"] = None
                    requests.post(f"{host}/api/device", headers=headers, json=dev_unassign, timeout=15)
                del_res = requests.delete(f"{host}/api/otaPackage/{pkg_id}", headers=headers, timeout=15)
                if del_res.status_code in (200, 204):
                    logger.info("Deleted old package '%s' v%s cleanly.", title, version)
                else:
                    logger.warning("Could not delete package (HTTP %d). Reusing existing ID...", del_res.status_code)
                    return pkg_id
                break

    # Create new OTA package
    create_url = f"{host}/api/otaPackage"
    payload = {
        "type": "FIRMWARE",
        "title": title,
        "version": version,
        "deviceProfileId": profile_id
    }
    logger.info("Creating new OTA Package: title='%s', version='%s'...", title, version)
    res = requests.post(create_url, headers=headers, json=payload, timeout=15)
    if res.status_code != 200:
        logger.error("Failed to create OTA package (HTTP %d): %s", res.status_code, res.text)
        sys.exit(1)
    pkg_id = res.json()["id"]["id"]
    logger.info("Created OTA Package successfully (ID: %s)", pkg_id)
    return pkg_id


def upload_firmware_binary(host: str, token: str, pkg_id: str, bin_file: Path) -> dict:
    """Upload firmware binary stream to the OTA Package."""
    headers = {"X-Authorization": f"Bearer {token}"}
    url = f"{host}/api/otaPackage/{pkg_id}"
    file_size = bin_file.stat().st_size
    sha256_hash = compute_sha256(bin_file)
    logger.info("Uploading '%s' (%d bytes, SHA256: %s)...", bin_file.name, file_size, sha256_hash)

    with open(bin_file, "rb") as f:
        files = {"file": (bin_file.name, f, "application/octet-stream")}
        params = {"checksumAlgorithm": "SHA256"}
        res = requests.post(url, headers=headers, params=params, files=files, timeout=60)

    if res.status_code != 200:
        logger.error("Failed to upload binary (HTTP %d): %s", res.status_code, res.text)
        sys.exit(1)

    data = res.json()
    logger.info("Binary upload complete: hasData=%s, Checksum=%s", data.get("hasData"), data.get("checksum"))
    return data


def assign_firmware_to_device(host: str, token: str, device: dict, pkg_id: str):
    """Assign OTA Package to the device entity."""
    headers = {"X-Authorization": f"Bearer {token}"}
    device["firmwareId"] = {"entityType": "OTA_PACKAGE", "id": pkg_id}
    url = f"{host}/api/device"
    logger.info("Assigning firmware package to device '%s'...", device["name"])
    res = requests.post(url, headers=headers, json=device, timeout=15)
    if res.status_code != 200:
        logger.error("Failed to assign firmware to device (HTTP %d): %s", res.status_code, res.text)
        sys.exit(1)
    logger.info("Firmware package successfully assigned to device '%s'!", device["name"])


def main():
    parser = argparse.ArgumentParser(description="Upload and assign OTA Firmware to CoreIOT / ThingsBoard")
    parser.add_argument("--host", default=DEFAULT_HOST, help="ThingsBoard REST host (default: http://localhost:9090)")
    parser.add_argument("--user", default=DEFAULT_USER, help="REST username (default: tenant@thingsboard.org)")
    parser.add_argument("--password", default=DEFAULT_PASS, help="REST password")
    parser.add_argument("--device", default=DEFAULT_DEVICE_NAME, help="Device name (default: FireAlarm_Gateway)")
    parser.add_argument("--title", default=DEFAULT_TITLE, help="Firmware package title (default: yolo_firmware)")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="Firmware version (default: 1.0.1)")
    parser.add_argument("--file", default=str(DEFAULT_BIN_PATH), help="Path to firmware.bin")

    args = parser.parse_args()
    bin_path = Path(args.file)

    if not bin_path.exists():
        logger.error("Firmware file not found at: %s", bin_path)
        logger.error("Please build the firmware first via: pio run -d 01_Firmware_EndNode")
        sys.exit(1)

    print("=" * 65)
    print("   CoreIOT / ThingsBoard OTA Firmware Provisioner")
    print(f" -> Host    : {args.host}")
    print(f" -> Device  : {args.device}")
    print(f" -> Firmware: {args.title} v{args.version}")
    print(f" -> File    : {bin_path} ({bin_path.stat().st_size} bytes)")
    print("=" * 65)

    jwt_token = authenticate(args.host, args.user, args.password)
    device = get_device_info(args.host, jwt_token, args.device)
    profile_id = device.get("deviceProfileId")
    pkg_id = find_or_create_ota_package(args.host, jwt_token, args.title, args.version, profile_id, device)
    upload_firmware_binary(args.host, jwt_token, pkg_id, bin_path)
    
    # Re-fetch latest device object to avoid HTTP 409 optimistic locking conflicts
    device = get_device_info(args.host, jwt_token, args.device)
    assign_firmware_to_device(args.host, jwt_token, device, pkg_id)

    print("\n" + "=" * 65)
    print("OTA Firmware Package Successfully Deployed to CoreIOT Cloud!")
    print(f"Web UI Verification Link: {args.host}/#/otaUpdates")
    print(f"Device Details Link    : {args.host}/#/devices/{device['id']['id']}")
    print("ThingsBoard is now broadcasting OTA shared attributes over MQTT.")
    print("The LocalGateway and ESP32-S3 will download and apply the update.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
