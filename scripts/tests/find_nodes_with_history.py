from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple


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

    out: Dict[str, Any] = {"action": "find_nodes_with_history", "db": str(db_file)}
    try:
        con = sqlite3.connect(str(db_file))
        try:
            con.row_factory = sqlite3.Row
            # Find project named 'Graph Planner'
            proj_row = con.execute(
                "SELECT id, name FROM project WHERE name LIKE ? ORDER BY name LIMIT 1",
                ("%Graph Planner%",),
            ).fetchone()
            if not proj_row:
                out["ok"] = False
                out["error"] = "project 'Graph Planner' not found"
            else:
                pid = proj_row["id"]
                out["project"] = {"id": pid, "name": proj_row["name"]}
                rows: List[sqlite3.Row] = con.execute(
                    """
                    SELECT n.id AS node_id, n.title AS title, COUNT(s.id) AS changes
                    FROM node n
                    JOIN status_change s ON s.node_id = n.id
                    WHERE n.project_id = ?
                    GROUP BY n.id, n.title
                    HAVING COUNT(s.id) > 0
                    ORDER BY changes DESC, title ASC
                    """,
                    (pid,),
                ).fetchall()
                out["ok"] = True
                out["count"] = len(rows)
                out["nodes"] = [
                    {"id": str(r["node_id"]), "title": r["title"], "changes": int(r["changes"]) }
                    for r in rows
                ]
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


