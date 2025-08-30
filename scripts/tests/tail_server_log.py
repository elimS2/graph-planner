from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


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


def tail_latest_server_log(root: Path, n: int = 200) -> Dict[str, Any]:
    envv = load_dotenv_values(root)
    logs_dir = envv.get("LOGS_DIR", "logs")
    log_dir = Path(logs_dir) if Path(logs_dir).is_absolute() else (root / logs_dir)
    out: Dict[str, Any] = {
        "logs_dir": str(log_dir.resolve()),
        "file": None,
        "lines": [],
        "gemini": [],
    }
    try:
        files = sorted(log_dir.glob("server-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return out
        latest = files[0]
        out["file"] = latest.name
        lines = latest.read_text(encoding="utf-8", errors="ignore").splitlines()
        tail = lines[-n:]
        out["lines"] = tail
        out["gemini"] = [ln for ln in tail if "provider=gemini" in ln]
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    data = tail_latest_server_log(root, n=300)
    data["timestamp"] = datetime.utcnow().isoformat() + "Z"
    out_path = root / "scripts" / "tests" / "json-result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()


