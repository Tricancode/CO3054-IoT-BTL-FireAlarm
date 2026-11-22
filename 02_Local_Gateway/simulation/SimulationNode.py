"""
SimulationNode.py
=================
Virtual End Node (YoloUNO ESP32-S3) for Smart Fire Alarm System.
- Wireless communication (ESP-NOW / Local Wi-Fi) is simulated via UDP Sockets.
- Periodically samples and transmits environmental sensor telemetry: Smoke (ppm), Flame (0/1), and actuator states.
- Listens for downstream actuator control commands from Local Gateway (Servo, Buzzer, LED).
- Strictly English logs and zero icons or emojis.
"""

import json
import random
import socket
import sys
import threading
import time

# Local simulation network configuration
GATEWAY_IP = "127.0.0.1"
GATEWAY_PORT = 5000
NODE_PORT = 5001

# Virtual hardware actuator states
hardware_state = {
    "servo": 0,       # 0 degrees: Normal open, 90 degrees: Fire barrier closed
    "buzzer": 0,      # 0: Siren off, 1: Emergency siren active
    "led": 0,         # 0: LED off, 1: Red warning strobe active
}
state_lock = threading.Lock()

# UDP socket initialization
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    sock.bind(("127.0.0.1", NODE_PORT))
except Exception as e:
    print(f"[End Node Error] Unable to bind UDP port {NODE_PORT}: {e}")
    sys.exit(1)


def receive_commands():
    """Background listener for downstream commands from the Gateway."""
    print(f"[End Node] Listening for downstream commands at UDP 127.0.0.1:{NODE_PORT}...")
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            command = json.loads(data.decode("utf-8"))
            print(f"\n[End Node] Received command from Gateway ({addr[0]}:{addr[1]}): {command}")

            with state_lock:
                if "servo" in command:
                    hardware_state["servo"] = int(command["servo"])
                    angle = hardware_state["servo"]
                    status = "FIRE DOOR CLOSED" if angle > 45 else "FIRE DOOR OPEN"
                    print(f" -> [Actuator Servo] Rotated to {angle} degrees ({status})")

                if "buzzer" in command:
                    hardware_state["buzzer"] = 1 if command["buzzer"] else 0
                    print(f" -> [Actuator Buzzer] Audio Siren: {'ACTIVE' if hardware_state['buzzer'] else 'OFF'}")

                if "led" in command:
                    hardware_state["led"] = 1 if command["led"] else 0
                    print(f" -> [Actuator LED] Visual Alarm: {'BLINKING RED' if hardware_state['led'] else 'OFF'}")

        except Exception as e:
            print(f"[End Node Error] Command parsing error: {e}")


def main():
    t = threading.Thread(target=receive_commands, daemon=True)
    t.start()

    print("=" * 65)
    print("VIRTUAL END NODE ESP32-S3 (YOLOUNO) - FIRE ALARM SYSTEM")
    print(f" -> Gateway Telemetry Target: {GATEWAY_IP}:{GATEWAY_PORT}")
    print(f" -> Downstream Command Port : 127.0.0.1:{NODE_PORT}")
    print("=" * 65)

    fire_incident_active = False
    fire_counter = 0

    while True:
        try:
            # Environmental simulation:
            # 12% probability of a fire outbreak lasting 3 cycles
            if not fire_incident_active and random.randint(1, 100) > 88:
                fire_incident_active = True
                fire_counter = 3
                print("\n[SIMULATION EVENT] WARNING: Fire incident triggered! Smoke and flame surging!")

            if fire_incident_active:
                smoke_level = random.uniform(75.0, 98.0)
                flame_detected = 1
                fire_counter -= 1
                if fire_counter <= 0:
                    fire_incident_active = False
                    print("\n[SIMULATION EVENT] NOTICE: Fire incident cleared. Environment returned to normal.")
            else:
                smoke_level = random.uniform(8.0, 32.0)  # Normal smoke level
                flame_detected = 0

            with state_lock:
                current_servo = hardware_state["servo"]
                current_buzzer = hardware_state["buzzer"]
                current_led = hardware_state["led"]

            payload = {
                "device_id": "YOLOUNO_FIRE_NODE_01",
                "smoke": round(smoke_level, 2),
                "flame": flame_detected,
                "servo": current_servo,
                "buzzer": current_buzzer,
                "led": current_led,
                "timestamp": round(time.time(), 2)
            }

            msg_bytes = json.dumps(payload).encode("utf-8")
            sock.sendto(msg_bytes, (GATEWAY_IP, GATEWAY_PORT))
            print(f"[End Node TX -> Gateway] Smoke: {payload['smoke']} ppm | Flame: {payload['flame']} | Servo: {payload['servo']} deg | Buzzer: {payload['buzzer']} | LED: {payload['led']}")

            time.sleep(3)

        except KeyboardInterrupt:
            print("\n[End Node] Simulation terminated gracefully.")
            break
        except Exception as e:
            print(f"[End Node Error] Loop error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
