#!/usr/bin/env python3
"""
run_system.py
=============
MASTER SYSTEM RUNNER - HCMUT IOT FIRE ALARM SYSTEM (T08, T10, T12, T13).
Executes the complete physical IoT fire alarm system from the repository root:
1. Auto-detects ESP32-S3 YoloUNO hardware on USB Serial COM port.
2. Auto-detects local ThingsBoard Docker stack (ports 1883/9090) or falls back to CoreIOT Cloud.
3. Automatically launches both production dashboards simultaneously in browser:
   - Dashboard 1: Local SCADA Web Monitor (http://localhost:5050)
   - Dashboard 2: ThingsBoard Industrial Dashboard (http://localhost:9090 or https://app.coreiot.io)
4. Supervises LocalGateway process with graceful Ctrl+C shutdown releasing COM port.
Strictly English logs, UI, and comments. Zero icons or emojis.
"""

import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import List, Optional

import serial.tools.list_ports

ROOT_DIR = Path(__file__).resolve().parent
GATEWAY_DIR = ROOT_DIR / "02_Local_Gateway"
HW_GATEWAY_SCRIPT = GATEWAY_DIR / "hardware_gateway" / "LocalGateway.py"

LOCAL_WEB_HOST = "127.0.0.1"
LOCAL_WEB_PORT = 5050
LOCAL_WEB_URL = f"http://localhost:{LOCAL_WEB_PORT}"

TB_LOCAL_HOST = "127.0.0.1"
TB_LOCAL_HTTP_PORT = 9090
TB_LOCAL_MQTT_PORT = 1883
TB_DEFAULT_LOCAL_URL = f"http://localhost:{TB_LOCAL_HTTP_PORT}"

STARTUP_TIMEOUT = 12.0

processes: List[subprocess.Popen] = []
is_shutting_down = False
shutdown_lock = threading.Lock()


def is_port_open(host: str, port: int) -> bool:
    """Check if TCP port is active and accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def is_local_thingsboard_active() -> bool:
    """Check if local ThingsBoard container is active on both HTTP (9090) and MQTT (1883)."""
    return is_port_open(TB_LOCAL_HOST, TB_LOCAL_HTTP_PORT) and is_port_open(TB_LOCAL_HOST, TB_LOCAL_MQTT_PORT)


def detect_usb_serial_ports() -> List[serial.tools.list_ports_common.ListPortInfo]:
    """Scan and return all available COM / ttyUSB serial devices."""
    return list(serial.tools.list_ports.comports())


def find_best_esp32_port() -> Optional[str]:
    """Scan and match ESP32/CH340/CP210x hardware signatures."""
    ports = detect_usb_serial_ports()
    for p in ports:
        desc = (p.description or "").upper()
        hwid = (p.hwid or "").upper()
        if any(k in desc or k in hwid for k in ["ESP32", "CH340", "CP210", "UART", "USB SERIAL", "303A"]):
            return p.device
    if ports:
        return ports[0].device
    return None


def open_browser_when_ready(host: str, port: int, url: str, label: str = "Web dashboard") -> None:
    """Polls TCP port and launches default browser upon readiness."""
    start_time = time.time()
    while time.time() - start_time < STARTUP_TIMEOUT:
        if is_shutting_down:
            return
        if is_port_open(host, port):
            print(f"[System Launcher] {label} is ready on port {port}. Opening: {url}")
            webbrowser.open(url)
            return
        time.sleep(0.3)
    print(f"[System Launcher Warning] {label} port {port} timed out after {STARTUP_TIMEOUT}s. Launch skipped.")


def launch_dashboards(no_browser: bool, no_tb_browser: bool, tb_url: str, tb_is_local: bool):
    """Spawns asynchronous browser launch routines for both dashboards."""
    if no_browser:
        return

    # 1. Local SCADA Web Monitor (Port 5050)
    threading.Thread(
        target=open_browser_when_ready,
        args=(LOCAL_WEB_HOST, LOCAL_WEB_PORT, LOCAL_WEB_URL, "Local SCADA Web Monitor (5050)"),
        daemon=True
    ).start()

    # 2. ThingsBoard Dashboard (Port 9090 or Cloud)
    if not no_tb_browser:
        if tb_is_local:
            threading.Thread(
                target=open_browser_when_ready,
                args=(TB_LOCAL_HOST, TB_LOCAL_HTTP_PORT, tb_url, "ThingsBoard Industrial Dashboard (9090)"),
                daemon=True
            ).start()
        else:
            def _open_remote_tb():
                time.sleep(1.2)
                if not is_shutting_down:
                    print(f"[System Launcher] Opening Remote ThingsBoard Dashboard: {tb_url}")
                    webbrowser.open(tb_url)
            threading.Thread(target=_open_remote_tb, daemon=True).start()


def shutdown_handler(signum=None, frame=None):
    """Gracefully terminates all child processes on Ctrl+C."""
    global is_shutting_down
    with shutdown_lock:
        if is_shutting_down:
            return
        is_shutting_down = True

    print("\n[System Launcher] Shutdown signal received. Stopping Hardware Gateway...")
    for proc in reversed(processes):
        if proc.poll() is None:
            try:
                print(f"[System Launcher] Terminating PID {proc.pid}...")
                proc.terminate()
            except Exception as e:
                print(f"[System Launcher Warning] Error terminating PID {proc.pid}: {e}")

    start_wait = time.time()
    while time.time() - start_wait < 3.0:
        if all(p.poll() is not None for p in processes):
            break
        time.sleep(0.1)

    for proc in processes:
        if proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    print("[System Launcher] Gateway shutdown complete. Serial COM port released cleanly.")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="HCMUT IoT Fire Alarm - Master System Runner")
    parser.add_argument(
        "--port",
        "-p",
        default=None,
        help="Serial COM port for ESP32-S3 (e.g. COM4 or /dev/ttyUSB0). Default: Auto-detect"
    )
    parser.add_argument(
        "--baud",
        "-b",
        type=int,
        default=115200,
        help="UART Baudrate (default: 115200)"
    )
    parser.add_argument(
        "--broker",
        default=None,
        help="MQTT Broker address (default: auto-detects localhost if local ThingsBoard is active, else app.coreiot.io)"
    )
    parser.add_argument(
        "--token",
        default="i2tchqq1390qcxhun4zr",
        help="Device Access Token (default: i2tchqq1390qcxhun4zr)"
    )
    parser.add_argument(
        "--tb-url",
        default=None,
        help="ThingsBoard Dashboard URL to open (default: auto-detected)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open any web browsers automatically."
    )
    parser.add_argument(
        "--no-tb-browser",
        action="store_true",
        help="Do not open ThingsBoard dashboard in browser."
    )
    args = parser.parse_args()

    # Register OS signal handlers for clean exit
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    print("=" * 70)
    print("HCMUT IOT FIRE ALARM SYSTEM - MASTER HARDWARE LAUNCHER")
    print("=" * 70)

    # 1. Serial Port Detection
    detected_port = args.port or find_best_esp32_port()
    ports_list = detect_usb_serial_ports()

    print("[Hardware Info] Scanning available USB Serial COM ports:")
    if ports_list:
        for p in ports_list:
            selected_marker = " <-- [SELECTED]" if p.device == detected_port else ""
            print(f"  * {p.device:<10} | {p.description} {selected_marker}")
    else:
        print("  * No active serial devices found! Please ensure ESP32-S3 USB cable is firmly plugged in.")

    target_port = detected_port or ("COM3" if sys.platform == "win32" else "/dev/ttyUSB0")
    print(f" -> Active UART Port  : {target_port} @ {args.baud} baud")

    # 2. Broker & ThingsBoard Resolution
    tb_local_active = is_local_thingsboard_active()
    if args.broker is not None:
        broker = args.broker
    elif tb_local_active:
        broker = "127.0.0.1"
        print("[Hardware Info] Local ThingsBoard Docker detected (1883/9090). Prioritizing broker: 127.0.0.1")
    else:
        broker = "app.coreiot.io"
        print("[Hardware Info] Local ThingsBoard not detected. Defaulting broker: app.coreiot.io")

    # 3. Resolve Dashboard URLs
    if args.tb_url:
        tb_url = args.tb_url
    elif broker in ("127.0.0.1", "localhost"):
        tb_url = TB_DEFAULT_LOCAL_URL
    else:
        tb_url = "https://app.coreiot.io"

    print(f" -> MQTT Cloud Broker : {broker}:1883 (Token: {args.token})")
    print(f" -> Local SCADA UI    : {LOCAL_WEB_URL}")
    print(f" -> ThingsBoard UI    : {tb_url}")
    print("=" * 70)

    # 4. Launch LocalGateway Process
    python_executable = sys.executable
    gw_cmd = [
        python_executable,
        str(HW_GATEWAY_SCRIPT),
        "--port", target_port,
        "--baud", str(args.baud),
        "--broker", broker,
        "--token", args.token
    ]

    print("[System Launcher] Launching Local Hardware Gateway subprocess...")
    gw_proc = subprocess.Popen(gw_cmd, cwd=str(GATEWAY_DIR))
    processes.append(gw_proc)

    # 5. Launch both Dashboards concurrently in browser
    launch_dashboards(
        no_browser=args.no_browser,
        no_tb_browser=args.no_tb_browser,
        tb_url=tb_url,
        tb_is_local=(broker in ("127.0.0.1", "localhost") and tb_local_active)
    )

    print("[System Launcher] System is fully operational.")
    print(" -> Real-time sensor logs will stream directly from ESP32-S3 UART below.")
    print(" -> Press Ctrl+C at any time to gracefully stop the Gateway and release the COM port.\n")

    # Supervisor Loop
    try:
        while True:
            exit_code = gw_proc.poll()
            if exit_code is not None:
                print(f"[System Launcher Warning] LocalGateway exited with returncode {exit_code}.")
                shutdown_handler()
            time.sleep(1.0)
    except KeyboardInterrupt:
        shutdown_handler()


if __name__ == "__main__":
    main()

