#!/usr/bin/env python3
"""
deploy_thingsboard.py
=====================
Automated Deployment & Management Tool for Local ThingsBoard (Criterion N07).
Features:
1. Docker daemon and Docker Compose availability checks.
2. Launching ThingsBoard container stack (tb-postgres).
3. Polling HTTP health check (http://localhost:9090) and MQTT port (1883).
4. Stopping/cleaning up the stack via --stop / --down.
Strictly English. Zero icons or emojis.
"""

import argparse
import logging
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] (TB-Deployer) %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ThingsBoardDeployer")

DEFAULT_HTTP_PORT = 9090
DEFAULT_MQTT_PORT = 1883
HEALTH_CHECK_URL = f"http://localhost:{DEFAULT_HTTP_PORT}/login"
MAX_HEALTH_WAIT_SECONDS = 180
POLL_INTERVAL_SECONDS = 5

DEFAULT_CREDENTIALS = [
    ("System Administrator", "sysadmin@thingsboard.org", "sysadmin"),
    ("Tenant Administrator", "tenant@thingsboard.org", "tenant"),
    ("Customer User", "customer@thingsboard.org", "customer"),
]


class ThingsBoardDeployer:
    def __init__(self, compose_file: Path):
        self.compose_file = compose_file
        self.docker_cmd = self._detect_docker_compose_cmd()

    def _detect_docker_compose_cmd(self) -> List[str]:
        """Detect whether 'docker compose' (V2) or 'docker-compose' (V1) is available."""
        try:
            res = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                logger.info("Detected Docker Compose Plugin (V2 CLI).")
                return ["docker", "compose"]
        except FileNotFoundError:
            pass

        try:
            res = subprocess.run(
                ["docker-compose", "version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                logger.info("Detected Standalone docker-compose (V1 CLI).")
                return ["docker-compose"]
        except FileNotFoundError:
            pass

        logger.error("Neither 'docker compose' nor 'docker-compose' binary found in system PATH.")
        return []

    def check_docker_daemon(self) -> bool:
        """Verify that Docker Engine daemon is active and responsive."""
        logger.info("Checking Docker Engine daemon status...")
        try:
            res = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                logger.info("Docker daemon is active and responsive.")
                return True
            logger.error("Docker daemon is not running. Please start Docker Desktop and retry.")
            return False
        except FileNotFoundError:
            logger.error("Docker CLI executable not found in system PATH.")
            return False

    def start_stack(self) -> bool:
        """Launch the ThingsBoard stack using Docker Compose."""
        if not self.docker_cmd:
            logger.error("Cannot start stack: Docker Compose CLI missing.")
            return False

        if not self.compose_file.exists():
            logger.error(f"Compose file not found at: {self.compose_file.resolve()}")
            return False

        logger.info(f"Starting ThingsBoard stack using: {self.compose_file.name}")
        cmd = self.docker_cmd + ["-f", str(self.compose_file), "up", "-d"]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            for line in res.stdout.splitlines():
                if line.strip():
                    logger.info(f"  {line}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start stack (exit code {e.returncode}): {e.stderr}")
            return False

    def stop_stack(self) -> bool:
        """Stop and tear down the ThingsBoard stack."""
        if not self.docker_cmd:
            logger.error("Docker Compose CLI missing.")
            return False

        logger.info("Stopping ThingsBoard stack...")
        cmd = self.docker_cmd + ["-f", str(self.compose_file), "down"]
        try:
            subprocess.run(cmd, check=True)
            logger.info("ThingsBoard stack stopped successfully.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop stack: {e}")
            return False

    def check_mqtt_port(self) -> bool:
        """Verify TCP socket connectivity on local MQTT port 1883."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                return s.connect_ex(("127.0.0.1", DEFAULT_MQTT_PORT)) == 0
        except Exception:
            return False

    def wait_for_healthcheck(self, timeout: int = MAX_HEALTH_WAIT_SECONDS) -> bool:
        """Poll HTTP login page until database schema and web application respond."""
        logger.info(f"Waiting for ThingsBoard HTTP service on port {DEFAULT_HTTP_PORT}...")
        logger.info("Note: Initial database initialization typically takes 45-90 seconds.")

        start_time = time.time()
        req = Request(HEALTH_CHECK_URL, headers={"User-Agent": "TB-Deployer/1.0"})

        while time.time() - start_time < timeout:
            elapsed = int(time.time() - start_time)
            try:
                with urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        mqtt_ready = self.check_mqtt_port()
                        logger.info(
                            f"ThingsBoard Web UI is ONLINE (HTTP 200 OK) after {elapsed}s. "
                            f"MQTT Port ({DEFAULT_MQTT_PORT}): {'OPEN' if mqtt_ready else 'PENDING'}"
                        )
                        return True
            except (HTTPError, URLError, TimeoutError, ConnectionResetError, socket.timeout):
                logger.info(f"  [{elapsed}s / {timeout}s] Waiting for ThingsBoard container initialization...")

            time.sleep(POLL_INTERVAL_SECONDS)

        logger.error(f"Health check timed out after {timeout} seconds.")
        return False

    def display_summary(self):
        """Output deployment summary and default credentials."""
        banner = "=" * 70
        print(f"\n{banner}")
        print("     THINGSBOARD LOCAL DEPLOYMENT SUCCESSFUL (Criterion N07)")
        print(f"{banner}")
        print(f"  Web Interface URL : http://localhost:{DEFAULT_HTTP_PORT}")
        print(f"  MQTT Broker Host  : localhost:{DEFAULT_MQTT_PORT}")
        print("  CoAP Endpoint     : localhost:5683 (UDP)")
        print("-" * 70)
        print("  DEFAULT CREDENTIALS:")
        print(f"  {'Role':<22} | {'Username':<28} | {'Password'}")
        print("-" * 70)
        for role, user, pwd in DEFAULT_CREDENTIALS:
            print(f"  {role:<22} | {user:<28} | {pwd}")
        print("-" * 70)
        print("  INTEGRATION WITH LOCAL GATEWAY:")
        print("  To point LocalGateway to this local ThingsBoard instance, run:")
        print(f"    python LocalGateway.py --broker localhost --port COM3")
        print(f"    python start_system.py --broker localhost")
        print(f"{banner}\n")


def main():
    parser = argparse.ArgumentParser(description="ThingsBoard Local Stack Automated Deployment Tool")
    default_compose = str(Path(__file__).resolve().parent / "docker-compose.yml")
    parser.add_argument("--file", "-f", default=default_compose, help="Path to docker-compose.yml")
    parser.add_argument("--timeout", "-t", type=int, default=MAX_HEALTH_WAIT_SECONDS, help="Max wait time in seconds")
    parser.add_argument("--stop", "--down", action="store_true", help="Stop and take down the ThingsBoard container stack")
    args = parser.parse_args()

    compose_path = Path(args.file).resolve()
    deployer = ThingsBoardDeployer(compose_path)

    if args.stop:
        if deployer.stop_stack():
            sys.exit(0)
        sys.exit(1)

    if not deployer.check_docker_daemon():
        sys.exit(1)

    if not deployer.start_stack():
        sys.exit(1)

    if deployer.wait_for_healthcheck(timeout=args.timeout):
        deployer.display_summary()
        sys.exit(0)
    else:
        logger.error("Deployment finished but service failed health check within timeout.")
        sys.exit(1)


if __name__ == "__main__":
    main()
