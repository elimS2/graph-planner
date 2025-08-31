from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    # Read last json-result to get node_id
    last = root / "scripts" / "tests" / "json-result.json"
    node_id = None
    try:
        js = json.loads(last.read_text(encoding="utf-8"))
        node_id = js.get("node_id") or (js.get("data", {}) if isinstance(js.get("data"), dict) else {}).get("node_id")
    except Exception:
        pass

    # Resolve DB path (prefer instance)
    db_uri = os.getenv("DATABASE_URL", "")
    if db_uri.startswith("sqlite"):
        db_path = db_uri.split("///", 1)[-1]
        db_file = Path(db_path if os.path.isabs(db_path) else (root / db_path))
    else:
        inst = root / "instance" / "graph_tracker.db"
        db_file = inst if inst.exists() else (root / "graph_tracker.db")

    out: Dict[str, Any] = {"action": "check_status_rows", "db": str(db_file), "node_id": node_id}
    try:
        con = sqlite3.connect(str(db_file))
        try:
            cur = con.execute("SELECT COUNT(*) FROM status_change WHERE node_id = ?", (str(node_id or ""),))
            cnt = int(cur.fetchone()[0])
            out["ok"] = True
            out["count"] = cnt
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


