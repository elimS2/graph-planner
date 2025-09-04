from __future__ import annotations

from ..extensions import db
from ..models import Node, TimeEntry, CostEntry, Comment


def recompute_importance_score(node_id: str) -> None:
    node = db.session.get(Node, node_id)
    if not node:
        return
    total_hours = float(node.actual_hours or 0) + float(node.planned_hours or 0)
    degree = len(node.incoming_edges) + len(node.outgoing_edges)
    descendants = len(node.children)
    score = 0.5 * _log1p(total_hours) + 0.2 * _log1p(descendants) + 0.2 * _log1p(degree)
    node.importance_score = float(score)
    db.session.commit()


def _log1p(x: float) -> float:
    import math
    return math.log1p(max(0.0, x))


def recompute_group_status(start_group_id: str | None) -> None:
    """Recalculate status for a group and its ancestors based on children.

    Priority: blocked > in-progress > planned > done. Status 'discuss' is treated as planned.
    All done => done; any blocked => blocked; any in-progress => in-progress; else planned.
    """
    current_id = start_group_id
    while current_id:
        group: Node | None = db.session.get(Node, current_id)
        if not group:
            break
        children: list[Node] = db.session.query(Node).filter_by(parent_id=current_id).all()
        if not children:
            # empty groups default to planned
            group.status = "planned"
        else:
            # Treat any unknown/non-terminal statuses (e.g., 'discuss') as 'planned' for grouping
            statuses = { (c.status if c.status in {"planned", "in-progress", "done", "blocked"} else "planned") or "planned" for c in children }
            if "blocked" in statuses:
                group.status = "blocked"
            elif "in-progress" in statuses:
                group.status = "in-progress"
            elif statuses == {"done"}:
                group.status = "done"
            else:
                group.status = "planned"
        db.session.commit()
        # walk up
        current_id = group.parent_id


