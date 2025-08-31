from __future__ import annotations

from pathlib import Path
from typing import Dict


def read_dotenv_values(root: Path) -> Dict[str, str]:
    """Read key=value pairs from a .env file at the given root.

    - Ignores empty lines and lines starting with '#'.
    - Splits on the first '=' only.
    - Trims surrounding whitespace for keys and values.
    - Returns an empty dict if file does not exist or on safe failure.
    """
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
                    key = k.strip()
                    val = v.strip()
                    if key:
                        values[key] = val
    except Exception:
        # Fail-safe: return what we have (possibly empty)
        return values
    return values


SENSITIVE_KEYS = (
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PWD",
    "KEY",
    "AUTH",
    "BEARER",
)


def is_sensitive_key(key: str) -> bool:
    """Heuristic to classify sensitive keys by substring match (case-insensitive)."""
    k = key.upper()
    return any(s in k for s in SENSITIVE_KEYS)


def mask_value(value: str, visible: int = 2) -> str:
    """Mask the value leaving a small prefix/suffix visible.

    If value length <= visible*2, returns a fixed number of bullets.
    """
    n = len(value or "")
    if n <= max(1, visible * 2):
        return "•" * min(8, max(4, n))
    return f"{value[:visible]}{'•' * 6}{value[-visible:]}"


