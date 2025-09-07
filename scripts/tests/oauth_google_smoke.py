import json
import os


def main():
    result = {
        "has_client_id": bool(os.getenv("GOOGLE_OAUTH_CLIENT_ID")),
        "has_client_secret": bool(os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")),
        "has_redirect_uri": bool(os.getenv("GOOGLE_OAUTH_REDIRECT_URI")),
        "scopes_default": os.getenv("GOOGLE_OAUTH_SCOPES", "openid email profile"),
    }
    out_path = os.path.join("scripts", "tests", "json-result.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    print(json.dumps(result))


if __name__ == "__main__":
    main()


