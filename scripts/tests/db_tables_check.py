from __future__ import annotations

import json
from pathlib import Path
import sqlite3


def load_env(root: Path) -> dict[str, str]:
    env_path = root / ".env"
    out: dict[str, str] = {}
    try:
        if env_path.exists():
            for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    out[k.strip()] = v.strip()
    except Exception:
        pass
    return out


def guess_sqlite_path(root: Path, envv: dict[str, str]) -> Path:
    db_url = envv.get('DATABASE_URL', '')
    if db_url.startswith('sqlite:///'):
        return Path(db_url.split('///', 1)[-1])
    # fallback to instance/graph_tracker.db or project root
    inst = root / 'instance' / 'graph_tracker.db'
    if inst.exists():
        return inst
    return root / 'graph_tracker.db'


def list_tables(sqlite_path: Path) -> list[str]:
    try:
        con = sqlite3.connect(str(sqlite_path))
        try:
            cur = con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            rows = cur.fetchall()
            return [r[0] for r in rows]
        finally:
            con.close()
    except Exception:
        return []


def ensure_out(root: Path) -> Path:
    out = root / 'scripts' / 'tests' / 'json-result.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    envv = load_env(root)
    sqlite_path = guess_sqlite_path(root, envv)
    tables = list_tables(sqlite_path)
    has_attachment = 'attachment' in tables
    has_comment_attachment = 'comment_attachment' in tables
    result = {
        'db': str(sqlite_path),
        'tables': tables,
        'checks': {
            'attachment_exists': has_attachment,
            'comment_attachment_exists': has_comment_attachment,
        }
    }
    out = ensure_out(root)
    try:
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()


