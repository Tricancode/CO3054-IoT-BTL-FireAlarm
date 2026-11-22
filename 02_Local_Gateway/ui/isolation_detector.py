"""
isolation_detector.py
=====================
Isolation Forest Machine Learning Anomaly Detector for IoT Fire Gateway.
Performs real-time edge anomaly detection on multi-sensor telemetry:
- Inputs: Smoke Density (ppm), Ambient Temperature (deg C), Flame Status (0/1).
- Outputs: is_anomaly (0: Normal, 1: Anomaly), anomaly_score (0.0 to 1.0).

Strictly English. Zero icons or emojis.
"""

import math
import threading
from collections import deque
from typing import List, Tuple

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class IsolationDetector:
    """
    Edge Machine Learning Anomaly Detector using Scikit-Learn Isolation Forest.
    Pre-trains an initial baseline to ensure immediate prediction capability,
    and dynamically adapts to normal sensor drift while rejecting anomalies.
    """

    def __init__(
        self,
        window_size: int = 200,
        retrain_interval: int = 50,
        contamination: float = 0.05,
        random_state: int = 42,
    ):
        self.window_size = window_size
        self.retrain_interval = retrain_interval
        self.contamination = contamination
        self.random_state = random_state
        self.lock = threading.Lock()
        self.buffer = deque(maxlen=window_size)
        self.samples_since_retrain = 0
        self.model = None

        self._initialize_baseline_model()

    def _generate_synthetic_baseline(self, num_samples: int = 100) -> List[List[float]]:
        """Generates representative normal ambient indoor sensor readings."""
        samples = []
        for i in range(num_samples):
            # Normal ambient indoor readings: smoke ADC 120-180, temp 24-28 C, flame 0
            smoke_val = 150.0 + ((i % 25) - 12.0) * 2.0
            temp_val = 26.0 + ((i * 3) % 7) - 3.0
            flame_val = 0.0
            samples.append([float(smoke_val), float(temp_val), float(flame_val)])
        return samples

    def _initialize_baseline_model(self) -> None:
        """Fits initial model with baseline data to avoid cold-start delays."""
        baseline_samples = self._generate_synthetic_baseline(100)
        for s in baseline_samples:
            self.buffer.append(s)

        if HAS_SKLEARN:
            X = np.array(baseline_samples, dtype=float)
            self.model = IsolationForest(
                n_estimators=100,
                contamination=self.contamination,
                random_state=self.random_state
            )
            self.model.fit(X)

    def _fit_model(self, data_list: List[List[float]]) -> None:
        """Trains an Isolation Forest model on the provided data snapshot."""
        if not HAS_SKLEARN or len(data_list) < 10:
            return
        X = np.array(data_list, dtype=float)
        # Add small jitter if variance is near-zero to prevent tree degeneration
        if np.any(np.std(X, axis=0) < 1e-4):
            noise = np.random.normal(0, 1e-3, size=X.shape)
            X = X + noise

        model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=self.random_state
        )
        model.fit(X)
        self.model = model

    def update_and_predict(self, smoke: float, temperature: float, flame: float) -> Tuple[int, float]:
        """
        Infers anomaly status and normalized anomaly score for a sensor reading vector.
        Returns:
            is_anomaly: 1 if anomaly detected, else 0
            anomaly_score: normalized float between 0.0 (safe) and 1.0 (extreme anomaly)
        """
        try:
            s = float(smoke)
            t = float(temperature)
            f = float(flame)
        except (ValueError, TypeError):
            return 0, 0.0

        sample = [s, t, f]

        if not HAS_SKLEARN or self.model is None:
            # Statistical rule-based fallback
            is_anom = 1 if (s > 800.0 or t > 45.0 or f > 0.5) else 0
            score = 0.95 if is_anom else 0.15
            return is_anom, score

        with self.lock:
            X_eval = np.array([sample], dtype=float)
            try:
                raw_df = float(self.model.decision_function(X_eval)[0])
                pred = int(self.model.predict(X_eval)[0])
            except Exception:
                return 0, 0.0

            # Sigmoid mapping: decision_function > 0 -> < 0.5, decision_function < 0 -> >= 0.5
            norm = 1.0 / (1.0 + math.exp(raw_df * 15.0))
            anomaly_score = round(min(1.0, max(0.0, norm)), 2)
            is_anomaly = 1 if (pred == -1 or anomaly_score >= 0.65 or f > 0.5 or s > 800.0 or t > 45.0) else 0

            # For active fire or extreme smoke, boost score to reflect severity
            if f > 0.5 or s > 800.0 or t > 45.0:
                anomaly_score = max(anomaly_score, 0.90)

            # Prevent model poisoning: only add normal samples to training buffer
            if is_anomaly == 0:
                self.buffer.append(sample)
                self.samples_since_retrain += 1
                if self.samples_since_retrain >= self.retrain_interval:
                    self.samples_since_retrain = 0
                    snapshot = list(self.buffer)
                    self._fit_model(snapshot)

        return is_anomaly, anomaly_score
