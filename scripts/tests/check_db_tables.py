from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    # Determine DB path similarly to app.config default
    db_uri = os.getenv("DATABASE_URL", "sqlite:///graph_tracker.db")
    if not db_uri.startswith("sqlite"):
        out = {"action": "check_db_tables", "error": "Non-sqlite DB not supported in this check", "db_uri": db_uri}
        (root / "scripts" / "tests" / "json-result.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(out, ensure_ascii=False))
        return 2
    path = db_uri.split("///", 1)[-1]
    # Fallback to instance/ path if root file missing
    db_path = Path(path)
    if not db_path.is_absolute():
        db_path = root / path
    if not db_path.exists():
        alt = root / "instance" / Path(path).name
        if alt.exists():
            db_path = alt

    result: Dict[str, Any] = {"action": "check_db_tables", "db_path": str(db_path)}
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = sorted([r[0] for r in cur.fetchall()])
            result["ok"] = True
            result["tables"] = tables
            result["has_status_change"] = ("status_change" in set(tables))
        finally:
            conn.close()
    except Exception as e:
        result["ok"] = False
        result["error"] = str(e)

    out_path = root / "scripts" / "tests" / "json-result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())


