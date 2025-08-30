from __future__ import annotations

import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone

from flask import Flask
import logging

from ..repositories.translations import (
    get_missing_node_titles,
    get_stale_node_titles,
    upsert_node_translations,
    get_missing_comment_bodies,
    get_stale_comment_bodies,
    upsert_comment_translations,
)
from .translation import translate_texts, TranslationError
from ..extensions import db
from ..models import BackgroundJob


_max_workers = int(os.getenv("ASYNC_WORKERS", "2"))
_executor = ThreadPoolExecutor(max_workers=_max_workers)
_queue_mode = (os.getenv("QUEUE_MODE") or "thread").lower()  # thread | executor
_jobs: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


def _new_job_db(project_id: str | None, job_type: str = "translate") -> str:
    j = BackgroundJob(project_id=project_id, type=job_type, status="queued", total=0, done=0, translated=0, skipped=0)
    db.session.add(j)
    db.session.commit()
    return j.id


def get_job(job_id: str) -> Dict[str, Any] | None:
    jb = db.session.get(BackgroundJob, job_id)
    if not jb:
        return None
    now = datetime.now(timezone.utc)
    created = jb.created_at
    updated = jb.updated_at
    # Compute runtime in ms: running => now - created; finished/failed => updated - created
    run_ms = 0
    try:
        if created:
            end = now if (jb.status == "running") else (updated or now)
            run_ms = int(((end - created).total_seconds()) * 1000)
    except Exception:
        run_ms = 0
    return {
        "id": jb.id,
        "status": jb.status,
        "total": jb.total,
        "done": jb.done,
        "translated": jb.translated,
        "skipped": jb.skipped,
        "error": jb.error,
        "created_at": jb.created_at,
        "updated_at": jb.updated_at,
        "pid": os.getpid(),
        "run_ms": run_ms,
        "now": now,
    }


def _update_job_db(job_id: str, **kwargs: Any) -> None:
    jb = db.session.get(BackgroundJob, job_id)
    if not jb:
        return
    for k, v in kwargs.items():
        if hasattr(jb, k):
            setattr(jb, k, v)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def enqueue_translation_job(
    app: Flask,
    project_id: str,
    lang: str = "en",
    include_nodes: bool = True,
    include_comments: bool = False,
    stale: bool = False,
    provider: str | None = None,
    force: bool = False,
) -> str:
    """Enqueue background translation job for a project.

    Returns job_id.
    """
    job_id = _new_job_db(project_id, job_type="translate")
    logging.info(f"[translate job {job_id}] enqueued project={project_id} lang={lang} nodes={include_nodes} comments={include_comments} stale={stale} force={force} provider={provider}")

    # Fast-path: no work requested → complete synchronously to surface logs/status
    if not include_nodes and not include_comments:
        try:
            with app.app_context():
                _update_job_db(job_id, status="running", total=0, done=0, translated=0)
                logging.info(f"[translate job {job_id}] running (fast-path) pid={os.getpid()} thread={threading.get_ident()}")
                _update_job_db(job_id, status="finished", skipped=2)
                logging.info(f"[translate job {job_id}] finished (fast-path) translated=0 skipped_groups=2")
        except Exception as e:
            try:
                with app.app_context():
                    _update_job_db(job_id, status="failed", error=str(e))
            finally:
                logging.exception(f"[translate job {job_id}] unexpected error in fast-path")
        return job_id

    def _runner() -> None:
        try:
            with app.app_context():
                _update_job_db(job_id, status="running")
                logging.info(f"[translate job {job_id}] running pid={os.getpid()} thread={threading.get_ident()}")
                translated_count = 0
                skipped_groups = 0

                to_translate_nodes: List[Tuple[str, str]] = []
                to_translate_comments: List[Tuple[str, str]] = []
                full_nodes: List[Tuple[str, str]] = []
                full_comments: List[Tuple[str, str]] = []

                if include_nodes:
                    from ..models import Node
                    full_nodes = [(nid, title or "") for nid, title in db.session.query(Node.id, Node.title).filter(Node.project_id == project_id).all()]
                    if force:
                        to_translate_nodes = list(full_nodes)
                    else:
                        missing = get_missing_node_titles(project_id, lang)
                        stale_nodes = get_stale_node_titles(project_id, lang) if stale else []
                        to_translate_nodes = list({(nid, t) for (nid, t) in missing + stale_nodes})
                if include_comments:
                    from ..models import Comment, Node as NodeModel
                    full_comments = [ (cid, body or "") for cid, body in db.session.query(Comment.id, Comment.body).join(NodeModel, NodeModel.id == Comment.node_id).filter(NodeModel.project_id == project_id).all() ]
                    if force:
                        to_translate_comments = list(full_comments)
                    else:
                        missing_c = get_missing_comment_bodies(project_id, lang)
                        stale_c = get_stale_comment_bodies(project_id, lang) if stale else []
                        to_translate_comments = list({(cid, b) for (cid, b) in missing_c + stale_c})

                total_items = len(full_nodes) + len(full_comments)
                _update_job_db(job_id, total=total_items)
                logging.info(f"[translate job {job_id}] total items: {total_items} (nodes={len(full_nodes)}, comments={len(full_comments)})")

                provider_name = provider or os.getenv("TRANSLATION_PROVIDER") or ("deepl" if os.getenv("DEEPL_API_KEY") else "mock")
                logging.info(f"[translate job {job_id}] provider={provider_name}")

                # Prepare maps for nodes/comments that need translation
                to_translate_node_ids = [nid for (nid, _) in to_translate_nodes]
                to_translate_node_texts = [t for (_, t) in to_translate_nodes]
                node_translate_map = {}
                if to_translate_node_texts:
                    node_results = translate_texts(to_translate_node_texts, lang, provider=provider_name)
                    for nid, tr in zip(to_translate_node_ids, node_results):
                        node_translate_map[nid] = tr
                else:
                    skipped_groups += 1

                to_translate_comment_ids = [cid for (cid, _) in to_translate_comments]
                to_translate_comment_texts = [b for (_, b) in to_translate_comments]
                comment_translate_map = {}
                if to_translate_comment_texts:
                    comment_results = translate_texts(to_translate_comment_texts, lang, provider=provider_name)
                    for cid, tr in zip(to_translate_comment_ids, comment_results):
                        comment_translate_map[cid] = tr
                else:
                    skipped_groups += 1

                # Iterate all nodes and update progress per item
                node_records: List[Tuple[str, str, str, str | None]] = []
                done_counter = 0
                for nid, _title in full_nodes:
                    if nid in node_translate_map:
                        tr = node_translate_map[nid]
                        node_records.append((nid, lang, tr.text, tr.detected_source_lang))
                        translated_count += 1
                    done_counter += 1
                    _update_job_db(job_id, done=done_counter, translated=translated_count)
                    logging.info(f"[translate job {job_id}] progress {done_counter}/{total_items} (translated={translated_count})")

                # Iterate all comments and update progress per item
                comment_records: List[Tuple[str, str, str, str | None]] = []
                for cid, _body in full_comments:
                    if cid in comment_translate_map:
                        tr = comment_translate_map[cid]
                        comment_records.append((cid, lang, tr.text, tr.detected_source_lang))
                        translated_count += 1
                    done_counter += 1
                    _update_job_db(job_id, done=done_counter, translated=translated_count)
                    logging.info(f"[translate job {job_id}] progress {done_counter}/{total_items} (translated={translated_count})")

                # Bulk upsert after iteration
                if node_records:
                    upsert_node_translations(node_records)
                if comment_records:
                    upsert_comment_translations(comment_records)

                db.session.remove()

                _update_job_db(job_id, status="finished", skipped=skipped_groups)
                logging.info(f"[translate job {job_id}] finished translated={translated_count} skipped_groups={skipped_groups}")
        except TranslationError as e:
            try:
                with app.app_context():
                    _update_job_db(job_id, status="failed", error=str(e))
            finally:
                logging.error(f"[translate job {job_id}] failed: {e}")
        except Exception as e:  # defensive catch-all
            try:
                with app.app_context():
                    _update_job_db(job_id, status="failed", error=str(e))
            finally:
                logging.exception(f"[translate job {job_id}] unexpected error")

    try:
        if _queue_mode == "executor":
            _executor.submit(_runner)
            logging.info(f"[translate job {job_id}] submitted to executor")
        else:
            th = threading.Thread(target=_runner, name=f"job-{job_id}", daemon=True)
            th.start()
            logging.info(f"[translate job {job_id}] started thread id={th.ident}")
    except Exception as e:
        logging.exception(f"[translate job {job_id}] failed to submit: {e}")
    return job_id


