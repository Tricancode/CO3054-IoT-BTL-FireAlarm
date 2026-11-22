"""
start_system.py
===============
All-in-One System Runner for Local IoT Gateway & End Node (T08, T10 - HCMUT).
Allows launching the entire ecosystem with a single command:
1. Spawns the Local Gateway process (Simulation or Hardware mode).
2. Waits for Web Dashboard port (5050) and ThingsBoard Dashboard (9090) readiness.
3. Automatically opens browser tabs for Local Monitor and ThingsBoard.
4. Auto-detects active Local ThingsBoard (ports 1883/9090) and prioritizes localhost broker.
5. Spawns the Simulation Node (in simulation mode).
6. Handles graceful cross-platform shutdown on Ctrl+C.
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
DASHBOARD_URL = f"http://localhost:5050"

TB_LOCAL_HOST = "127.0.0.1"
TB_LOCAL_HTTP_PORT = 9090
TB_LOCAL_MQTT_PORT = 1883
TB_DEFAULT_URL = f"http://localhost:{TB_LOCAL_HTTP_PORT}"

STARTUP_TIMEOUT = 10.0

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


def open_browser_when_ready(host: str, port: int, url: str, label: str = "Web dashboard") -> None:
    """Polls Web UI port and launches default browser upon readiness."""
    start_time = time.time()
    while time.time() - start_time < STARTUP_TIMEOUT:
        if is_shutting_down:
            return
        if is_port_open(host, port):
            print(f"[Launcher] {label} ready on port {port}. Opening browser: {url}")
            webbrowser.open(url)
            return
        time.sleep(0.3)
    print(f"[Launcher Warning] {label} port {port} timed out. Browser launch skipped.")


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
        default=None,
        help="MQTT Broker address (default: auto-detects localhost if local ThingsBoard is active, else app.coreiot.io)"
    )
    parser.add_argument(
        "--token",
        default="i2tchqq1390qcxhun4zr",
        help="Device Access Token"
    )
    parser.add_argument(
        "--tb-url",
        default=None,
        help="ThingsBoard Dashboard URL to open (default: http://localhost:9090 or https://app.coreiot.io based on broker)"
    )
    parser.add_argument(
        "--no-tb-browser",
        action="store_true",
        help="Do not open ThingsBoard dashboard in browser."
    )
    args = parser.parse_args()

    # Register OS signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    tb_local_active = is_local_thingsboard_active()

    # Resolve broker: user argument > auto-detected local ThingsBoard > app.coreiot.io
    if args.broker is not None:
        broker = args.broker
    elif tb_local_active:
        broker = "127.0.0.1"
        print("[Launcher] Auto-detected active local ThingsBoard stack on port 9090/1883. Selected broker: 127.0.0.1")
    else:
        broker = "app.coreiot.io"

    # Resolve ThingsBoard Web UI URL
    if args.tb_url:
        tb_url = args.tb_url
    elif broker in ("127.0.0.1", "localhost"):
        tb_url = TB_DEFAULT_URL
    else:
        tb_url = "https://app.coreiot.io"

    print("=" * 65)
    print("HCMUT IOT FIRE ALARM SYSTEM - UNIFIED LAUNCHER")
    print(f" -> Mode          : {args.mode.upper()}")
    print(f" -> Broker        : {broker}")
    print(f" -> Local Monitor : {DASHBOARD_URL}")
    print(f" -> ThingsBoard   : {tb_url}")
    print("=" * 65)

    python_executable = sys.executable

    def start_dashboard_browsers():
        if args.no_browser:
            return

        # 1. Open Local Gateway Monitor (port 5050)
        threading.Thread(
            target=open_browser_when_ready,
            args=(WEB_HOST, WEB_PORT, DASHBOARD_URL, "Local Web Monitor"),
            daemon=True
        ).start()

        # 2. Open ThingsBoard Dashboard
        if not args.no_tb_browser:
            if broker in ("127.0.0.1", "localhost") and tb_local_active:
                threading.Thread(
                    target=open_browser_when_ready,
                    args=(TB_LOCAL_HOST, TB_LOCAL_HTTP_PORT, tb_url, "ThingsBoard Dashboard"),
                    daemon=True
                ).start()
            else:
                def _open_remote_tb():
                    time.sleep(1.0)
                    if not is_shutting_down:
                        print(f"[Launcher] Opening remote ThingsBoard in browser: {tb_url}")
                        webbrowser.open(tb_url)
                threading.Thread(target=_open_remote_tb, daemon=True).start()

    if args.mode == "sim":
        # 1. Start Local Simulation Gateway
        print("[Launcher] Starting Local Gateway (Simulation)...")
        gw_cmd = [python_executable, str(SIM_GATEWAY_SCRIPT)]
        if broker != "app.coreiot.io":
            gw_cmd.extend(["--broker", broker])
        if args.token != "i2tchqq1390qcxhun4zr":
            gw_cmd.extend(["--token", args.token])
        gw_proc = subprocess.Popen(gw_cmd, cwd=str(BASE_DIR))
        processes.append(gw_proc)

        # 2. Start browser launch threads
        start_dashboard_browsers()

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
        if broker:
            cmd.extend(["--broker", broker])
        if args.token:
            cmd.extend(["--token", args.token])
        print("[Launcher] Starting Local Gateway (Hardware UART)...")
        hw_proc = subprocess.Popen(cmd, cwd=str(BASE_DIR))
        processes.append(hw_proc)

        start_dashboard_browsers()

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
