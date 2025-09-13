from flask import Blueprint, jsonify, request, current_app, send_file
import os
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import glob
from pathlib import Path
import logging

from ...extensions import db
from flask_login import login_required
from ...models import Project, Node, Edge, Comment, TimeEntry, CostEntry, NodeLayout, StatusChange, User, NodeTranslation, Attachment
from ...schemas import ProjectSchema, NodeSchema, EdgeSchema, CommentSchema, TimeEntrySchema, CostEntrySchema, StatusChangeSchema, AttachmentSchema, CommentWithAttachmentsSchema
from flask_login import current_user
from ...repositories.translations import (
    get_missing_node_titles,
    get_stale_node_titles,
    upsert_node_translations,
    get_missing_comment_bodies,
    get_stale_comment_bodies,
    upsert_comment_translations,
)
from ...services.translation import translate_texts, TranslationError
from ...services.async_jobs import enqueue_translation_job, get_job
from ...services.nodes import recompute_importance_score, recompute_group_status
from ...services.graph_analysis import longest_path_by_planned_hours
from ...models import NodeTranslation, CommentTranslation
from ...utils.sanitize import sanitize_comment_html
from marshmallow import ValidationError
from ...models import BackgroundJob
from urllib.parse import urlparse
from ...services.uploads import save_filestorage, _resolve_files_root
try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore


bp = Blueprint("graph", __name__, url_prefix="/api/v1")
# Helpers
def _fallback_user_id() -> str:
    """Return a valid user id to attach to audit records when unauthenticated.
    Uses current_user if authenticated; otherwise ensures a demo user exists.
    """
    try:
        if current_user.is_authenticated:  # type: ignore[attr-defined]
            uid = current_user.get_id()  # type: ignore[attr-defined]
            if uid:
                return uid
    except Exception:
        pass
    # Find or create a demo user
    u = db.session.query(User).filter_by(email="demo@example.com").first()
    if not u:
        u = User(email="demo@example.com", name="Demo User")
        db.session.add(u)
        db.session.flush()
    return u.id


def _normalize_and_validate_link_url(raw: object) -> str | None:
    """Trim, normalize empty to None, and validate URL scheme.

    Allowed schemes: http, https, mailto, ftp. Returns normalized string or None.
    Raises ValueError on invalid/unsafe inputs.
    """
    if raw is None:
        return None
    try:
        s = str(raw).strip()
    except Exception:
        return None
    if not s:
        return None
    # Basic control char guard
    if any(ord(ch) < 32 for ch in s):
        raise ValueError("URL contains control characters")
    # Auto-prefix bare domains without scheme
    p = urlparse(s)
    if not p.scheme and not p.netloc and '://' not in s:
        # looks like bare domain? add https://
        try:
            import re
            if re.match(r"^[A-Za-z0-9._-]+\.[A-Za-z]{2,}(/.*)?$", s):
                s = "https://" + s
                p = urlparse(s)
        except Exception:
            pass
    scheme = (p.scheme or "").lower()
    if scheme not in {"http", "https", "mailto", "ftp"}:
        raise ValueError("URL scheme must be http/https/mailto/ftp")
    # For http/https, require netloc
    if scheme in {"http", "https"} and not p.netloc:
        raise ValueError("URL must include a valid host")
    return s


@bp.get("/health")
def health():
    try:
        pid = os.getpid()
    except Exception:
        pid = None
    # Uptime info based on app boot time (config) as a stable reference
    started_iso = None
    now_iso = None
    uptime_seconds = None
    try:
        import datetime as _dt
        started_iso = current_app.config.get("SERVER_STARTED_AT")
        now_dt = _dt.datetime.utcnow()
        now_iso = now_dt.isoformat() + "Z"
        if started_iso:
            try:
                st = _dt.datetime.fromisoformat(started_iso.replace("Z", "+00:00"))
                uptime_seconds = int((now_dt - st).total_seconds())
            except Exception:
                uptime_seconds = None
    except Exception:
        pass
    return jsonify({
        "data": {
            "status": "ok",
            "pid": pid,
            "started": started_iso,
            "now": now_iso,
            "uptime_seconds": uptime_seconds,
        }
    })

###################################################################################################
# Comment management: update and delete
###################################################################################################

def _is_admin(user: User | None) -> bool:
    try:
        return bool(user and getattr(user, "role", "user") == "admin")
    except Exception:
        return False


def _can_manage_comment(user: User | None, comment: Comment) -> bool:
    try:
        uid = user.get_id() if user and hasattr(user, "get_id") else None  # type: ignore[attr-defined]
    except Exception:
        uid = None
    return bool((uid and uid == comment.user_id) or _is_admin(user))


@bp.patch("/comments/<id>")
@login_required
def update_comment(id: str):
    item = db.session.get(Comment, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    if not _can_manage_comment(current_user, item):  # type: ignore[arg-type]
        return jsonify({"errors": [{"status": 403, "title": "Forbidden"}]}), 403
    payload = request.get_json(force=True) or {}
    # Accept only allowed fields
    allowed = {}
    if "body" in payload:
        try:
            allowed["body"] = str(payload.get("body") or "").strip()
        except Exception:
            allowed["body"] = ""
    if "body_html" in payload:
        allowed["body_html"] = sanitize_comment_html(payload.get("body_html"))
    # Validate via schema (partial)
    try:
        data = CommentSchema(partial=True).load(allowed)
    except ValidationError as ve:
        return jsonify({"errors": [{"status": 400, "title": "Invalid payload", "detail": ve.messages}]}), 400
    # Prevent empty updates
    if ("body" in allowed and (allowed.get("body") or "").strip() == "") and ("body_html" not in allowed or not allowed.get("body_html")):
        return jsonify({"errors": [{"status": 400, "title": "Empty content"}]}), 400
    for k, v in data.items():
        setattr(item, k, v)
    # Optional attachments update
    try:
        attach_ids = payload.get("attachment_ids")
        if isinstance(attach_ids, list):
            refs = [db.session.get(Attachment, str(aid)) for aid in attach_ids]
            item.attachments = [a for a in refs if a is not None]
    except Exception:
        pass
    db.session.commit()
    return jsonify({"data": CommentWithAttachmentsSchema().dump(item)})


@bp.delete("/comments/<id>")
@login_required
def delete_comment(id: str):
    item = db.session.get(Comment, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    if not _can_manage_comment(current_user, item):  # type: ignore[arg-type]
        return jsonify({"errors": [{"status": 403, "title": "Forbidden"}]}), 403
    db.session.delete(item)
    db.session.commit()
    return ("", 204)


# Projects CRUD
@bp.get("/projects")
def list_projects():
    items = db.session.query(Project).all()
    return jsonify({"data": ProjectSchema(many=True).dump(items)})


@bp.post("/projects")
@login_required
def create_project():
    payload = request.get_json(force=True) or {}
    data = ProjectSchema().load(payload)
    item = Project(**data)
    db.session.add(item)
    db.session.commit()
    return jsonify({"data": ProjectSchema().dump(item)}), 201


@bp.get("/projects/<id>")
def get_project(id: str):
    item = db.session.get(Project, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    return jsonify({"data": ProjectSchema().dump(item)})


@bp.patch("/projects/<id>")
@login_required
def update_project(id: str):
    item = db.session.get(Project, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    payload = request.get_json(force=True) or {}
    data = ProjectSchema(partial=True).load(payload)
    for k, v in data.items():
        setattr(item, k, v)
    db.session.commit()
    return jsonify({"data": ProjectSchema().dump(item)})


# Nodes
@bp.get("/projects/<project_id>/nodes")
def list_nodes(project_id: str):
    lang = (request.args.get("lang") or "").lower().strip()
    include_hidden_raw = (request.args.get("include_hidden") or "").strip().lower()
    include_hidden = include_hidden_raw in {"1", "true", "yes", "y", "on"}
    base_q = db.session.query(Node).filter_by(project_id=project_id)
    if not include_hidden:
        # Execute with hidden-filter, but fall back to no-filter if DB not migrated yet
        try:
            items = base_q.filter(Node.is_hidden == False).all()  # noqa: E712
        except SQLAlchemyError:
            items = base_q.all()
        except Exception:
            items = base_q.all()
    else:
        items = base_q.all()
    payload = NodeSchema(many=True).dump(items)
    # attach layout if exists (best-effort)
    try:
        layouts = {l.node_id: l for l in db.session.query(NodeLayout).join(Node, Node.id == NodeLayout.node_id).filter(Node.project_id == project_id).all()}
        for n in payload:
            lay = layouts.get(n["id"]) if isinstance(n, dict) else None
            if lay:
                n["position"] = {"x": lay.x, "y": lay.y}
        # attach translations if requested
        if lang:
            tr = { (t.node_id): t for t in db.session.query(NodeTranslation).filter(NodeTranslation.lang==lang, NodeTranslation.node_id.in_([x["id"] for x in payload])).all() }
            for n in payload:
                t = tr.get(n["id"]) if isinstance(n, dict) else None
                if t:
                    n["title_translated"] = t.text
    except SQLAlchemyError:
        pass
    return jsonify({"data": payload})


@bp.post("/projects/<project_id>/nodes")
@login_required
def create_node(project_id: str):
    payload = request.get_json(force=True) or {}
    payload["project_id"] = project_id
    # link_url: normalize and validate if provided
    if "link_url" in payload:
        try:
            payload["link_url"] = _normalize_and_validate_link_url(payload.get("link_url"))
        except ValueError as e:
            return jsonify({"errors": [{"status": 400, "title": "Invalid link_url", "detail": str(e)}]}), 400
    # default link_open_in_new_tab if not provided
    if "link_open_in_new_tab" not in payload:
        payload["link_open_in_new_tab"] = True
    data = NodeSchema().load(payload)
    item = Node(**data)
    db.session.add(item)
    db.session.commit()
    # Record initial status entry for history
    try:
        sc = StatusChange(node_id=item.id, old_status=item.status or "planned", new_status=item.status or "planned")
        db.session.add(sc)
        db.session.commit()
    except Exception:
        db.session.rollback()
    recompute_importance_score(item.id)
    return jsonify({"data": NodeSchema().dump(item)}), 201


@bp.get("/nodes/<id>")
def get_node(id: str):
    item = db.session.get(Node, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    return jsonify({"data": NodeSchema().dump(item)})


@bp.get("/nodes/<node_id>/translation")
def get_node_translation(node_id: str):
    lang = (request.args.get("lang") or "en").lower()
    t = db.session.get(NodeTranslation, (node_id, lang))
    if not t:
        return jsonify({"data": None})
    return jsonify({"data": {"node_id": node_id, "lang": lang, "text": t.text, "provider": t.provider}})


@bp.post("/nodes/<node_id>/translate")
def translate_single_node(node_id: str):
    payload = request.get_json(force=True) or {}
    lang = (payload.get("lang") or "en").lower()
    provider = (payload.get("provider")
                or os.getenv("TRANSLATION_PROVIDER")
                or ("deepl" if os.getenv("DEEPL_API_KEY") else "mock")).lower()
    item = db.session.get(Node, node_id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Node not found"}]}), 404
    try:
        res = translate_texts([item.title or ""], lang, provider=provider)
        if not res:
            return jsonify({"errors": [{"status": 502, "title": "Provider returned no result"}]}), 502
        upsert_node_translations([(node_id, lang, res[0].text, res[0].detected_source_lang)])
        return jsonify({"data": {"node_id": node_id, "lang": lang, "text": res[0].text}})
    except TranslationError as e:
        return jsonify({"errors": [{"status": 502, "title": "Translation error", "detail": str(e)}]}), 502


@bp.patch("/nodes/<id>")
def update_node(id: str):
    item = db.session.get(Node, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    payload = request.get_json(force=True) or {}
    # link_url: normalize and validate if provided
    if "link_url" in payload:
        try:
            payload["link_url"] = _normalize_and_validate_link_url(payload.get("link_url"))
        except ValueError as e:
            return jsonify({"errors": [{"status": 400, "title": "Invalid link_url", "detail": str(e)}]}), 400
    data = NodeSchema(partial=True).load(payload)
    old_status = item.status
    for k, v in data.items():
        setattr(item, k, v)
    db.session.commit()
    # if status changed, recompute group chain
    if "status" in data and data.get("status") != old_status:
        try:
            sc = StatusChange(node_id=item.id, old_status=old_status or "planned", new_status=item.status or "planned")
            db.session.add(sc)
            db.session.commit()
        except Exception:
            db.session.rollback()
        recompute_group_status(item.parent_id)
    recompute_importance_score(item.id)
    return jsonify({"data": NodeSchema().dump(item)})
@bp.get("/nodes/<node_id>/status-history")
def node_status_history(node_id: str):
    try:
        # Return 404 if node does not exist
        node = db.session.get(Node, node_id)
        if not node:
            return jsonify({"errors": [{"status": 404, "title": "Node not found"}]}), 404
        items = (
            db.session.query(StatusChange)
            .filter_by(node_id=node_id)
            .order_by(StatusChange.created_at.desc())
            .all()
        )
        return jsonify({"data": StatusChangeSchema(many=True).dump(items)})
    except SQLAlchemyError:
        # DB not migrated or table missing — return empty list
        return jsonify({"data": []})
    except Exception:
        # Any other error — return empty list to avoid breaking UI
        return jsonify({"data": []})


@bp.delete("/nodes/<id>")
@login_required
def delete_node(id: str):
    item = db.session.get(Node, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    db.session.delete(item)
    db.session.commit()
    return ("", 204)


# Edges
@bp.post("/projects/<project_id>/edges")
@login_required
def create_edge(project_id: str):
    payload = request.get_json(force=True) or {}
    payload["project_id"] = project_id
    data = EdgeSchema().load(payload)
    # Validate source/target existence in this project to avoid ghost edges
    src = db.session.get(Node, data["source_node_id"]) if "source_node_id" in data else None
    tgt = db.session.get(Node, data["target_node_id"]) if "target_node_id" in data else None
    if not src or not tgt or src.project_id != project_id or tgt.project_id != project_id:
        return jsonify({"errors": [{"status": 400, "title": "Invalid edge", "detail": "Source/target missing or not in project"}]}), 400
    item = Edge(**data)
    try:
        db.session.add(item)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"errors": [{"status": 400, "title": "Invalid edge"}]}), 400
    recompute_importance_score(item.source_node_id)
    recompute_importance_score(item.target_node_id)
    return jsonify({"data": EdgeSchema().dump(item)}), 201


@bp.delete("/edges/<id>")
@login_required
def delete_edge(id: str):
    item = db.session.get(Edge, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    source_id = item.source_node_id
    target_id = item.target_node_id
    db.session.delete(item)
    db.session.commit()
    recompute_importance_score(source_id)
    recompute_importance_score(target_id)
    return ("", 204)


# Comments
@bp.post("/nodes/<node_id>/comments")
@login_required
def add_comment(node_id: str):
    try:
        payload = request.get_json(force=True) or {}
        payload["node_id"] = node_id
        # Force a valid user id (ignore client-provided value)
        payload["user_id"] = _fallback_user_id()
        # Extract attachments to avoid schema validation error on unknown field
        attach_ids = None
        try:
            attach_ids = payload.pop("attachment_ids", None)
        except Exception:
            attach_ids = None
        # Safety: ensure body not empty if only attachments/html are present
        try:
            btxt = str(payload.get("body") or "").strip()
            if not btxt:
                payload["body"] = "(attachment)"
        except Exception:
            payload["body"] = "(attachment)"
        data = CommentSchema().load(payload)
        # Sanitize optional HTML
        if "body_html" in data:
            data["body_html"] = sanitize_comment_html(data.get("body_html"))
        item = Comment(**data)
        db.session.add(item)
        # Link attachments if provided
        try:
            if isinstance(attach_ids, list):
                refs = [db.session.get(Attachment, str(aid)) for aid in attach_ids]
                item.attachments = [a for a in refs if a is not None]
        except Exception:
            pass
        db.session.commit()
        return jsonify({"data": CommentWithAttachmentsSchema().dump(item)}), 201
    except ValidationError as ve:
        return jsonify({"errors": [{"status": 400, "title": "Invalid comment payload", "detail": ve.messages}]}), 400
    except IntegrityError as ie:
        db.session.rollback()
        return jsonify({"errors": [{"status": 409, "title": "Integrity error", "detail": str(ie)}]}), 409
    except Exception as e:  # pragma: no cover
        db.session.rollback()
        current_app.logger.exception("Failed to add comment")
        return jsonify({"errors": [{"status": 500, "title": "Internal Server Error", "detail": str(e)}]}), 500


@bp.get("/nodes/<node_id>/comments")
def list_comments(node_id: str):
    lang = (request.args.get("lang") or "").lower().strip()
    order = (request.args.get("order") or "asc").strip().lower()
    if order not in {"asc", "desc"}:
        order = "asc"
    q = db.session.query(Comment).filter_by(node_id=node_id)
    if order == "desc":
        q = q.order_by(Comment.created_at.desc())
    else:
        q = q.order_by(Comment.created_at.asc())
    items = q.all()
    payload = CommentWithAttachmentsSchema(many=True).dump(items)
    if lang:
        from ...models import CommentTranslation
        try:
            trs = {(t.comment_id): t for t in db.session.query(CommentTranslation).filter(CommentTranslation.lang==lang, CommentTranslation.comment_id.in_([c["id"] for c in payload])).all()}
            for c in payload:
                t = trs.get(c["id"]) if isinstance(c, dict) else None
                if t:
                    c["body_translated"] = t.text
        except SQLAlchemyError:
            pass
    return jsonify({"data": payload})


# Attachments API
@bp.post("/attachments")
@login_required
def upload_attachment():
    try:
        # Simple in-memory rate limiting per IP (best-effort)
        try:
            from flask import g
            import time
            now = time.time()
            wnd = 3.0
            key = f"upload_last_{request.remote_addr or 'x'}"
            last = getattr(g, key, 0)
            if last and (now - last) < 0.5:
                return jsonify({"errors": [{"status": 429, "title": "Too Many Requests"}]}), 429
            setattr(g, key, now)
        except Exception:
            pass
        if "file" not in request.files:
            return jsonify({"errors": [{"status": 400, "title": "file field is required"}]}), 400
        file = request.files["file"]
        uploader_id = _fallback_user_id()
        saved = save_filestorage(file, uploader_id)
        att = saved.attachment
        # Public URL for client
        safe_name = (att.original_name or "file").replace("/", "-")
        url = f"/api/v1/files/{att.id}/{safe_name}"
        data = AttachmentSchema().dump(att)
        data["url"] = url
        return jsonify({"data": data}), 201
    except Exception as e:
        return jsonify({"errors": [{"status": 400, "title": "Upload failed", "detail": str(e)}]}), 400


@bp.get("/attachments/<id>")
def get_attachment(id: str):
    att = db.session.get(Attachment, id)
    if not att:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    safe_name = (att.original_name or "file").replace("/", "-")
    url = f"/api/v1/files/{att.id}/{safe_name}"
    data = AttachmentSchema().dump(att)
    data["url"] = url
    return jsonify({"data": data})


@bp.get("/files/<id>/<name>")
def serve_attachment(id: str, name: str):
    att = db.session.get(Attachment, id)
    if not att:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    root = _resolve_files_root()
    abs_path = (root / att.storage_path).resolve()
    try:
        # Simple caching via ETag on checksum (extend with resize params if any)
        etag_base = (att.checksum_sha256 or att.id)
        w_raw = request.args.get("w")
        h_raw = request.args.get("h")
        w = int(w_raw) if w_raw and w_raw.isdigit() else None
        h = int(h_raw) if h_raw and h_raw.isdigit() else None
        # Clamp to sane bounds
        if w is not None:
            w = max(16, min(4096, w))
        if h is not None:
            h = max(16, min(4096, h))
        # If image and resize requested, serve a cached thumbnail or create one
        is_image = (att.mime_type or "").lower().startswith("image/")
        thumb_path = None
        if is_image and (w or h) and Image is not None:
            try:
                thumbs_dir = (root / "thumbnails").resolve()
                thumbs_dir.mkdir(parents=True, exist_ok=True)
                # Choose output ext/format based on original
                ext = "jpg" if (att.mime_type or "").lower() in {"image/jpeg", "image/jpg"} else ("png" if (att.mime_type or "").lower() == "image/png" else "webp")
                out_name = f"{att.id}_w{w or 'x'}_h{h or 'x'}.{ext}"
                thumb_path = thumbs_dir / out_name
                if not thumb_path.exists():
                    with Image.open(abs_path) as im:  # type: ignore[attr-defined]
                        im_format = "JPEG" if ext == "jpg" else ("PNG" if ext == "png" else "WEBP")
                        # Preserve aspect ratio within bounds
                        max_w = w or 4096
                        max_h = h or 4096
                        im.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)  # type: ignore[attr-defined]
                        # Convert alpha for JPEG
                        if im_format == "JPEG" and im.mode in ("RGBA", "LA"):
                            bg = Image.new("RGB", im.size, (255, 255, 255))  # type: ignore[attr-defined]
                            bg.paste(im, mask=im.split()[-1])
                            bg.save(thumb_path, im_format, quality=85)
                        else:
                            save_kwargs = {"quality": 85} if im_format in {"JPEG", "WEBP"} else {}
                            im.save(thumb_path, im_format, **save_kwargs)
                # Serve thumbnail
                etag = f"{etag_base}_{w or 'x'}x{h or 'x'}"
                inm = request.headers.get('If-None-Match')
                if inm and etag and inm.strip('"') == etag:
                    return ("", 304, {"ETag": f'"{etag}"', "Cache-Control": "public, max-age=86400"})
                rv = send_file(thumb_path, mimetype=att.mime_type if ext in {"jpg", "png"} else "image/webp", as_attachment=False, download_name=(att.original_name or name))
                try:
                    rv.headers["ETag"] = f'"{etag}"'
                    rv.headers["Cache-Control"] = "public, max-age=86400"
                except Exception:
                    pass
                return rv
            except Exception:
                # Fallback to original if resize fails
                pass
        # Fall back to serving original
        etag = etag_base
        inm = request.headers.get('If-None-Match')
        if inm and etag and inm.strip('"') == etag:
            return ("", 304, {"ETag": f'"{etag}"', "Cache-Control": "public, max-age=86400"})
        rv = send_file(abs_path, mimetype=att.mime_type, as_attachment=False, download_name=(att.original_name or name))
        try:
            rv.headers["ETag"] = f'"{etag}"'
            rv.headers["Cache-Control"] = "public, max-age=86400"
        except Exception:
            pass
        return rv
    except Exception as e:
        return jsonify({"errors": [{"status": 404, "title": "File not found", "detail": str(e)}]}), 404


# Time entries
@bp.post("/nodes/<node_id>/time-entries")
@login_required
def add_time_entry(node_id: str):
    payload = request.get_json(force=True) or {}
    payload["node_id"] = node_id
    # Ensure a valid user id
    payload["user_id"] = _fallback_user_id()
    data = TimeEntrySchema().load(payload)
    item = TimeEntry(**data)
    db.session.add(item)
    # roll up hours to node
    node = db.session.get(Node, node_id)
    if node:
        node.actual_hours = float(node.actual_hours or 0) + float(item.hours or 0)
    db.session.commit()
    recompute_importance_score(node_id)
    # touch parent group status if any
    parent = node.parent_id if node else None
    if parent:
        recompute_group_status(parent)
    return jsonify({"data": TimeEntrySchema().dump(item)}), 201


@bp.get("/nodes/<node_id>/time-entries")
def list_time_entries(node_id: str):
    items = db.session.query(TimeEntry).filter_by(node_id=node_id).all()
    return jsonify({"data": TimeEntrySchema(many=True).dump(items)})


# Cost entries
@bp.post("/nodes/<node_id>/cost-entries")
@login_required
def add_cost_entry(node_id: str):
    payload = request.get_json(force=True) or {}
    payload["node_id"] = node_id
    data = CostEntrySchema().load(payload)
    item = CostEntry(**data)
    db.session.add(item)
    # roll up costs to node
    node = db.session.get(Node, node_id)
    if node:
        node.actual_cost = float(node.actual_cost or 0) + float(item.amount or 0)
    db.session.commit()
    recompute_importance_score(node_id)
    parent = node.parent_id if node else None
    if parent:
        recompute_group_status(parent)
    return jsonify({"data": CostEntrySchema().dump(item)}), 201


@bp.get("/nodes/<node_id>/cost-entries")
def list_cost_entries(node_id: str):
    items = db.session.query(CostEntry).filter_by(node_id=node_id).all()
    return jsonify({"data": CostEntrySchema(many=True).dump(items)})


@bp.get("/projects/<project_id>/edges")
def list_edges(project_id: str):
    from sqlalchemy.orm import aliased
    S = aliased(Node)
    T = aliased(Node)
    items = (
        db.session.query(Edge)
        .join(S, S.id == Edge.source_node_id)
        .join(T, T.id == Edge.target_node_id)
        .filter(Edge.project_id == project_id)
        .all()
    )
    return jsonify({"data": EdgeSchema(many=True).dump(items)})


@bp.post("/nodes/<node_id>/position")
@login_required
def save_node_position(node_id: str):
    payload = request.get_json(force=True) or {}
    x = float(payload.get("x", 0))
    y = float(payload.get("y", 0))
    try:
        lay = db.session.get(NodeLayout, node_id)
        if not lay:
            lay = NodeLayout(node_id=node_id, x=x, y=y)
            db.session.add(lay)
        else:
            lay.x = x
            lay.y = y
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        # best-effort: ignore if table missing
    return jsonify({"data": {"node_id": node_id, "x": x, "y": y}})


@bp.get("/projects/<project_id>/metrics")
def project_metrics(project_id: str):
    nodes = db.session.query(Node).filter_by(project_id=project_id).all()
    edges = db.session.query(Edge).filter_by(project_id=project_id).all()
    total_hours = sum(float(n.actual_hours or 0) for n in nodes)
    total_cost = sum(float(n.actual_cost or 0) for n in nodes)
    top_nodes = sorted(nodes, key=lambda n: float(n.importance_score or 0), reverse=True)[:5]
    path, weight = longest_path_by_planned_hours(project_id)
    return jsonify({
        "data": {
            "count_nodes": len(nodes),
            "count_edges": len(edges),
            "total_hours": total_hours,
            "total_cost": total_cost,
            "top_nodes": [{"id": n.id, "title": n.title, "score": n.importance_score} for n in top_nodes],
            "critical_path_hint": {"node_ids": path, "total_planned_hours": weight}
        }
    })


@bp.get("/debug/db-url")
def debug_db_url():
    try:
        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
        return jsonify({"data": {"sqlalchemy_database_uri": uri}})
    except Exception as e:
        return jsonify({"errors": [{"status": 500, "title": "Debug error", "detail": str(e)}]}), 500


@bp.get("/debug/status-count/<node_id>")
def debug_status_count(node_id: str):
    try:
        exists_node = bool(db.session.get(Node, node_id))
        cnt = db.session.query(db.func.count(StatusChange.id)).filter(StatusChange.node_id == node_id).scalar() or 0
        sample = (
            db.session.query(StatusChange)
            .filter(StatusChange.node_id == node_id)
            .order_by(StatusChange.created_at.desc())
            .limit(5)
            .all()
        )
        return jsonify({
            "data": {
                "node_exists": exists_node,
                "count": int(cnt),
                "sample": StatusChangeSchema(many=True).dump(sample),
            }
        })
    except SQLAlchemyError as e:
        return jsonify({"errors": [{"status": 500, "title": "DB error", "detail": str(e)}]}), 500

@bp.get("/projects/<project_id>/nodes/lang-audit")
def nodes_lang_audit(project_id: str):
    items = db.session.query(Node).filter_by(project_id=project_id).all()
    def guess_lang(text: str) -> str:
        t = (text or "")
        # Heuristic: Cyrillic => ru/uk (by presence of іїєґ), Latin letters => en
        try:
            if any('\u0400' <= ch <= '\u04FF' for ch in t):
                if any(ch in t for ch in ("і", "ї", "є", "ґ", "І", "Ї", "Є", "Ґ")):
                    return "uk"
                return "ru"
            if any(('A' <= ch <= 'Z') or ('a' <= ch <= 'z') for ch in t):
                return "en"
        except Exception:
            pass
        return "unknown"

    out = []
    counts = {"ru": 0, "uk": 0, "en": 0, "unknown": 0}
    for n in items:
        gl = guess_lang(n.title or "")
        counts[gl] = counts.get(gl, 0) + 1
        out.append({"id": n.id, "title": n.title, "guess": gl})
    return jsonify({"data": {"total": len(items), "counts": counts, "items": out}})
@bp.post("/projects/<project_id>/translate")
def translate_project(project_id: str):
    payload = request.get_json(force=True) or {}
    lang = (payload.get("lang") or "en").lower()
    include_nodes = True if payload.get("include_nodes") in (None, True) else False
    include_comments = bool(payload.get("include_comments"))
    include_stale = bool(payload.get("stale"))
    force = bool(payload.get("force"))
    dry_run = bool(payload.get("dry_run"))
    provider = (payload.get("provider")
                or os.getenv("TRANSLATION_PROVIDER")
                or ("deepl" if os.getenv("DEEPL_API_KEY") else "mock")).lower()

    translated = 0
    skipped = 0

    try:
        todo_nodes: list[tuple[str, str]] = []
        todo_comments: list[tuple[str, str]] = []
        if include_nodes:
            if force:
                todo_nodes = [(nid, title or "") for nid, title in db.session.query(Node.id, Node.title).filter(Node.project_id == project_id).all()]
            else:
                missing = get_missing_node_titles(project_id, lang)
                stale = get_stale_node_titles(project_id, lang) if include_stale else []
                todo_nodes = list({(nid, t) for (nid, t) in missing + stale})
            if dry_run:
                pass
            elif todo_nodes:
                texts = [t for (_, t) in todo_nodes]
                res = translate_texts(texts, lang, provider=provider)
                records = []
                for (nid, _), tr in zip(todo_nodes, res):
                    records.append((nid, lang, tr.text, tr.detected_source_lang))
                upsert_node_translations(records)
                translated += len(records)
            else:
                skipped += 1
        if include_comments:
            if force:
                todo_comments = [
                    (cid, body or "")
                    for cid, body in (
                        db.session.query(Comment.id, Comment.body)
                        .join(Node, Node.id == Comment.node_id)
                        .filter(Node.project_id == project_id)
                        .all()
                    )
                ]
            else:
                missing_c = get_missing_comment_bodies(project_id, lang)
                stale_c = get_stale_comment_bodies(project_id, lang) if include_stale else []
                todo_comments = list({(cid, b) for (cid, b) in missing_c + stale_c})
            if dry_run:
                pass
            elif todo_comments:
                texts = [b for (_, b) in todo_comments]
                res = translate_texts(texts, lang, provider=provider)
                records = []
                for (cid, _), tr in zip(todo_comments, res):
                    records.append((cid, lang, tr.text, tr.detected_source_lang))
                upsert_comment_translations(records)
                translated += len(records)
    except TranslationError as e:
        return jsonify({"errors": [{"status": 502, "title": "Translation provider error", "detail": str(e)}]}), 502

    if dry_run:
        return jsonify({
            "data": {
                "dry_run": True,
                "todo_nodes": len(todo_nodes),
                "todo_comments": len(todo_comments),
                "total": len(todo_nodes) + len(todo_comments),
            }
        })
    return jsonify({"data": {"translated": translated, "skipped": skipped}})


@bp.post("/projects/<project_id>/translate/async")
def translate_project_async(project_id: str):
    payload = request.get_json(force=True) or {}
    lang = (payload.get("lang") or "en").lower()
    include_nodes = True if payload.get("include_nodes") in (None, True) else False
    include_comments = bool(payload.get("include_comments"))
    include_stale = bool(payload.get("stale"))
    provider = (payload.get("provider")
                or os.getenv("TRANSLATION_PROVIDER")
                or ("deepl" if os.getenv("DEEPL_API_KEY") else "mock")).lower()
    force = bool(payload.get("force"))
    # Synchronous fast-path: if nothing requested, mark job finished immediately
    if not include_nodes and not include_comments:
        job_id = enqueue_translation_job(current_app._get_current_object(), project_id, lang, include_nodes, include_comments, include_stale, provider, force)  # type: ignore[arg-type]
        try:
            jb = db.session.get(BackgroundJob, job_id)
            if jb:
                jb.status = "running"
                jb.total = 0
                jb.done = 0
                jb.translated = 0
                db.session.commit()
                logging.info(f"[translate job {job_id}] running (api fast-path)")
                jb.status = "finished"
                jb.skipped = 2
                db.session.commit()
                logging.info(f"[translate job {job_id}] finished (api fast-path)")
        except Exception:
            db.session.rollback()
        return jsonify({"data": {"job_id": job_id}}), 202

    job_id = enqueue_translation_job(current_app._get_current_object(), project_id, lang, include_nodes, include_comments, include_stale, provider, force)  # type: ignore[arg-type]
    try:
        logging.info(f"[translate job {job_id}] enqueued via API project={project_id} lang={lang} nodes={include_nodes} comments={include_comments} stale={include_stale} force={force} provider={provider}")
    except Exception:
        pass
    return jsonify({"data": {"job_id": job_id}}), 202


@bp.get("/jobs/<job_id>")
def get_job_status(job_id: str):
    j = get_job(job_id)
    if not j:
        return jsonify({"errors": [{"status": 404, "title": "Job not found"}]}), 404
    return jsonify({"data": j})


@bp.get("/projects/<project_id>/translation/stats")
def translation_stats(project_id: str):
    lang = (request.args.get("lang") or "en").lower()
    try:
        mn = len(get_missing_node_titles(project_id, lang))
        sn = len(get_stale_node_titles(project_id, lang))
        mc = len(get_missing_comment_bodies(project_id, lang))
        sc = len(get_stale_comment_bodies(project_id, lang))
        # totals across all items in board
        total_nodes = db.session.query(db.func.count(Node.id)).filter(Node.project_id == project_id).scalar() or 0
        total_comments = (
            db.session.query(db.func.count(Comment.id))
            .join(Node, Node.id == Comment.node_id)
            .filter(Node.project_id == project_id)
            .scalar() or 0
        )
        return jsonify({"data": {
            "missing_nodes": mn,
            "stale_nodes": sn,
            "missing_comments": mc,
            "stale_comments": sc,
            "total_nodes": int(total_nodes),
            "total_comments": int(total_comments),
        }})
    except SQLAlchemyError:
        return jsonify({"errors": [{"status": 500, "title": "Stats unavailable"}]}), 500


@bp.get("/logs/latest")
def get_latest_log():
    try:
        # Read LOGS_DIR from .env (project root)
        root = Path(current_app.root_path).parent
        env_path = root / ".env"
        logs_dir = None
        if env_path.exists():
            try:
                for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == "LOGS_DIR":
                            logs_dir = v.strip()
                            break
            except Exception:
                pass
        logs_dir = logs_dir or "logs"
        log_dir_path = Path(logs_dir) if Path(logs_dir).is_absolute() else (root / logs_dir)
        files = sorted(log_dir_path.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return jsonify({"data": {"file": None, "lines": []}})
        latest = files[0]
        with latest.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-200:]
        return jsonify({"data": {"file": latest.name, "lines": [ln.rstrip("\n") for ln in lines]}})
    except Exception as e:
        return jsonify({"errors": [{"status": 500, "title": "Log read error", "detail": str(e)}]}), 500


@bp.get("/logs/jobs/<job_id>")
def get_job_log(job_id: str):
    try:
        root = Path(current_app.root_path).parent
        env_path = root / ".env"
        logs_dir = None
        if env_path.exists():
            try:
                for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == "LOGS_DIR":
                            logs_dir = v.strip()
                            break
            except Exception:
                pass
        logs_dir = logs_dir or "logs"
        log_dir_path = Path(logs_dir) if Path(logs_dir).is_absolute() else (root / logs_dir)
        files = sorted(log_dir_path.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return jsonify({"data": {"file": None, "lines": []}})
        latest = files[0]
        matched: list[str] = []
        with latest.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if f"[translate job {job_id}]" in line:
                    matched.append(line.rstrip("\n"))
        matched = matched[-200:]
        return jsonify({"data": {"file": latest.name, "lines": matched}})
    except Exception as e:
        return jsonify({"errors": [{"status": 500, "title": "Log read error", "detail": str(e)}]}), 500

@bp.post("/projects/<project_id>/groups")
@login_required
def group_nodes(project_id: str):
    payload = request.get_json(force=True) or {}
    title = (payload.get("title") or "Group").strip()
    node_ids = payload.get("node_ids") or []
    if not node_ids:
        return jsonify({"errors": [{"status": 400, "title": "node_ids required"}]}), 400
    group = Node(project_id=project_id, title=title, is_group=True, status="todo")
    db.session.add(group)
    db.session.flush()
    children = db.session.query(Node).filter(Node.id.in_(node_ids), Node.project_id == project_id).all()
    for ch in children:
        ch.parent_id = group.id
    db.session.commit()
    return jsonify({"data": NodeSchema().dump(group)}), 201


@bp.post("/groups/<group_id>/ungroup")
@login_required
def ungroup_nodes(group_id: str):
    group = db.session.get(Node, group_id)
    if not group or not group.is_group:
        return jsonify({"errors": [{"status": 404, "title": "Group not found"}]}), 404
    children = db.session.query(Node).filter_by(parent_id=group.id).all()
    for ch in children:
        ch.parent_id = None
    group.is_group = False
    db.session.commit()
    return jsonify({"data": {"ungrouped": [c.id for c in children], "group_id": group.id}})

