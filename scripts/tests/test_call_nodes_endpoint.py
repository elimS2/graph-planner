import json
import os
import sys
from urllib import request, error


def main() -> dict:
    base_url = os.environ.get("GT_BASE_URL", "http://127.0.0.1:5050")
    project_id = os.environ.get("GT_PROJECT_ID", "220aee43-ba07-4862-ab5d-b68743026cd6")
    url = f"{base_url}/api/v1/projects/{project_id}/nodes"
    try:
        with request.urlopen(url, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {"raw": body}
            result = {
                "ok": True,
                "status": resp.status,
                "url": url,
                "data_sample": data.get("data")[:3] if isinstance(data, dict) and isinstance(data.get("data"), list) else None,
            }
    except error.HTTPError as e:
        result = {"ok": False, "status": e.code, "url": url, "error": e.reason}
    except Exception as e:  # noqa: BLE001
        result = {"ok": False, "status": None, "url": url, "error": str(e)}

    out_dir = os.path.join("scripts", "tests")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "json-result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


if __name__ == "__main__":
    res = main()
    # Print compact JSON to stdout as well
    sys.stdout.write(json.dumps(res, ensure_ascii=False))
    sys.stdout.flush()


