from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any

import requests


def load_env(root: Path) -> Dict[str, str]:
    env_path = root / ".env"
    values: Dict[str, str] = {}
    try:
        if env_path.exists():
            for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip()
    except Exception:
        pass
    return values


def ensure_out(root: Path) -> Path:
    out = root / "scripts" / "tests" / "json-result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    envv = load_env(root)
    base_url = envv.get("BASE_URL") or f"http://{envv.get('HOST','127.0.0.1')}:{envv.get('PORT','5050')}"
    result: Dict[str, Any] = {"base_url": base_url, "restart": {}, "health": []}

    try:
        r = requests.post(f"{base_url}/api/v1/settings/restart", timeout=10)
        try:
            result["restart"] = r.json()
        except Exception:
            result["restart"] = {"status_code": r.status_code, "text": r.text}
    except Exception as e:
        result["restart"] = {"error": str(e)}

    # Poll health
    deadline = time.time() + 20
    last = None
    while time.time() < deadline:
        try:
            hr = requests.get(f"{base_url}/api/v1/health", timeout=3)
            last = {"status": hr.status_code, "ok": hr.ok}
            try:
                last["json"] = hr.json()
            except Exception:
                last["text"] = hr.text
            result["health"].append(last)
            if hr.ok:
                break
        except Exception as e:
            last = {"error": str(e)}
            result["health"].append(last)
        time.sleep(1.0)

    out = ensure_out(root)
    try:
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()


