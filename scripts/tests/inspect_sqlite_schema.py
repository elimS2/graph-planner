import json
import os
import sqlite3
from pathlib import Path


def describe_table(db_path: str, table: str) -> dict:
    info = {"table": table, "columns": [], "exists": False}
    if not os.path.exists(db_path):
        return {"error": f"db not found: {db_path}"}
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # Check table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        row = cur.fetchone()
        if not row:
            info["exists"] = False
            return info
        info["exists"] = True
        cur.execute(f"PRAGMA table_info({table})")
        cols = cur.fetchall()
        for cid, name, ctype, notnull, dflt_value, pk in cols:
            info["columns"].append({
                "cid": cid,
                "name": name,
                "type": ctype,
                "notnull": bool(notnull),
                "default": dflt_value,
                "pk": bool(pk),
            })
        return info
    finally:
        conn.close()


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    db_path = os.environ.get("GT_DB_PATH", str(root / "instance" / "graph_tracker.db"))
    report = {
        "db_path": db_path,
        "node": describe_table(db_path, "node"),
        "alembic_version": describe_table(db_path, "alembic_version"),
    }
    out_dir = root / "scripts" / "tests"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "json-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


