from flask import Blueprint, jsonify, request, redirect
from flask_login import login_user, logout_user, current_user
from ...extensions import db
from ...models import User
from ...services.oauth_google import build_auth_url, exchange_code_for_tokens, verify_id_token, fetch_userinfo, normalize_profile


bp = Blueprint("users", __name__, url_prefix="/api/v1")


@bp.post("/auth/login")
def login():
    payload = request.get_json(force=True) or {}
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    user = db.session.query(User).filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"errors": [{"status": 401, "title": "Invalid credentials"}]}), 401
    login_user(user)
    return jsonify({"data": {"id": user.id, "email": user.email, "name": user.name}})


@bp.post("/auth/logout")
def logout():
    logout_user()
    return jsonify({"data": {"ok": True}})


@bp.get("/auth/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"data": None}), 200
    # Return richer profile for UI
    user = db.session.get(User, current_user.get_id())
    return jsonify({"data": {"id": user.id, "email": user.email, "name": user.name, "avatar_url": getattr(user, 'avatar_url', None)}})


@bp.get("/auth/google/login")
def google_login():
    url, state = build_auth_url()
    return redirect(url)


@bp.get("/auth/google/callback")
def google_callback():
    from flask import session
    state = request.args.get('state')
    if not state or session.get('oauth_google_state') != state:
        return jsonify({"errors": [{"status": 400, "title": "Invalid state"}]}), 400
    code = request.args.get('code')
    if not code:
        return jsonify({"errors": [{"status": 400, "title": "Missing authorization code"}]}), 400
    try:
        tokens = exchange_code_for_tokens(code)
        idinfo = verify_id_token(tokens.get('id_token', ''))
        userinfo = None
        access_token = tokens.get('access_token')
        if access_token:
            try:
                userinfo = fetch_userinfo(access_token)
            except Exception:
                userinfo = None
        profile = normalize_profile(idinfo, userinfo)
        email = profile['email']
        if not email:
            return jsonify({"errors": [{"status": 400, "title": "Email not provided by Google"}]}), 400
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            user = User(email=email, name=profile['name'] or email.split('@')[0])
            user.google_sub = profile.get('google_sub')
            user.avatar_url = profile.get('avatar_url')
            db.session.add(user)
        else:
            # Update external identity if new
            if not getattr(user, 'google_sub', None) and profile.get('google_sub'):
                user.google_sub = profile.get('google_sub')
            if profile.get('avatar_url') and profile.get('avatar_url') != getattr(user, 'avatar_url', None):
                user.avatar_url = profile.get('avatar_url')
        db.session.commit()
        login_user(user)
    except Exception as e:
        return jsonify({"errors": [{"status": 400, "title": "Google auth failed"}]}), 400
    # Redirect back to home or referer
    return redirect("/")

