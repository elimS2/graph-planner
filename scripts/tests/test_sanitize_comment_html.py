from __future__ import annotations

import json
import os
from typing import Any, Dict

from app.utils.sanitize import sanitize_comment_html


def run() -> Dict[str, Any]:
    cases = {
        "plain": "Hello <b>world</b>",
        "script": "<p>Hi</p><script>alert(1)</script>",
        "link": '<a href="javascript:alert(1)">bad</a> <a href="https://ok">ok</a>',
        "headers": "<h1>T</h1><h4>small</h4>",
        "blockquote": "<blockquote>q</blockquote>",
    }
    results: Dict[str, Any] = {}
    for k, v in cases.items():
        results[k] = sanitize_comment_html(v)
    return {"results": results}


if __name__ == "__main__":
    out = run()
    os.makedirs(os.path.join("scripts", "tests"), exist_ok=True)
    out_path = os.path.join("scripts", "tests", "json-result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out))


