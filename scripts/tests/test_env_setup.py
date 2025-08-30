from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List


ENV_FILENAME = ".env"

# Keys we care about for translation providers
REQUIRED_KEYS_DEFAULTS: Dict[str, str] = {
    "TRANSLATION_PROVIDER": "gemini",
    "GEMINI_API_KEY": "",
    "GEMINI_MODEL": "gemini-1.5-flash",
    "DEEPL_API_KEY": "",
    "LT_API_URL": "",
    "LT_API_KEY": "",
    "TRANSLATION_BATCH_SIZE": "50",
    "TRANSLATION_TIMEOUT_MS": "60000",
    "ASYNC_WORKERS": "2",
}


def read_env_file(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def write_env_file(path: Path, kv: Dict[str, str]) -> None:
    # Preserve order for readability
    lines: List[str] = []
    for k, default in REQUIRED_KEYS_DEFAULTS.items():
        lines.append(f"{k}={kv.get(k, default)}")
    # Include any extra keys present originally
    for k, v in kv.items():
        if k not in REQUIRED_KEYS_DEFAULTS:
            lines.append(f"{k}={v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    root = Path.cwd()
    env_path = root / ENV_FILENAME
    existed = env_path.exists()
    before = read_env_file(env_path)

    merged = dict(REQUIRED_KEYS_DEFAULTS)
    merged.update(before)

    # Ensure required keys exist (keep existing values)
    changed_keys: List[str] = []
    for k, default in REQUIRED_KEYS_DEFAULTS.items():
        if k not in before:
            merged[k] = default
            changed_keys.append(k)

    # Create or update file if needed
    created = False
    updated = False
    if not existed:
        write_env_file(env_path, merged)
        created = True
    elif changed_keys:
        write_env_file(env_path, merged)
        updated = True

    # Prepare safe preview (mask secrets)
    preview = {k: ("***" if k.endswith("_KEY") else merged.get(k, "")) for k in REQUIRED_KEYS_DEFAULTS.keys()}

    has_values = {k: bool((merged.get(k, "") or "").strip()) for k in REQUIRED_KEYS_DEFAULTS.keys() if k.endswith("_KEY")}

    out = {
        "env_path": str(env_path),
        "existed": existed,
        "created": created,
        "updated": updated,
        "added_keys": changed_keys,
        "preview": preview,
        "has_values": has_values,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()


