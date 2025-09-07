from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any, Dict

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

    result: Dict[str, Any] = {"base_url": base_url, "login": {}, "upload": {}}

    s = requests.Session()
    try:
        r = s.post(f"{base_url}/api/v1/auth/login", json={"email":"demo@example.com","password":"demo1234"}, timeout=10)
        try:
            result["login"] = {"status": r.status_code, "json": r.json()}
        except Exception:
            result["login"] = {"status": r.status_code, "text": r.text}
    except Exception as e:
        result["login"] = {"error": str(e)}

    try:
        # Prepare tiny PNG
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAuMB9yQj7U4AAAAASUVORK5CYII=")
        files = {"file": ("tiny.png", io.BytesIO(png), "image/png")}
        ur = s.post(f"{base_url}/api/v1/attachments", files=files, timeout=15)
        try:
            result["upload"] = {"status": ur.status_code, "json": ur.json()}
        except Exception:
            result["upload"] = {"status": ur.status_code, "text": ur.text}
    except Exception as e:
        result["upload"] = {"error": str(e)}

    out = ensure_out(root)
    try:
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()


