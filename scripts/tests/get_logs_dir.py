from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def load_dotenv_values(root: Path) -> Dict[str, str]:
    env_path = root / ".env"
    values: Dict[str, str] = {}
    try:
        if env_path.exists():
            for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip()
    except Exception:
        pass
    return values


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    env_values = load_dotenv_values(root)
    logs_dir = env_values.get("LOGS_DIR", "logs")
    p = Path(logs_dir)
    abs_path = str(p.resolve())
    exists = p.exists()
    is_dir = p.is_dir() if exists else False

    result: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "env": {"LOGS_DIR": logs_dir},
        "path": {"abs": abs_path, "exists": exists, "is_dir": is_dir},
    }

    # Best-effort: list a few *.log files if directory exists
    if is_dir:
        try:
            files = sorted(p.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
            result["logs"] = [
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "mtime_iso": datetime.utcfromtimestamp(f.stat().st_mtime).isoformat() + "Z",
                }
                for f in files[:10]
            ]
        except Exception as e:
            result["logs_error"] = str(e)

    # Save JSON to scripts/tests/json-result.json
    out_path = Path("scripts/tests/json-result.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # Also print to stdout
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()


