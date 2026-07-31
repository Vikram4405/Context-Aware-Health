# Context Aware Health

**On-device health monitoring for Wear OS** — fall detection and heart rate anomaly alerts running entirely on a Fossil Gen 6 smartwatch, powered by Edge Impulse machine learning.

This project is a full wearable health stack: collect labeled sensor data from the wrist, train ML models in Edge Impulse, deploy them as native C++ libraries on the watch, and send caregiver alerts over Wi‑Fi when something looks wrong. No cloud inference required at runtime.

**Hardware tested:** Fossil Gen 6 · Wear OS · ARM (arm64-v8a / armeabi-v7a)

---

## Why "Context Aware"?

The watch doesn't just read raw numbers — it understands **context**:

| Signal | What the watch knows | What triggers an alert |
|--------|----------------------|------------------------|
| **Motion context** | Gravity vector at 50 Hz over 1.5 seconds | Fall-like impact + orientation change + ML confidence |
| **Physiological context** | BPM pattern over 30 seconds | Deviation from learned "normal" baseline (K-means anomaly) |
| **Connectivity context** | Wi‑Fi available or not | Alert only sent when network is reachable |

Two models run in parallel inside a foreground monitoring service. Each uses post-ML gating (impact detection, consecutive confirmation, cooldowns) so normal daily activity doesn't spam false alarms.

---

## Features

- **Fall detection** — Gravity sensor → spectral neural network → email alert
- **Heart rate anomaly detection** — BPM time series → K-means anomaly score → email alert
- **Live monitoring UI** — On-watch Fall % / Normal % scores while monitoring
- **Data collection mode** — Record labeled sessions and upload directly to Edge Impulse for retraining
- **Email alerts** — Wi‑Fi email to caregiver (no phone companion required)
- **On-device inference** — Edge Impulse C++ MCU libraries via Android NDK (INT8 quantized)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Fossil Gen 6 Watch                        │
├──────────────────────────────────────────────────────────────┤
│  Gravity (50 Hz) ──► libei_fall.so ──► Fall decision logic   │
│  Heart Rate (1 Hz) ──► libei_hr.so  ──► HR anomaly logic     │
│                              │                                │
│                    MonitoringService (foreground)             │
│                              │                                │
│                    PhoneAlertSender (Wi‑Fi email)             │
└──────────────────────────────────────────────────────────────┘
         ▲                                    │
         │ training data                      ▼
   Edge Impulse Cloud                   Caregiver Gmail
   (ingestion API)                     notification
```

### Modules

| Module | Purpose |
|--------|---------|
| `:app` | Watch app — data collector + health monitor + native ML |
| `:phone` | Optional Android phone companion (Wearable Data Layer listener) |

---

## ML Models

### 1. Fall Detection (`fossil-fall-detection`)

| | |
|---|---|
| **Type** | Supervised binary classifier |
| **Labels** | `Fall` · `Non-Fall` |
| **Input** | 75 samples × gravX/Y/Z @ **50 Hz** (1.5 seconds) |
| **Pipeline** | Spectral Analysis (FFT) → 39 features → INT8 neural network |
| **Output** | P(Fall), P(Non-Fall) |
| **Accuracy** | ~90% on Edge Impulse test set |

**Post-ML gating (reduces false alarms):**
- Impact / orientation change must be present
- Inference every 0.5 s (not every sample)
- 2 consecutive high-confidence windows required
- Fall score must beat Non-Fall by 12%+
- Threshold: 72% normally, 55% on strong impact
- 2-minute cooldown between alerts

### 2. Heart Rate Anomaly (`fossil-hr-activity`)

| | |
|---|---|
| **Type** | Unsupervised K-means anomaly detection |
| **Input** | 30 BPM readings @ **1 Hz** (30 seconds) |
| **Pipeline** | Spectral Analysis → 13 features → 4-cluster K-means |
| **Output** | Anomaly score (≥ 0.5 triggers alert) |
| **Training** | 64 Normal samples + synthetic anomaly data |

The watch firmware derives BPM from the optical PPG sensor on the back of the watch. The app reads `Sensor.TYPE_HEART_RATE` — it does not process raw PPG waveforms on Fossil Gen 6.

---

## Sensors

| Sensor | Used for | Rate | Notes |
|--------|----------|------|-------|
| **Gravity** | Fall model | 50 Hz | Primary input — isolates tilt/orientation |
| **Accelerometer** | Fallback | 50 Hz | Only if gravity sensor unavailable |
| **Heart rate** | HR model | ~1 Hz | OS-processed BPM from PPG hardware |
| **Gyroscope** | Data collection | 50 Hz | Available, not in production models |

**IMU explained:** The accelerometer measures force (including gravity). The gravity sensor strips out motion so the fall model sees orientation changes cleanly. A real fall shows a sudden impact spike plus a large shift in the gravity vector direction.

**BPM explained:** Green LED on the watch back shines into the wrist → photodiode measures reflected light → blood volume changes with each heartbeat → watch firmware converts the pulsating signal to beats-per-minute → app reads one BPM value per second.

---


## Setup

### Prerequisites

- Android Studio (Ladybug+) with Wear OS support
- Android SDK 35, NDK, CMake 3.22+
- [Edge Impulse](https://studio.edgeimpulse.com) account
- Fossil Gen 6 (or compatible Wear OS watch) on Wi‑Fi for alerts

### Configure API key

```bash
cp gradle.properties.example gradle.properties
```

Edit `gradle.properties`:

```properties
EI_API_KEY=ei_your_api_key_here
```

Get your key from **Edge Impulse Studio → Dashboard → Keys**.  
Never commit `gradle.properties` — it is gitignored.

### Configure alert email

Edit `app/src/main/java/com/example/wizdatacollector/presentation/PhoneAlertSender.kt`:

```kotlin
private const val ALERT_EMAIL = "your-email@gmail.com"
```

First run: FormSubmit sends a one-time activation link to that address — click it once.

---

## Usage

### Health monitoring (launcher app)

1. Connect watch to **Wi‑Fi**
2. Open the monitor app
3. Tap **Test phone alert** — confirm email arrives
4. Tap **Start monitoring**
5. Watch live **Fall X% / Normal Y%** on screen
6. Fall or abnormal HR → email alert to caregiver

### Data collection (for retraining)

1. Select **Gravity** sensor (matches fall model)
2. Enter label: `Fall`, `Non-Fall`, `Normal`, etc.
3. Record 2–60 seconds
4. Uploads automatically to Edge Impulse

---

## Edge Impulse Integration

### Export models to watch

1. Train in [Edge Impulse Studio](https://studio.edgeimpulse.com)
2. **Deployment → C++ library (MCU)**
3. Extract into:
   - Fall → `app/src/main/cpp/ei_fall/`
   - HR → `app/src/main/cpp/ei_hr/`
4. Rebuild

---

## Tech Stack

Kotlin · Jetpack Compose · Wear OS · Android NDK · C++ · Edge Impulse · TensorFlow Lite INT8 · FormSubmit

---

## Author

**Vikramadhitya** — 2026

Built with [Edge Impulse](https://edgeimpulse.com) on a Fossil Gen 6 smartwatch.
