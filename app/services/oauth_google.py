from __future__ import annotations

import json
import secrets
import time
from typing import Any, Dict, Optional, Tuple

import requests
from flask import current_app, url_for, session
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token


GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URI = "https://openidconnect.googleapis.com/v1/userinfo"


def _get_cfg(key: str, default: Optional[str] = None) -> Optional[str]:
    return current_app.config.get(key, default)


def build_auth_url() -> Tuple[str, str]:
    client_id = _get_cfg("GOOGLE_OAUTH_CLIENT_ID")
    redirect_uri = _get_cfg("GOOGLE_OAUTH_REDIRECT_URI")
    scopes = (_get_cfg("GOOGLE_OAUTH_SCOPES") or "openid email profile").split()
    hd = _get_cfg("GOOGLE_OAUTH_HD")
    if not client_id or not redirect_uri:
        raise RuntimeError("Google OAuth is not configured")
    state = secrets.token_urlsafe(24)
    session['oauth_google_state'] = state
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(scopes),
        'access_type': 'online',
        'include_granted_scopes': 'true',
        'state': state,
        'prompt': 'consent',
    }
    if hd:
        params['hd'] = hd
    from urllib.parse import urlencode
    return f"{GOOGLE_AUTH_URI}?{urlencode(params)}", state


def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    client_id = _get_cfg("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = _get_cfg("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect_uri = _get_cfg("GOOGLE_OAUTH_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        raise RuntimeError("Google OAuth is not configured")
    data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }
    r = requests.post(GOOGLE_TOKEN_URI, data=data, timeout=15)
    r.raise_for_status()
    return r.json()


def verify_id_token(id_token: str) -> Dict[str, Any]:
    client_id = _get_cfg("GOOGLE_OAUTH_CLIENT_ID")
    if not client_id:
        raise RuntimeError("Google OAuth is not configured")
    request = google_requests.Request()
    payload = google_id_token.verify_oauth2_token(id_token, request, client_id)
    # Minimal checks
    if not payload.get('email') or not payload.get('email_verified'):
        raise ValueError('Email not present or not verified')
    return payload


def fetch_userinfo(access_token: str) -> Dict[str, Any]:
    h = { 'Authorization': f'Bearer {access_token}' }
    r = requests.get(GOOGLE_USERINFO_URI, headers=h, timeout=15)
    r.raise_for_status()
    return r.json()


def normalize_profile(idinfo: Dict[str, Any], userinfo: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    email = idinfo.get('email') or (userinfo or {}).get('email')
    name = idinfo.get('name') or (userinfo or {}).get('name') or (email or '').split('@')[0]
    sub = idinfo.get('sub')
    picture = idinfo.get('picture') or (userinfo or {}).get('picture')
    return {
        'email': (email or '').strip().lower(),
        'name': name or 'User',
        'google_sub': sub,
        'avatar_url': picture,
    }


