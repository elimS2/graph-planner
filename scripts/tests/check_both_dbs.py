from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict


def list_tables(db_path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"db_path": str(db_path)}
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = sorted([r[0] for r in cur.fetchall()])
            out["ok"] = True
            out["tables"] = tables
            out["has_status_change"] = ("status_change" in set(tables))
        finally:
            conn.close()
    except Exception as e:
        out["ok"] = False
        out["error"] = str(e)
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    primary = root / "graph_tracker.db"
    secondary = root / "instance" / "graph_tracker.db"
    result: Dict[str, Any] = {
        "action": "check_both_dbs",
        "primary": str(primary),
        "secondary": str(secondary),
        "env_DATABASE_URL": os.getenv("DATABASE_URL", "")
    }
    checks = []
    if primary.exists():
        checks.append(list_tables(primary))
    else:
        checks.append({"db_path": str(primary), "ok": False, "error": "missing"})
    if secondary.exists():
        checks.append(list_tables(secondary))
    else:
        checks.append({"db_path": str(secondary), "ok": False, "error": "missing"})
    result["checks"] = checks
    out_path = root / "scripts" / "tests" / "json-result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    # success exit even if one missing; we just report
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


