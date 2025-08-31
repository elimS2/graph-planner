from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    # Resolve DB path (prefer instance)
    db_uri = os.getenv("DATABASE_URL", "")
    if db_uri.startswith("sqlite"):
        db_path = db_uri.split("///", 1)[-1]
        db_file = Path(db_path if os.path.isabs(db_path) else (root / db_path))
    else:
        inst = root / "instance" / "graph_tracker.db"
        db_file = inst if inst.exists() else (root / "graph_tracker.db")

    out: Dict[str, Any] = {"action": "backfill_status_history", "db": str(db_file)}
    try:
        con = sqlite3.connect(str(db_file))
        try:
            con.execute("PRAGMA foreign_keys=ON")
            # Find nodes without any status_change rows
            rows = con.execute(
                """
                SELECT n.id, COALESCE(NULLIF(TRIM(n.status), ''), 'planned') as st
                FROM node n
                WHERE NOT EXISTS (SELECT 1 FROM status_change s WHERE s.node_id = n.id)
                """
            ).fetchall()
            created = 0
            for nid, st in rows:
                try:
                    con.execute(
                        "INSERT INTO status_change (id, node_id, old_status, new_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            __import__("uuid").uuid4().hex,
                            str(nid),
                            str(st),
                            str(st),
                            __import__("datetime").datetime.utcnow().isoformat() + "Z",
                            __import__("datetime").datetime.utcnow().isoformat() + "Z",
                        ),
                    )
                    created += 1
                except Exception:
                    # continue with best-effort
                    pass
            con.commit()
            out["ok"] = True
            out["created"] = created
            out["scanned"] = len(rows)
        finally:
            con.close()
    except Exception as e:
        out["ok"] = False
        out["error"] = str(e)

    out_path = root / "scripts" / "tests" / "json-result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())


