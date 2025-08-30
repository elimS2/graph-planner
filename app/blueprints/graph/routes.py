from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ...extensions import db
from ...models import Project, Node, Edge, Comment, TimeEntry, CostEntry, NodeLayout
from ...schemas import ProjectSchema, NodeSchema, EdgeSchema, CommentSchema, TimeEntrySchema, CostEntrySchema
from ...services.nodes import recompute_importance_score, recompute_group_status
from ...services.graph_analysis import longest_path_by_planned_hours


bp = Blueprint("graph", __name__, url_prefix="/api/v1")


@bp.get("/health")
def health():
    return jsonify({"data": {"status": "ok"}})


# Projects CRUD
@bp.get("/projects")
def list_projects():
    items = db.session.query(Project).all()
    return jsonify({"data": ProjectSchema(many=True).dump(items)})


@bp.post("/projects")
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
    items = db.session.query(Node).filter_by(project_id=project_id).all()
    payload = NodeSchema(many=True).dump(items)
    # attach layout if exists (best-effort)
    try:
        layouts = {l.node_id: l for l in db.session.query(NodeLayout).join(Node, Node.id == NodeLayout.node_id).filter(Node.project_id == project_id).all()}
        for n in payload:
            lay = layouts.get(n["id"]) if isinstance(n, dict) else None
            if lay:
                n["position"] = {"x": lay.x, "y": lay.y}
    except SQLAlchemyError:
        pass
    return jsonify({"data": payload})


@bp.post("/projects/<project_id>/nodes")
def create_node(project_id: str):
    payload = request.get_json(force=True) or {}
    payload["project_id"] = project_id
    data = NodeSchema().load(payload)
    item = Node(**data)
    db.session.add(item)
    db.session.commit()
    recompute_importance_score(item.id)
    return jsonify({"data": NodeSchema().dump(item)}), 201


@bp.get("/nodes/<id>")
def get_node(id: str):
    item = db.session.get(Node, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    return jsonify({"data": NodeSchema().dump(item)})


@bp.patch("/nodes/<id>")
def update_node(id: str):
    item = db.session.get(Node, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    payload = request.get_json(force=True) or {}
    data = NodeSchema(partial=True).load(payload)
    for k, v in data.items():
        setattr(item, k, v)
    db.session.commit()
    # if status changed, recompute group chain
    if "status" in data:
        recompute_group_status(item.parent_id)
    recompute_importance_score(item.id)
    return jsonify({"data": NodeSchema().dump(item)})


@bp.delete("/nodes/<id>")
def delete_node(id: str):
    item = db.session.get(Node, id)
    if not item:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404
    db.session.delete(item)
    db.session.commit()
    return ("", 204)


# Edges
@bp.post("/projects/<project_id>/edges")
def create_edge(project_id: str):
    payload = request.get_json(force=True) or {}
    payload["project_id"] = project_id
    data = EdgeSchema().load(payload)
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
def add_comment(node_id: str):
    payload = request.get_json(force=True) or {}
    payload["node_id"] = node_id
    data = CommentSchema().load(payload)
    item = Comment(**data)
    db.session.add(item)
    db.session.commit()
    return jsonify({"data": CommentSchema().dump(item)}), 201


@bp.get("/nodes/<node_id>/comments")
def list_comments(node_id: str):
    items = db.session.query(Comment).filter_by(node_id=node_id).order_by(Comment.created_at.desc()).all()
    return jsonify({"data": CommentSchema(many=True).dump(items)})


# Time entries
@bp.post("/nodes/<node_id>/time-entries")
def add_time_entry(node_id: str):
    payload = request.get_json(force=True) or {}
    payload["node_id"] = node_id
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
    items = db.session.query(Edge).filter_by(project_id=project_id).all()
    return jsonify({"data": EdgeSchema(many=True).dump(items)})


@bp.post("/nodes/<node_id>/position")
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


@bp.post("/projects/<project_id>/groups")
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

