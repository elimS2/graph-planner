from __future__ import annotations

from typing import Iterable, List, Tuple

from ..extensions import db
from ..models import Node, Comment, NodeTranslation, CommentTranslation


def get_missing_node_titles(project_id: str, lang: str) -> List[Tuple[str, str]]:
    """Return list of (node_id, title) where translation for lang is missing."""
    q = (
        db.session.query(Node.id, Node.title)
        .filter(Node.project_id == project_id)
        .outerjoin(NodeTranslation, (NodeTranslation.node_id == Node.id) & (NodeTranslation.lang == lang))
        .filter(NodeTranslation.node_id.is_(None))
    )
    return [(nid, title or "") for nid, title in q.all()]


def get_stale_node_titles(project_id: str, lang: str) -> List[Tuple[str, str]]:
    q = (
        db.session.query(Node.id, Node.title, NodeTranslation.created_at)
        .join(NodeTranslation, (NodeTranslation.node_id == Node.id) & (NodeTranslation.lang == lang))
        .filter(Node.project_id == project_id)
        .filter(Node.updated_at > NodeTranslation.created_at)
    )
    return [(nid, title or "") for nid, title, _ in q.all()]


def upsert_node_translations(records: List[Tuple[str, str, str, str | None]]) -> None:
    """records: list of (node_id, lang, text, detected_source_lang)"""
    for node_id, lang, text, det in records:
        inst = db.session.query(NodeTranslation).get((node_id, lang))
        if inst:
            inst.text = text
            inst.provider = "deepl"
            inst.detected_source_lang = det
        else:
            inst = NodeTranslation(node_id=node_id, lang=lang, text=text, provider="deepl", detected_source_lang=det)
            db.session.add(inst)
    db.session.commit()


def get_missing_comment_bodies(project_id: str, lang: str) -> List[Tuple[str, str]]:
    q = (
        db.session.query(Comment.id, Comment.body)
        .join(Node, Node.id == Comment.node_id)
        .filter(Node.project_id == project_id)
        .outerjoin(CommentTranslation, (CommentTranslation.comment_id == Comment.id) & (CommentTranslation.lang == lang))
        .filter(CommentTranslation.comment_id.is_(None))
    )
    return [(cid, body or "") for cid, body in q.all()]


def get_stale_comment_bodies(project_id: str, lang: str) -> List[Tuple[str, str]]:
    q = (
        db.session.query(Comment.id, Comment.body, CommentTranslation.created_at)
        .join(CommentTranslation, (CommentTranslation.comment_id == Comment.id) & (CommentTranslation.lang == lang))
        .join(Node, Node.id == Comment.node_id)
        .filter(Node.project_id == project_id)
        .filter(Comment.updated_at > CommentTranslation.created_at)
    )
    return [(cid, body or "") for cid, body, _ in q.all()]


def upsert_comment_translations(records: List[Tuple[str, str, str, str | None]]) -> None:
    for comment_id, lang, text, det in records:
        inst = db.session.query(CommentTranslation).get((comment_id, lang))
        if inst:
            inst.text = text
            inst.provider = "deepl"
            inst.detected_source_lang = det
        else:
            inst = CommentTranslation(comment_id=comment_id, lang=lang, text=text, provider="deepl", detected_source_lang=det)
            db.session.add(inst)
    db.session.commit()


