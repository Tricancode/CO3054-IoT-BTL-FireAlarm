#!/usr/bin/env python3
"""
train_tinyml.py
===============
HCMUT IoT (CO3054) - Tiêu chí T05:
Công cụ thu thập dữ liệu, huấn luyện và export ra model TinyML cho ESP32-S3.

Quy trình:
1. Thu thập / Tổng hợp tập dữ liệu đặc trưng cảm biến đa chiều (MQ-2 ADC, Temp, Humidity, Flame).
2. Huấn luyện mô hình Logistic Regression / Neural Classifier có chuẩn hóa z-score.
3. Đánh giá độ chính xác (Accuracy, Confusion Matrix, Classification Report).
4. Tự động xuất model sang header C thuần túy (tinyml_fire_model.h) phục vụ suy luận trực tiếp trên ESP32-S3 (T04).
"""

import os
import sys
import math
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

# Output paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
HEADER_OUTPUT_PATH = PROJECT_ROOT / "include" / "tinyml_fire_model.h"


def generate_synthetic_dataset(num_samples: int = 2000, random_state: int = 42) -> tuple:
    """
    Sinh tập dữ liệu mẫu dựa trên đặc tính vật lý thực tế của hệ thống:
    Features:
      0: mq2_adc (0 - 4095)
      1: temperature (15.0 - 65.0 C)
      2: humidity (20.0 - 95.0 %)
      3: flame (0 hoặc 1)
    Label:
      0: Safe (Bình thường / Không có cháy)
      1: Fire Hazard (Nguy cơ cháy cao / Đang cháy)
    """
    np.random.seed(random_state)
    
    # Số lượng mẫu cho từng trạng thái
    n_safe = int(num_samples * 0.65)
    n_hazard = num_samples - n_safe
    
    # 1. Safe samples:
    # Khói sạch: 120 - 350 ADC (nhiễu ngẫu nhiên)
    mq2_safe = np.random.normal(loc=180, scale=40, size=n_safe).clip(80, 500)
    # Nhiệt độ phòng bình thường: 24 - 34 C
    temp_safe = np.random.normal(loc=28.0, scale=3.0, size=n_safe).clip(20.0, 38.0)
    # Độ ẩm phòng: 50 - 80%
    hum_safe = np.random.normal(loc=65.0, scale=8.0, size=n_safe).clip(40.0, 90.0)
    # Không có lửa
    flame_safe = np.zeros(n_safe)
    labels_safe = np.zeros(n_safe)
    
    X_safe = np.column_stack([mq2_safe, temp_safe, hum_safe, flame_safe])
    
    # 2. Hazard / Fire samples:
    # 3 kịch bản cháy: A) Cháy có lửa bùng, B) Cháy âm ỉ nhiều khói gas, C) Cháy nhiệt độ cao
    n_flame = int(n_hazard * 0.4)
    n_smoke = int(n_hazard * 0.4)
    n_thermal = n_hazard - n_flame - n_smoke
    
    # Kịch bản A: Có lửa
    mq2_a = np.random.uniform(500, 2500, size=n_flame)
    temp_a = np.random.uniform(32.0, 60.0, size=n_flame)
    hum_a = np.random.uniform(20.0, 55.0, size=n_flame)
    flame_a = np.ones(n_flame)
    
    # Kịch bản B: Khói gas đậm đặc
    mq2_b = np.random.uniform(1800, 3800, size=n_smoke)
    temp_b = np.random.uniform(28.0, 50.0, size=n_smoke)
    hum_b = np.random.uniform(25.0, 60.0, size=n_smoke)
    flame_b = np.random.choice([0, 1], p=[0.7, 0.3], size=n_smoke)
    
    # Kịch bản C: Quá nhiệt cháy âm ỉ
    mq2_c = np.random.uniform(900, 2200, size=n_thermal)
    temp_c = np.random.uniform(50.0, 68.0, size=n_thermal)
    hum_c = np.random.uniform(20.0, 45.0, size=n_thermal)
    flame_c = np.random.choice([0, 1], p=[0.8, 0.2], size=n_thermal)
    
    X_hazard = np.vstack([
        np.column_stack([mq2_a, temp_a, hum_a, flame_a]),
        np.column_stack([mq2_b, temp_b, hum_b, flame_b]),
        np.column_stack([mq2_c, temp_c, hum_c, flame_c]),
    ])
    labels_hazard = np.ones(n_hazard)
    
    X = np.vstack([X_safe, X_hazard])
    y = np.concatenate([labels_safe, labels_hazard])
    
    # Shuffle dataset
    indices = np.random.permutation(len(y))
    return X[indices], y[indices]


def train_model(X: np.ndarray, y: np.ndarray):
    """Huấn luyện mô hình phân loại Logistic Regression chuẩn hóa z-score."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Tính mean và std cho chuẩn hóa Z-score
    mean = np.mean(X_train, axis=0)
    std = np.std(X_train, axis=0)
    std[std == 0] = 1.0  # Tránh chia cho 0
    
    X_train_scaled = (X_train - mean) / std
    X_test_scaled = (X_test - mean) / std
    
    model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    # Đánh giá
    y_pred = model.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    
    print("\n" + "=" * 60)
    print("=== TINYML MODEL TRAINING EVALUATION (T05 CRITERIA) ===")
    print("=" * 60)
    print(f"Dataset Size         : {len(X)} samples (Train: {len(X_train)}, Test: {len(X_test)})")
    print(f"Overall Accuracy     : {acc * 100:.2f}%")
    print(f"Confusion Matrix     :\n{confusion_matrix(y_test, y_pred)}")
    print("\nClassification Report:\n" + classification_report(y_test, y_pred, target_names=["Safe", "Fire Hazard"]))
    
    weights = model.coef_[0]
    bias = model.intercept_[0]
    
    print(f"Model Learned Weights: {weights}")
    print(f"Model Learned Bias   : {bias:.6f}")
    print(f"Feature Means        : {mean}")
    print(f"Feature Stds         : {std}")
    print("=" * 60)
    
    return weights, bias, mean, std, acc


def export_c_header(weights: np.ndarray, bias: float, mean: np.ndarray, std: np.ndarray, acc: float, filepath: Path):
    """Xuất mã nguồn C header độc lập phục vụ suy luận trên ESP32-S3 (T04)."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    feature_names = ["MQ2_ADC", "TEMPERATURE", "HUMIDITY", "FLAME"]
    
    c_content = f"""/*
 * tinyml_fire_model.h
 * ====================
 * AUTOGENERATED TINYML INFERENCE ENGINE FOR ESP32-S3 (CO3054 - T04 & T05)
 * Generated by: train_tinyml.py
 * Model Type  : Standalone Logistic Regression with Z-score Standardization
 * Accuracy    : {acc * 100:.2f}%
 * Memory Footprint: ~128 bytes RAM, Zero dynamic heap allocation.
 */

#ifndef TINYML_FIRE_MODEL_H
#define TINYML_FIRE_MODEL_H

#include <math.h>

#ifdef __cplusplus
extern "C" {{
#endif

#define TINYML_NUM_FEATURES 4

// Feature normalization constants (Z-Score scaling)
static const float TINYML_MEANS[TINYML_NUM_FEATURES] = {{
    {mean[0]:.6f}f, // {feature_names[0]}
    {mean[1]:.6f}f, // {feature_names[1]}
    {mean[2]:.6f}f, // {feature_names[2]}
    {mean[3]:.6f}f  // {feature_names[3]}
}};

static const float TINYML_STDS[TINYML_NUM_FEATURES] = {{
    {std[0]:.6f}f, // {feature_names[0]}
    {std[1]:.6f}f, // {feature_names[1]}
    {std[2]:.6f}f, // {feature_names[2]}
    {std[3]:.6f}f  // {feature_names[3]}
}};

// Model Parameters (Weights & Bias)
static const float TINYML_WEIGHTS[TINYML_NUM_FEATURES] = {{
    {weights[0]:.6f}f, // Weight for {feature_names[0]}
    {weights[1]:.6f}f, // Weight for {feature_names[1]}
    {weights[2]:.6f}f, // Weight for {feature_names[2]}
    {weights[3]:.6f}f  // Weight for {feature_names[3]}
}};

static const float TINYML_BIAS = {bias:.6f}f;

/**
 * Sigmoid activation function with numerical stabilization.
 */
static inline float tinyml_sigmoid(float z) {{
    if (z > 12.0f) return 1.0f;
    if (z < -12.0f) return 0.0f;
    return 1.0f / (1.0f + expf(-z));
}}

/**
 * Predicts fire probability directly on ESP32-S3 hardware (T04 criteria).
 *
 * @param mq2_adc      Raw 12-bit ADC value from MQ-2 smoke sensor (0 - 4095)
 * @param temp_c       Temperature reading in Celsius
 * @param flame        Flame sensor binary state (0: Normal, 1: Fire detected)
 * @param humidity     Relative humidity percentage (0 - 100%)
 * @return             Fire hazard probability between 0.0f (Safe) and 1.0f (Critical Fire)
 */
static inline float tinyml_predict_fire_risk(float mq2_adc, float temp_c, float flame, float humidity) {{
    float inputs[TINYML_NUM_FEATURES] = {{ mq2_adc, temp_c, humidity, flame }};
    float z = TINYML_BIAS;

    for (int i = 0; i < TINYML_NUM_FEATURES; ++i) {{
        float scaled = (inputs[i] - TINYML_MEANS[i]) / TINYML_STDS[i];
        z += TINYML_WEIGHTS[i] * scaled;
    }}

    return tinyml_sigmoid(z);
}}

/**
 * Returns textual risk level based on inferred probability.
 */
static inline const char* tinyml_get_risk_label(float probability) {{
    if (probability >= 0.70f) {{
        return "CRITICAL";
    }} else if (probability >= 0.40f) {{
        return "WARNING";
    }} else {{
        return "SAFE";
    }}
}}

#ifdef __cplusplus
}}
#endif

#endif // TINYML_FIRE_MODEL_H
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(c_content)
    
    print(f"\n[OK] Successfully exported TinyML C header to:\n     -> {filepath.resolve()}\n")


def main():
    print("Collecting and synthesizing sensor domain dataset...")
    X, y = generate_synthetic_dataset(num_samples=2500)
    
    print("Training TinyML Logistic Regression classifier...")
    weights, bias, mean, std, acc = train_model(X, y)
    
    print("Exporting model to standalone C header for ESP32-S3...")
    export_c_header(weights, bias, mean, std, acc, HEADER_OUTPUT_PATH)
    print("T05 Model Training & Export pipeline completed successfully!")


if __name__ == "__main__":
    main()
