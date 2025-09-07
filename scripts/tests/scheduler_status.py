from __future__ import annotations

import json
from pathlib import Path

from app import create_app


def main() -> dict:
    app = create_app()
    with app.test_client() as client:
        status = client.get('/api/v1/settings/scheduler').get_json(silent=True)
        run_now = client.post('/api/v1/settings/scheduler/backup/run').get_json(silent=True)
        return {
            "scheduler_status": status,
            "run_now": run_now,
        }


if __name__ == '__main__':
    out = main()
    out_dir = Path('scripts/tests')
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'json-result.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out))


