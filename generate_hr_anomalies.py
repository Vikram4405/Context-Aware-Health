"""
Generate synthetic heart-rate anomaly samples for Edge Impulse K-means testing.

Reads normal export stats, writes an importable zip to the Desktop.
"""

from __future__ import annotations

import json
import random
import statistics
import zipfile
from pathlib import Path

NORMAL_EXPORT = Path(r"C:\Users\HP\Downloads\fossil-hr-export-temp\training")
OUTPUT_DIR = Path(r"C:\Users\HP\Desktop\fossil-hr-synthetic-anomalies")
OUTPUT_ZIP = Path(r"C:\Users\HP\Desktop\fossil-hr-synthetic-anomalies.zip")

INTERVAL_MS = 1000
SAMPLES_PER_WINDOW = 30
SEED = 42


def load_normal_stats() -> tuple[int, float, float]:
    lengths: list[int] = []
    bpms: list[float] = []
    for path in NORMAL_EXPORT.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        values = [row[0] for row in data["payload"]["values"] if row[0] > 0]
        if values:
            lengths.append(len(data["payload"]["values"]))
            bpms.extend(values)
    window = int(statistics.median(lengths)) if lengths else SAMPLES_PER_WINDOW
    return window, min(bpms), max(bpms)


def clamp_bpm(value: float, low: int = 35, high: int = 200) -> int:
    return int(max(low, min(high, round(value))))


def smooth(values: list[float], start: float, end: float) -> list[int]:
    n = len(values)
    if n <= 1:
        return [clamp_bpm(start)]
    out: list[int] = []
    for i in range(n):
        t = i / (n - 1)
        target = start + (end - start) * t
        noisy = target + random.uniform(-2, 2)
        out.append(clamp_bpm(noisy))
    return out


def generate_tachycardia(length: int, baseline: float) -> list[int]:
    """Resting baseline, rapid rise, sustained high HR."""
    phase1 = max(4, length // 5)
    phase2 = max(6, length // 4)
    phase3 = length - phase1 - phase2

    peak = random.uniform(145, 175)
    series: list[int] = []
    series.extend(smooth([0] * phase1, baseline, baseline + random.uniform(8, 15)))
    series.extend(smooth([0] * phase2, series[-1], peak))
    series.extend(
        [clamp_bpm(peak + random.uniform(-4, 4)) for _ in range(phase3)]
    )
    return series[:length]


def generate_bradycardia(length: int, baseline: float) -> list[int]:
    """Normal start, gradual drop, sustained low HR."""
    phase1 = max(5, length // 4)
    phase2 = max(6, length // 4)
    phase3 = length - phase1 - phase2

    low = random.uniform(38, 48)
    series: list[int] = []
    series.extend(smooth([0] * phase1, baseline, baseline))
    series.extend(smooth([0] * phase2, baseline, low))
    series.extend([clamp_bpm(low + random.uniform(-2, 2)) for _ in range(phase3)])
    return series[:length]


def generate_irregular(length: int, baseline: float) -> list[int]:
    """Mostly normal with sudden spikes and drops (arrhythmia-like)."""
    series = [clamp_bpm(baseline + random.uniform(-5, 5)) for _ in range(length)]
    spike_count = random.randint(3, 6)
    for _ in range(spike_count):
        idx = random.randint(2, length - 3)
        pattern = random.choice(["spike", "drop", "flutter"])
        if pattern == "spike":
            series[idx] = clamp_bpm(random.uniform(130, 165))
            if idx + 1 < length:
                series[idx + 1] = clamp_bpm(series[idx] - random.uniform(10, 25))
        elif pattern == "drop":
            series[idx] = clamp_bpm(random.uniform(42, 55))
            if idx + 1 < length:
                series[idx + 1] = clamp_bpm(series[idx] + random.uniform(8, 20))
        else:
            for j in range(idx, min(idx + 4, length)):
                series[j] = clamp_bpm(baseline + random.choice([-1, 1]) * random.uniform(20, 35))
    return series


def build_payload(values: list[int], timestamp_ms: int) -> dict:
    return {
        "protected": {
            "ver": "v1",
            "alg": "none",
            "iat": timestamp_ms // 1000,
        },
        "signature": "0" * 64,
        "payload": {
            "device_name": "fossil-gen6-synthetic",
            "device_type": "FOSSIL_GEN6",
            "interval_ms": INTERVAL_MS,
            "sensors": [{"name": "bpm", "units": "bpm"}],
            "values": [[bpm] for bpm in values],
        },
    }


def main() -> None:
    random.seed(SEED)
    window, normal_min, normal_max = load_normal_stats()
    baseline = statistics.mean([normal_min, normal_max])

    generators = [
        ("tachycardia", generate_tachycardia, 8),
        ("bradycardia", generate_bradycardia, 8),
        ("irregular", generate_irregular, 8),
    ]

    testing_dir = OUTPUT_DIR / "testing"
    testing_dir.mkdir(parents=True, exist_ok=True)

    label_files: list[dict] = []
    timestamp_base = 1_800_000_000_000

    for kind, generator, count in generators:
        for i in range(1, count + 1):
            ts = timestamp_base + len(label_files)
            values = generator(window, baseline)
            filename = f"Anomaly.Anomaly_{kind}_{i:02d}.json.synthetic.json"
            rel_path = f"testing/{filename}"
            file_path = testing_dir / filename
            file_path.write_text(
                json.dumps(build_payload(values, ts), separators=(",", ":")),
                encoding="utf-8",
            )
            label_files.append(
                {
                    "path": rel_path,
                    "name": f"Anomaly_{kind}_{i:02d}.synthetic",
                    "category": "testing",
                    "label": {"type": "label", "label": "anomaly"},
                }
            )

    info = {"version": 1, "files": label_files}
    info_text = json.dumps(info, separators=(",", ":"))
    (OUTPUT_DIR / "info.labels").write_text(info_text, encoding="utf-8")
    (testing_dir / "info.labels").write_text(info_text, encoding="utf-8")
    (OUTPUT_DIR / "README.txt").write_text(
        "# Synthetic HR anomaly samples for fossil-hr-activity\n\n"
        "Generated from your normal watch recordings.\n\n"
        "Types included:\n"
        "- tachycardia (8 samples): sustained high heart rate\n"
        "- bradycardia (8 samples): sustained low heart rate\n"
        "- irregular (8 samples): sudden spikes and drops\n\n"
        "Import into Edge Impulse:\n"
        "1. Data acquisition > Upload data\n"
        "2. Or: edge-impulse-uploader --info-file info.labels\n\n"
        "These are in the TESTING set with label `anomaly`.\n"
        "Keep your real `Normal` data in training only.\n",
        encoding="utf-8",
    )

    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in OUTPUT_DIR.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(OUTPUT_DIR).as_posix())

    print(f"Normal BPM range used as reference: {normal_min:.0f}-{normal_max:.0f}")
    print(f"Generated {len(label_files)} anomaly samples ({window} readings each)")
    print(f"Folder: {OUTPUT_DIR}")
    print(f"Zip:    {OUTPUT_ZIP}")


if __name__ == "__main__":
    main()
