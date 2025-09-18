from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

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


def make_zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("hello.txt", "hello")
    return buf.getvalue()


def make_doc_bytes() -> bytes:
    # Minimal fake DOC is not trivial. We'll send as generic bytes; browsers often set correct MIME by extension.
    return b"DOCTEST" * 10


def make_docx_bytes() -> bytes:
    # DOCX is a zip container. We'll create a minimal zip with required [Content_Types].xml entry name only for test.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"></Types>")
    return buf.getvalue()


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    envv = load_env(root)
    base_url = envv.get("BASE_URL") or f"http://{envv.get('HOST','127.0.0.1')}:{envv.get('PORT','5050')}"

    s = requests.Session()
    result: Dict[str, Any] = {"base_url": base_url, "tests": []}

    def run_upload(name: str, content: bytes, mime: str) -> Tuple[int, Any]:
        files = {"file": (name, io.BytesIO(content), mime)}
        r = s.post(f"{base_url}/api/v1/attachments", files=files, timeout=20)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text

    tests: List[Tuple[str, bytes, str]] = [
        ("sample.zip", make_zip_bytes(), "application/zip"),
        ("sample.doc", make_doc_bytes(), "application/msword"),
        ("sample.docx", make_docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ]

    for (name, data, mime) in tests:
        status, payload = run_upload(name, data, mime)
        result["tests"].append({
            "name": name,
            "mime": mime,
            "status": status,
            "response": payload,
        })

    out = ensure_out(root)
    try:
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()


