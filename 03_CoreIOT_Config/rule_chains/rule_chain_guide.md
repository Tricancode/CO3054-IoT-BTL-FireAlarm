# CoreIOT Fire Alarm Rule Chain Documentation

## Overview
This rule chain processes real-time telemetry sent by the Local Gateway to CoreIOT / ThingsBoard. It evaluates sensor values (`temperature`, `smoke_level`) and Edge TinyML Inference Flags (`tinyml_fire`) to handle native Cloud alarm creation, clearance, and timeseries persistence.

---

## Criterion Alignment
- **T09 (Cloud Rule Chain Alarm Pipeline)**: Automated rule processing, alarm state machine (`CRITICAL` / `NORMAL`), and telemetry persistence directly inside CoreIOT without external messaging dependencies.

---

## Rule Chain Architecture
