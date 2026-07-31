"""Upload synthetic HR anomaly samples to Edge Impulse testing set."""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

API_KEY = "ei_f50e22f713b0ba29502c2a46dbabc5908bbaa526606840d5"
UPLOAD_URL = "https://ingestion.edgeimpulse.com/api/testing/data"
LABEL = "anomaly"
SAMPLES_DIR = Path(r"C:\Users\HP\Desktop\fossil-hr-synthetic-anomalies\testing")


def upload_sample(path: Path) -> tuple[bool, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    payload = data["payload"]
    payload["device_name"] = "fossil-gen6"
    payload["device_type"] = "FOSSIL_GEN6"

    body = json.dumps(
        {
            "protected": data["protected"],
            "signature": data["signature"],
            "payload": payload,
        },
        separators=(",", ":"),
    ).encode("utf-8")

    req = urllib.request.Request(
        UPLOAD_URL,
        data=body,
        method="POST",
        headers={
            "x-api-key": API_KEY,
            "x-label": LABEL,
            "x-file-name": f"anomaly_{path.stem}_{int(time.time() * 1000)}.json",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            code = resp.getcode()
            text = resp.read().decode("utf-8", errors="replace")
            return 200 <= code <= 201, f"HTTP {code}: {text[:200]}"
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        return False, f"HTTP {e.code}: {err[:300]}"
    except Exception as e:
        return False, str(e)


def main() -> None:
    files = sorted(SAMPLES_DIR.glob("Anomaly*.json"))
    if not files:
        raise SystemExit(f"No samples found in {SAMPLES_DIR}")

    ok_count = 0
    fail_count = 0
    for i, path in enumerate(files, 1):
        ok, msg = upload_sample(path)
        status = "OK" if ok else "FAIL"
        print(f"[{i}/{len(files)}] {status} {path.name}: {msg}")
        if ok:
            ok_count += 1
        else:
            fail_count += 1
        time.sleep(0.3)

    print(f"\nDone: {ok_count} uploaded, {fail_count} failed (label={LABEL}, testing set)")


if __name__ == "__main__":
    main()
