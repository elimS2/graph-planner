from flask import Blueprint, jsonify, request
from flask_login import login_user, logout_user, current_user
from ...extensions import db
from ...models import User


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
    return jsonify({"data": {"id": current_user.get_id()}})

