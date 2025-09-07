from __future__ import annotations

import json
from pathlib import Path

from app import create_app


def main() -> dict:
    app = create_app()
    with app.test_client() as client:
        resp = client.post('/api/v1/settings/backup-db')
        try:
            payload = resp.get_json(force=True, silent=True)
        except Exception:
            payload = None
        result = {
            "status": resp.status_code,
            "ok": True if payload and isinstance(payload, dict) and payload.get('data') else False,
            "payload": payload,
        }
    return result


if __name__ == "__main__":
    out = main()
    out_dir = Path('scripts/tests')
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'json-result.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out))


