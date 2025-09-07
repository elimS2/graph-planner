from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import base64
import io
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


def ensure_out_path(root: Path) -> Path:
    out_dir = root / "scripts" / "tests"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "json-result.json"


def tiny_png_bytes() -> bytes:
    # 1x1 transparent PNG
    b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAuMB9yQj7U4AAAAASUVORK5CYII="
    )
    return base64.b64decode(b64)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    envv = load_env(root)
    base_url = envv.get("BASE_URL") or f"http://{envv.get('HOST','127.0.0.1')}:{envv.get('PORT','5050')}"

    result: Dict[str, Any] = {
        "base_url": base_url,
        "steps": [],
    }

    try:
        # Prepare multipart upload
        png = tiny_png_bytes()
        files = {"file": ("tiny.png", io.BytesIO(png), "image/png")}
        r = requests.post(f"{base_url}/api/v1/attachments", files=files, timeout=15)
        try:
            payload = r.json()
        except Exception:
            payload = {"raw": r.text}
        result["steps"].append({
            "action": "upload_attachment",
            "status_code": r.status_code,
            "response": payload,
        })

        if r.ok and isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            att = payload["data"]
            url = att.get("url")
            if url:
                gr = requests.get(f"{base_url}{url}", timeout=15)
                result["steps"].append({
                    "action": "get_file",
                    "status_code": gr.status_code,
                    "content_type": gr.headers.get("Content-Type"),
                    "ok": gr.ok,
                    "size": len(gr.content),
                })
    except Exception as e:
        result["error"] = str(e)

    out_path = ensure_out_path(root)
    try:
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()


