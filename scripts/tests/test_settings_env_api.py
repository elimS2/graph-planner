from __future__ import annotations

import json
import os
from pathlib import Path

from app import create_app


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    out_dir = root / "scripts" / "tests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "json-result.json"

    # Force testing config to pass gating
    os.environ["FLASK_ENV"] = "testing"
    app = create_app("testing")
    app.config.update(TESTING=True)

    with app.test_client() as c:
        resp = c.get("/api/v1/settings/env")
        try:
            payload = resp.get_json(force=True)
        except Exception:
            payload = {"errors": [{"status": resp.status_code}]}

    out = {
        "status": resp.status_code,
        "has_data": bool(payload and payload.get("data")),
        "meta": payload.get("meta", {}) if isinstance(payload, dict) else {},
    }
    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


