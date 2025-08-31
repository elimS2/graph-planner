from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    last = root / "scripts" / "tests" / "json-result.json"
    try:
        js = json.loads(last.read_text(encoding="utf-8"))
    except Exception:
        js = {}
    node_id = js.get("node_id")

    db_uri = os.getenv("DATABASE_URL", "")
    if db_uri.startswith("sqlite"):
        db_path = db_uri.split("///", 1)[-1]
        db_file = Path(db_path if os.path.isabs(db_path) else (root / db_path))
    else:
        inst = root / "instance" / "graph_tracker.db"
        db_file = inst if inst.exists() else (root / "graph_tracker.db")

    out: Dict[str, Any] = {"action": "dump_status_changes", "db": str(db_file), "node_id": node_id}
    try:
        con = sqlite3.connect(str(db_file))
        try:
            rows: List[Tuple[str, str, str, str]] = []
            for r in con.execute(
                "SELECT id, node_id, old_status, new_status FROM status_change ORDER BY rowid DESC LIMIT 20"
            ):
                rows.append(tuple(map(str, r)))
            out["rows"] = rows
            by_node: List[Tuple[str, str, str, str]] = []
            if node_id:
                for r in con.execute(
                    "SELECT id, node_id, old_status, new_status FROM status_change WHERE node_id = ? ORDER BY rowid DESC LIMIT 20",
                    (str(node_id),),
                ):
                    by_node.append(tuple(map(str, r)))
            out["rows_for_node"] = by_node
            out["ok"] = True
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


