from __future__ import annotations

import json
from pathlib import Path

import requests


def main() -> int:
    base = "http://127.0.0.1:5050"
    results = {}
    try:
        r1 = requests.patch(f"{base}/api/v1/comments/test", json={"body": "x"})
        results["patch_status"] = r1.status_code
        try:
            results["patch_json"] = r1.json()
        except Exception:
            results["patch_text"] = r1.text
    except Exception as e:
        results["patch_error"] = str(e)

    try:
        r2 = requests.delete(f"{base}/api/v1/comments/test")
        results["delete_status"] = r2.status_code
        try:
            results["delete_json"] = r2.json()
        except Exception:
            results["delete_text"] = r2.text
    except Exception as e:
        results["delete_error"] = str(e)

    out_dir = Path(__file__).resolve().parents[1] / "tests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "json-result.json"
    out_path.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


