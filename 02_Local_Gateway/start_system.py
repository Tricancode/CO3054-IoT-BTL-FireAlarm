"""
start_system.py
===============
All-in-One System Runner for Local IoT Gateway & End Node (T08, T10 - HCMUT).
Allows launching the entire ecosystem with a single command:
1. Spawns the Local Gateway process (Simulation or Hardware mode).
2. Waits for Web Dashboard port (5050) readiness.
3. Automatically opens the browser to http://localhost:5050.
4. Spawns the Simulation Node (in simulation mode).
5. Handles graceful cross-platform shutdown on Ctrl+C.
Strictly English. Zero icons or emojis.
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
from typing import List

BASE_DIR = Path(__file__).resolve().parent
SIM_GATEWAY_SCRIPT = BASE_DIR / "simulation" / "LocalGateway_Simulation.py"
HW_GATEWAY_SCRIPT = BASE_DIR / "hardware_gateway" / "LocalGateway.py"
NODE_SCRIPT = BASE_DIR / "simulation" / "SimulationNode.py"

WEB_HOST = "127.0.0.1"
WEB_PORT = 5050
DASHBOARD_URL = f"http://localhost:{WEB_PORT}"
STARTUP_TIMEOUT = 10.0

processes: List[subprocess.Popen] = []
is_shutting_down = False
shutdown_lock = threading.Lock()


def is_port_open(host: str, port: int) -> bool:
    """Check if TCP port is active and accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def open_browser_when_ready(host: str, port: int, url: str) -> None:
    """Polls Web UI port and launches default browser upon readiness."""
    start_time = time.time()
    while time.time() - start_time < STARTUP_TIMEOUT:
        if is_shutting_down:
            return
        if is_port_open(host, port):
            print(f"[Launcher] Web dashboard ready on port {port}. Opening browser: {url}")
            webbrowser.open(url)
            return
        time.sleep(0.3)
    print(f"[Launcher Warning] Dashboard port {port} timed out. Browser launch skipped.")


def shutdown_handler(signum=None, frame=None):
    """Gracefully terminates all child processes on Ctrl+C."""
    global is_shutting_down
    with shutdown_lock:
        if is_shutting_down:
            return
        is_shutting_down = True

    print("\n[Launcher] Shutdown signal received. Stopping all active processes...")
    for proc in reversed(processes):
        if proc.poll() is None:
            try:
                print(f"[Launcher] Terminating process PID {proc.pid}...")
                proc.terminate()
            except Exception as e:
                print(f"[Launcher Warning] Error terminating PID {proc.pid}: {e}")

    # Wait for processes to exit cleanly
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

    print("[Launcher] All processes stopped. Goodbye.")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="HCMUT Local IoT Gateway - All-in-One Launcher")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["sim", "hardware"],
        default="sim",
        help="Execution mode: 'sim' (Simulation Node + Gateway) or 'hardware' (UART Gateway). Default: sim"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open web browser automatically."
    )
    parser.add_argument(
        "--port",
        "-p",
        default=None,
        help="Serial COM port for hardware mode (e.g., COM3 or /dev/ttyUSB0)"
    )
    parser.add_argument(
        "--broker",
        default="app.coreiot.io",
        help="MQTT Broker address (e.g. app.coreiot.io or localhost for local ThingsBoard)"
    )
    parser.add_argument(
        "--token",
        default="i2tchqq1390qcxhun4zr",
        help="Device Access Token"
    )
    args = parser.parse_args()

    # Register OS signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    print("=" * 65)
    print("HCMUT IOT FIRE ALARM SYSTEM - UNIFIED LAUNCHER")
    print(f" -> Mode       : {args.mode.upper()}")
    print(f" -> Dashboard  : {DASHBOARD_URL}")
    print("=" * 65)

    python_executable = sys.executable

    if args.mode == "sim":
        # 1. Start Local Simulation Gateway
        print("[Launcher] Starting Local Gateway (Simulation)...")
        gw_cmd = [python_executable, str(SIM_GATEWAY_SCRIPT)]
        if args.broker != "app.coreiot.io":
            gw_cmd.extend(["--broker", args.broker])
        if args.token != "i2tchqq1390qcxhun4zr":
            gw_cmd.extend(["--token", args.token])
        gw_proc = subprocess.Popen(gw_cmd, cwd=str(BASE_DIR))
        processes.append(gw_proc)

        # 2. Start browser launch thread
        if not args.no_browser:
            threading.Thread(target=open_browser_when_ready, args=(WEB_HOST, WEB_PORT, DASHBOARD_URL), daemon=True).start()

        # 3. Wait 1.5 seconds for gateway initialization, then start Simulation Node
        time.sleep(1.5)
        print("[Launcher] Starting Virtual End Node (SimulationNode)...")
        node_proc = subprocess.Popen([python_executable, str(NODE_SCRIPT)], cwd=str(BASE_DIR))
        processes.append(node_proc)

    else:
        # Hardware Gateway mode
        cmd = [python_executable, str(HW_GATEWAY_SCRIPT)]
        if args.port:
            cmd.extend(["--port", args.port])
        if args.broker:
            cmd.extend(["--broker", args.broker])
        if args.token:
            cmd.extend(["--token", args.token])
        print("[Launcher] Starting Local Gateway (Hardware UART)...")
        hw_proc = subprocess.Popen(cmd, cwd=str(BASE_DIR))
        processes.append(hw_proc)

        if not args.no_browser:
            threading.Thread(target=open_browser_when_ready, args=(WEB_HOST, WEB_PORT, DASHBOARD_URL), daemon=True).start()

    print("[Launcher] System running. Press Ctrl+C at any time to shut down all components.")

    # Main supervisor loop
    try:
        while True:
            for proc in processes:
                exit_code = proc.poll()
                if exit_code is not None:
                    print(f"[Launcher Warning] Process PID {proc.pid} exited unexpectedly with code {exit_code}.")
                    shutdown_handler()
            time.sleep(1.0)
    except KeyboardInterrupt:
        shutdown_handler()


if __name__ == "__main__":
    main()
