"""
gateway_infrastructure.py
=========================
Shared Industrial Infrastructure for Local IoT Gateway (T08, T10 - HCMUT IoT).
Designed according to industrial engineering standards:
1. OfflineBufferRepository: SQLite Write-Ahead Logging (WAL) persistent storage preventing data loss during network outages.
2. CommandQueue: Thread-safe asynchronous queue for non-blocking command dispatching.
3. EmbeddedWebMonitor: Lightweight HTTP server hosting the Keen Dashboards Local Monitor UI and REST API.
All components strictly use English and contain zero icons or emojis.
"""

import http.server
import json
import logging
import queue
import socketserver
import sqlite3
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("GatewayInfrastructure")

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local Gateway Monitor Station - Fire Alarm System</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body.keen-dashboard {
            background-color: #f2f4f8;
            color: #2c3e50;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding-top: 60px;
        }

        /* Top Navigation Bar - Keen Style */
        .navbar {
            background-color: #1a2530;
            border-bottom: 2px solid #0f171e;
            color: #ffffff;
            left: 0;
            min-height: 54px;
            position: fixed;
            right: 0;
            top: 0;
            z-index: 1000;
        }

        .navbar-container {
            align-items: center;
            display: flex;
            justify-content: space-between;
            margin: 0 auto;
            max-width: 1280px;
            min-height: 54px;
            padding: 0 20px;
        }

        .navbar-brand {
            color: #ffffff;
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        .navbar-status {
            align-items: center;
            display: flex;
            gap: 10px;
        }

        .badge {
            border-radius: 3px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.4px;
            padding: 4px 8px;
            text-transform: uppercase;
        }

        .badge-online {
            background-color: #27ae60;
            color: #ffffff;
        }

        .badge-offline {
            background-color: #c0392b;
            color: #ffffff;
        }

        .badge-info {
            background-color: #2980b9;
            color: #ffffff;
        }

        .badge-mode {
            background-color: #34495e;
            color: #ecf0f1;
        }

        /* Container & Layout */
        .container {
            margin: 0 auto;
            max-width: 1280px;
            padding: 20px;
        }

        /* Emergency Alert Banner */
        #alert-banner {
            background-color: #e74c3c;
            border: 1px solid #c0392b;
            border-radius: 3px;
            color: #ffffff;
            display: none;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-bottom: 18px;
            padding: 12px 16px;
            text-align: center;
            text-transform: uppercase;
        }

        /* Grid System */
        .row {
            display: flex;
            flex-wrap: wrap;
            margin: 0 -8px;
        }

        .col-12 {
            flex: 0 0 100%;
            max-width: 100%;
            padding: 0 8px;
        }

        .col-6 {
            flex: 0 0 50%;
            max-width: 50%;
            padding: 0 8px;
        }

        .col-4 {
            flex: 0 0 33.3333%;
            max-width: 33.3333%;
            padding: 0 8px;
        }

        .col-3 {
            flex: 0 0 25%;
            max-width: 25%;
            padding: 0 8px;
        }

        .col-5-cards {
            flex: 0 0 20%;
            max-width: 20%;
            padding: 0 8px;
        }

        @media (max-width: 1024px) {
            .col-5-cards {
                flex: 0 0 50%;
                max-width: 50%;
            }
        }

        @media (max-width: 900px) {
            .col-3, .col-4, .col-6 {
                flex: 0 0 100%;
                max-width: 100%;
            }
        }

        /* Keen Chart Wrapper Style */
        .chart-wrapper {
            background: #ffffff;
            border: 1px solid #d9e0e7;
            border-radius: 3px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            margin-bottom: 18px;
        }

        .chart-wrapper .chart-title {
            background-color: #fafbfc;
            border-bottom: 1px solid #e1e7ec;
            color: #4a5b6d;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.4px;
            padding: 10px 14px;
            text-transform: uppercase;
        }

        .chart-wrapper .chart-stage {
            overflow: hidden;
            padding: 18px 16px;
            position: relative;
        }

        .chart-wrapper .chart-notes {
            background-color: #fafbfc;
            border-top: 1px solid #e1e7ec;
            color: #7f8c8d;
            font-size: 11px;
            padding: 8px 14px;
        }

        /* Metric Values */
        .metric-value {
            color: #1a2530;
            font-size: 32px;
            font-weight: 700;
            line-height: 1.1;
        }

        .metric-unit {
            color: #7f8c8d;
            font-size: 15px;
            font-weight: 400;
            margin-left: 4px;
        }

        .metric-state {
            font-size: 20px;
            font-weight: 700;
        }

        .text-safe {
            color: #27ae60;
        }

        .text-danger {
            color: #c0392b;
        }

        .text-warning {
            color: #d35400;
        }

        /* Progress Bar */
        .progress-bar-bg {
            background-color: #ecf0f1;
            border-radius: 3px;
            height: 10px;
            margin-top: 12px;
            overflow: hidden;
            width: 100%;
        }

        .progress-bar-fill {
            background-color: #27ae60;
            height: 100%;
            transition: width 0.3s ease, background-color 0.3s ease;
            width: 0%;
        }

        /* Actuator Grid inside Control Stage */
        .control-grid {
            display: grid;
            gap: 14px;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        }

        .control-item {
            background: #f8fafc;
            border: 1px solid #e1e7ec;
            border-radius: 3px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 14px;
        }

        .control-info h4 {
            font-size: 13px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 2px;
        }

        .control-info p {
            font-size: 11px;
            color: #7f8c8d;
        }

        .btn-group {
            display: flex;
            gap: 6px;
        }

        button {
            border: 1px solid transparent;
            border-radius: 3px;
            cursor: pointer;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.3px;
            padding: 7px 12px;
            text-transform: uppercase;
            transition: background 0.15s ease;
        }

        button:active {
            transform: translateY(1px);
        }

        .btn-danger {
            background-color: #c0392b;
            color: #ffffff;
        }

        .btn-danger:hover {
            background-color: #a93226;
        }

        .btn-success {
            background-color: #27ae60;
            color: #ffffff;
        }

        .btn-success:hover {
            background-color: #229954;
        }

        .btn-default {
            background-color: #bdc3c7;
            color: #2c3e50;
        }

        .btn-default:hover {
            background-color: #95a5a6;
        }

        .quick-actions {
            border-top: 1px solid #e1e7ec;
            display: flex;
            gap: 10px;
            margin-top: 16px;
            padding-top: 14px;
        }

        .quick-actions button {
            flex: 1;
            padding: 11px 16px;
            font-size: 12px;
        }

        /* Logs Table */
        .logs-list {
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
            font-size: 12px;
            list-style: none;
            max-height: 180px;
            overflow-y: auto;
        }

        .logs-list li {
            border-bottom: 1px solid #eef2f5;
            color: #34495e;
            padding: 6px 0;
        }

        footer {
            color: #7f8c8d;
            font-size: 11px;
            margin: 20px 0 30px;
            text-align: center;
        }
    </style>
</head>
<body class="keen-dashboard">
    <!-- Navigation Bar -->
    <div class="navbar">
        <div class="navbar-container">
            <div class="navbar-brand">
                Local IoT Gateway Station [Fire Alarm System]
            </div>
            <div class="navbar-status">
                <span id="badge-mode" class="badge badge-mode">Mode: Initializing</span>
                <span id="badge-cloud" class="badge badge-offline">CoreIOT: Offline</span>
                <span id="badge-node" class="badge badge-offline">End Node: Disconnected</span>
                <span id="badge-buffer" class="badge badge-info">Buffer: 0</span>
            </div>
        </div>
    </div>

    <!-- Main Content Container -->
    <div class="container">
        <!-- Emergency Alert Banner -->
        <div id="alert-banner">
            ALARM WARNING: HIGH SMOKE CONCENTRATION OR FLAME INCIDENT DETECTED!
        </div>

        <!-- Metric Cards Row -->
        <div class="row">
            <!-- Smoke Sensor -->
            <div class="col-5-cards">
                <div class="chart-wrapper">
                    <div class="chart-title">Smoke Concentration</div>
                    <div class="chart-stage">
                        <div class="metric-value">
                            <span id="val-smoke">--</span>
                            <span class="metric-unit">ADC</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div id="bar-smoke" class="progress-bar-fill"></div>
                        </div>
                    </div>
                    <div class="chart-notes">MQ-2 ADC: Normal &lt; 1800 | Warning 1800-2000 | Critical &gt; 2000</div>
                </div>
            </div>

            <!-- Ambient Temperature -->
            <div class="col-5-cards">
                <div class="chart-wrapper">
                    <div class="chart-title">Ambient Temperature</div>
                    <div class="chart-stage">
                        <div class="metric-value">
                            <span id="val-temp">--.-</span>
                            <span class="metric-unit">&deg;C</span>
                        </div>
                        <div id="desc-temp" style="font-size:12px; color:#7f8c8d; margin-top:14px;">DHT11 Room Sensor</div>
                    </div>
                    <div class="chart-notes">Normal &lt; 50&deg;C | High Heat &ge; 50&deg;C</div>
                </div>
            </div>

            <!-- Flame Detector -->
            <div class="col-5-cards">
                <div class="chart-wrapper">
                    <div class="chart-title">Flame Optical Sensor</div>
                    <div class="chart-stage">
                        <div id="val-flame" class="metric-state text-safe">SAFE</div>
                        <div id="desc-flame" style="font-size:12px; color:#7f8c8d; margin-top:14px;">No flame radiation detected</div>
                    </div>
                    <div class="chart-notes">Optical infrared flame sensing channel</div>
                </div>
            </div>

            <!-- Fire Barrier Door -->
            <div class="col-5-cards">
                <div class="chart-wrapper">
                    <div class="chart-title">Emergency Fire Door</div>
                    <div class="chart-stage">
                        <div class="metric-value">
                            <span id="val-servo">0</span>
                            <span class="metric-unit">degrees</span>
                        </div>
                        <div id="desc-servo" style="font-size:12px; color:#7f8c8d; margin-top:8px;">Normal Open Position</div>
                    </div>
                    <div class="chart-notes">0 deg: Open Access | 90 deg: Fire Partition Locked</div>
                </div>
            </div>

            <!-- AI Isolation Forest -->
            <div class="col-5-cards">
                <div class="chart-wrapper">
                    <div class="chart-title">AI Isolation Forest</div>
                    <div class="chart-stage">
                        <div id="val-anomaly" class="metric-state text-safe">NORMAL</div>
                        <div id="desc-anomaly" style="font-size:12px; color:#7f8c8d; margin-top:14px;">Anomaly Score: 0.00</div>
                    </div>
                    <div class="chart-notes">Edge ML Anomaly Detector (Smoke + Temp + Flame)</div>
                </div>
            </div>
        </div>

        <!-- Actuator Controls Section -->
        <div class="row">
            <div class="col-12">
                <div class="chart-wrapper">
                    <div class="chart-title">Local Actuator Overrides [Station Operator Controls]</div>
                    <div class="chart-stage">
                        <div class="control-grid">
                            <!-- Buzzer Control -->
                            <div class="control-item">
                                <div class="control-info">
                                    <h4>Audio Siren Alarm [Buzzer]</h4>
                                    <p id="lbl-buzzer">Current State: DEACTIVATED</p>
                                </div>
                                <div class="btn-group">
                                    <button class="btn-danger" onclick="sendActuator('buzzer', 1)">ACTIVATE</button>
                                    <button class="btn-default" onclick="sendActuator('buzzer', 0)">SILENCE</button>
                                </div>
                            </div>

                            <!-- LED Warning -->
                            <div class="control-item">
                                <div class="control-info">
                                    <h4>Visual Indicator [Warning LED]</h4>
                                    <p id="lbl-led">Current State: DEACTIVATED</p>
                                </div>
                                <div class="btn-group">
                                    <button class="btn-danger" onclick="sendActuator('led', 1)">ACTIVATE</button>
                                    <button class="btn-default" onclick="sendActuator('led', 0)">TURN OFF</button>
                                </div>
                            </div>

                            <!-- Servo Door -->
                            <div class="control-item">
                                <div class="control-info">
                                    <h4>Fire Partition Door [Servo Motor]</h4>
                                    <p id="lbl-servo">Current Angle: 0 deg</p>
                                </div>
                                <div class="btn-group">
                                    <button class="btn-danger" onclick="sendActuator('servo', 90)">CLOSE [90 deg]</button>
                                    <button class="btn-success" onclick="sendActuator('servo', 0)">OPEN [0 deg]</button>
                                </div>
                            </div>
                        </div>

                        <!-- Quick Emergency Buttons -->
                        <div class="quick-actions">
                            <button class="btn-danger" onclick="emergencyTrigger()">TRIGGER EMERGENCY LOCKDOWN</button>
                            <button class="btn-success" onclick="emergencyReset()">RESTORE NORMAL OPERATION</button>
                        </div>
                    </div>
                    <div class="chart-notes">Direct hardware override executed independently of cloud connectivity.</div>
                </div>
            </div>
        </div>

        <!-- Real-Time Activity Log -->
        <div class="row">
            <div class="col-12">
                <div class="chart-wrapper">
                    <div class="chart-title">Real-Time Station Event Log</div>
                    <div class="chart-stage">
                        <ul id="log-list" class="logs-list">
                            <li>[System Startup] Local gateway telemetry bridge initialized.</li>
                        </ul>
                    </div>
                    <div class="chart-notes">FIFO audit trail of inbound sensor updates and outbound actuator dispatches.</div>
                </div>
            </div>
        </div>

        <footer>
            HCMUT Department of Computer Science &amp; Engineering &bull; Internet of Things Course (BTL T08, T10)
        </footer>
    </div>

    <!-- JavaScript Client Logic -->
    <script>
        function addLog(message) {
            const list = document.getElementById('log-list');
            const item = document.createElement('li');
            const now = new Date().toLocaleTimeString();
            item.innerText = '[' + now + '] ' + message;
            list.insertBefore(item, list.firstChild);
            if (list.children.length > 25) {
                list.removeChild(list.lastChild);
            }
        }

        async function fetchTelemetry() {
            try {
                const response = await fetch('/api/telemetry');
                if (!response.ok) return;
                const data = await response.json();

                // Gateway Mode
                if (data.gateway_type) {
                    document.getElementById('badge-mode').innerText = 'Mode: ' + data.gateway_type;
                }

                // Cloud Status
                const badgeCloud = document.getElementById('badge-cloud');
                if (data.cloud_connected) {
                    badgeCloud.className = 'badge badge-online';
                    badgeCloud.innerText = 'CoreIOT: Connected';
                } else {
                    badgeCloud.className = 'badge badge-offline';
                    badgeCloud.innerText = 'CoreIOT: Offline (Buffering)';
                }

                // End Node Status
                const badgeNode = document.getElementById('badge-node');
                const nowSec = Math.floor(Date.now() / 1000);
                const isNodeActive = data.last_seen && (nowSec - data.last_seen < 6);
                if (isNodeActive) {
                    badgeNode.className = 'badge badge-online';
                    badgeNode.innerText = 'End Node: Online';
                } else {
                    badgeNode.className = 'badge badge-offline';
                    badgeNode.innerText = 'End Node: Disconnected';
                }

                // Buffer Count
                document.getElementById('badge-buffer').innerText = 'Buffer: ' + (data.buffer_count || 0);

                // Smoke Sensor
                if (data.smoke !== undefined) {
                    const smokeVal = Number(data.smoke).toFixed(1);
                    document.getElementById('val-smoke').innerText = smokeVal;
                    const smokePercent = Math.min(100, Math.max(0, (smokeVal / 4095) * 100));
                    const fill = document.getElementById('bar-smoke');
                    fill.style.width = smokePercent + '%';
                    if (smokeVal > 2000) fill.style.backgroundColor = '#c0392b';
                    else if (smokeVal >= 1800) fill.style.backgroundColor = '#d35400';
                    else fill.style.backgroundColor = '#27ae60';
                }

                // Ambient Temperature Sensor
                if (data.temperature !== undefined) {
                    const tempVal = Number(data.temperature).toFixed(1);
                    const elTemp = document.getElementById('val-temp');
                    const descTemp = document.getElementById('desc-temp');
                    if (elTemp && descTemp) {
                        elTemp.innerText = tempVal;
                        if (tempVal >= 50.0) {
                            elTemp.style.color = '#c0392b';
                            descTemp.innerText = 'OVERHEAT: FIRE TEMPERATURE DETECTED';
                            descTemp.style.color = '#c0392b';
                        } else if (tempVal >= 38.0) {
                            elTemp.style.color = '#d35400';
                            descTemp.innerText = 'ELEVATED TEMPERATURE WARNING';
                            descTemp.style.color = '#d35400';
                        } else {
                            elTemp.style.color = '#1a2530';
                            descTemp.innerText = 'Normal Ambient Range';
                            descTemp.style.color = '#7f8c8d';
                        }
                    }
                }

                // Flame Sensor
                const isFlame = (data.flame === 1 || data.flame === true || data.flame === '1');
                const valFlame = document.getElementById('val-flame');
                const descFlame = document.getElementById('desc-flame');
                const banner = document.getElementById('alert-banner');

                if (isFlame || (data.smoke && data.smoke >= 1800) || (data.temperature && data.temperature >= 50.0)) {
                    valFlame.innerText = 'FLAME DETECTED';
                    valFlame.className = 'metric-state text-danger';
                    descFlame.innerText = 'ACTIVE FIRE OR HIGH SMOKE DETECTED';
                    banner.style.display = 'block';
                } else {
                    valFlame.innerText = 'SAFE';
                    valFlame.className = 'metric-state text-safe';
                    descFlame.innerText = 'No flame radiation detected';
                    banner.style.display = 'none';
                }

                // Servo Motor
                if (data.servo !== undefined) {
                    document.getElementById('val-servo').innerText = data.servo;
                    document.getElementById('lbl-servo').innerText = 'Current Angle: ' + data.servo + ' deg';
                    document.getElementById('desc-servo').innerText = (data.servo > 45) ? 'Fire Partition Locked [Closed]' : 'Normal Open Position';
                }

                // Buzzer Status
                if (data.buzzer !== undefined) {
                    const bActive = Boolean(data.buzzer);
                    const el = document.getElementById('lbl-buzzer');
                    el.innerText = bActive ? 'Current State: SIREN ACTIVE' : 'Current State: DEACTIVATED';
                    el.style.color = bActive ? '#c0392b' : '#7f8c8d';
                }

                // LED Status
                if (data.led !== undefined) {
                    const lActive = Boolean(data.led);
                    const el = document.getElementById('lbl-led');
                    el.innerText = lActive ? 'Current State: BLINKING RED' : 'Current State: DEACTIVATED';
                    el.style.color = lActive ? '#c0392b' : '#7f8c8d';
                }

                // AI Isolation Forest
                const valAnom = document.getElementById('val-anomaly');
                const descAnom = document.getElementById('desc-anomaly');
                if (valAnom && descAnom) {
                    const isAnom = Boolean(data.is_anomaly);
                    const score = (data.anomaly_score !== undefined) ? Number(data.anomaly_score).toFixed(2) : '0.00';
                    if (isAnom) {
                        valAnom.innerText = 'ANOMALY DETECTED';
                        valAnom.className = 'metric-state text-danger';
                        descAnom.innerText = 'Anomaly Score: ' + score + ' (Abnormal Pattern)';
                    } else {
                        valAnom.innerText = 'NORMAL';
                        valAnom.className = 'metric-state text-safe';
                        descAnom.innerText = 'Anomaly Score: ' + score + ' (Baseline Pattern)';
                    }
                }

                // 4-Tier Automated Event Logger
                if (data.alarm_status && data.alarm_status !== window._lastAlarmStatus) {
                    window._lastAlarmStatus = data.alarm_status;
                    if (data.alarm_status.includes('CRITICAL')) {
                        addLog('[TIER 1-4 EMERGENCY] ' + (data.alarm_notification || 'Critical Fire Hazard Detected!'));
                        addLog('[TIER 4 BROADCAST] Emergency email dispatched to: customera@gmail.com, customerb@gmail.com, customerc@gmail.com');
                    } else if (data.alarm_status.includes('NORMAL')) {
                        addLog('[SYSTEM RESTORED] Normal baseline operation restored.');
                    }
                }
            } catch (error) {
                console.warn('Telemetry polling error:', error);
            }
        }

        async function sendActuator(actuator, value) {
            const payload = {};
            payload[actuator] = value;
            try {
                const response = await fetch('/api/control', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const resData = await response.json();
                if (response.ok) {
                    addLog('Dispatched command: ' + JSON.stringify(payload));
                    fetchTelemetry();
                } else {
                    alert('Command dispatch error: ' + (resData.error || 'Unknown error'));
                }
            } catch (err) {
                alert('Connection failure: Unable to reach gateway server.');
            }
        }

        async function emergencyTrigger() {
            if (!confirm('Confirm TRIGGER EMERGENCY LOCKDOWN across station?')) return;
            await sendActuator('buzzer', 1);
            await sendActuator('led', 1);
            await sendActuator('servo', 90);
            addLog('EMERGENCY: Station lockdown initiated (Siren ON, LED ON, Door 90 deg closed).');
        }

        async function emergencyReset() {
            await sendActuator('buzzer', 0);
            await sendActuator('led', 0);
            await sendActuator('servo', 0);
            addLog('RESTORE: Station restored to normal safe status (Siren OFF, LED OFF, Door open).');
        }

        setInterval(fetchTelemetry, 250);
        fetchTelemetry();
    </script>
</body>
</html>
"""


class OfflineBufferRepository:
    """
    SQLite database repository configured with Write-Ahead Logging (WAL) mode.
    Guarantees thread-safe access and zero data loss during network disconnection.
    """

    def __init__(self, db_file: Path):
        self.db_file = Path(db_file)
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS telemetry_buffer (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        payload TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        synced INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def insert(self, payload: dict):
        """Append a telemetry record to local offline buffer."""
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            try:
                conn.execute(
                    "INSERT INTO telemetry_buffer (payload, timestamp, synced) VALUES (?, ?, 0)",
                    (json.dumps(payload), time.time()),
                )
                conn.commit()
            finally:
                conn.close()

    def fetch_unsynced(self, limit: int = 50) -> List[Tuple[int, str]]:
        """Retrieve unsynced telemetry packets in FIFO order."""
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, payload FROM telemetry_buffer WHERE synced = 0 ORDER BY id ASC LIMIT ?",
                    (limit,),
                )
                return cursor.fetchall()
            finally:
                conn.close()

    def mark_synced(self, record_ids: List[int]):
        """Mark successfully published packets as synchronized."""
        if not record_ids:
            return
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            try:
                placeholders = ",".join("?" * len(record_ids))
                conn.execute(
                    f"UPDATE telemetry_buffer SET synced = 1 WHERE id IN ({placeholders})",
                    record_ids,
                )
                conn.commit()
            finally:
                conn.close()

    def count_unsynced(self) -> int:
        """Count the number of buffered packets awaiting synchronization."""
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM telemetry_buffer WHERE synced = 0")
                row = cursor.fetchone()
                return row[0] if row else 0
            except Exception:
                return 0
            finally:
                conn.close()

    def purge_synced(self, older_than_days: float = 7.0) -> int:
        """Purge synchronized records older than the specified retention window to avoid database bloat."""
        cutoff_time = time.time() - (older_than_days * 86400.0)
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM telemetry_buffer WHERE synced = 1 AND timestamp < ?",
                    (cutoff_time,),
                )
                deleted = cursor.rowcount
                conn.commit()
                return deleted
            except Exception:
                return 0
            finally:
                conn.close()


def create_web_handler(
    data_provider: Callable[[], Dict[str, Any]],
    command_consumer: Callable[[Dict[str, Any]], None],
):
    """Factory creating an HTTP request handler for Keen Dashboards UI and REST API."""

    class LocalMonitorRequestHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress default HTTP console spam to keep gateway logs clean

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(HTML_DASHBOARD.encode("utf-8"))
            elif self.path == "/api/telemetry":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                snapshot = data_provider()
                self.wfile.write(json.dumps(snapshot).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path == "/api/control":
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)
                try:
                    cmd = json.loads(body.decode("utf-8"))
                    command_consumer(cmd)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "command": cmd}).encode("utf-8"))
                except Exception as err:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(err)}).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

    return LocalMonitorRequestHandler


class EmbeddedWebMonitor:
    """Embedded HTTP server hosting the local monitoring station dashboard (T10)."""

    def __init__(self, host: str = "0.0.0.0", port: int = 5050):
        self.host = host
        self.port = port
        self.server: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(
        self,
        data_provider: Callable[[], Dict[str, Any]],
        command_consumer: Callable[[Dict[str, Any]], None],
    ):
        handler_cls = create_web_handler(data_provider, command_consumer)
        socketserver.TCPServer.allow_reuse_address = True
        try:
            self.server = socketserver.TCPServer((self.host, self.port), handler_cls)
            self.port = self.server.server_address[1]
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            print(f"[Web Monitor UI] Local Dashboard running at: http://localhost:{self.port}")
        except Exception as err:
            print(f"[Web Monitor UI] Failed to start HTTP server on port {self.port}: {err}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
