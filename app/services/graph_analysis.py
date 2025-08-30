from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Tuple

from ..extensions import db
from ..models import Node, Edge


def longest_path_by_planned_hours(project_id: str) -> Tuple[List[str], float]:
    nodes: Dict[str, Node] = {n.id: n for n in db.session.query(Node).filter_by(project_id=project_id).all()}
    edges: List[Edge] = db.session.query(Edge).filter_by(project_id=project_id).all()

    outgoing: Dict[str, list[str]] = defaultdict(list)
    indeg: Dict[str, int] = {nid: 0 for nid in nodes.keys()}
    for e in edges:
        if e.source_node_id in nodes and e.target_node_id in nodes:
            outgoing[e.source_node_id].append(e.target_node_id)
            indeg[e.target_node_id] += 1

    # Kahn's algorithm for topological order (ignore cycles by skipping when impossible)
    q = deque([nid for nid, d in indeg.items() if d == 0])
    topo: List[str] = []
    visited = set()
    while q:
        u = q.popleft()
        topo.append(u)
        visited.add(u)
        for v in outgoing.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)

    # If cycles exist, add remaining nodes arbitrarily
    for nid in nodes.keys():
        if nid not in visited:
            topo.append(nid)

    # DP over topo for longest path where weight is planned_hours of node
    dist: Dict[str, float] = {nid: float(nodes[nid].planned_hours or 0) for nid in nodes.keys()}
    prev: Dict[str, str | None] = {nid: None for nid in nodes.keys()}

    for u in topo:
        for v in outgoing.get(u, []):
            w = float(nodes[v].planned_hours or 0)
            if dist[u] + w > dist[v]:
                dist[v] = dist[u] + w
                prev[v] = u

    # Find end of longest path
    end = max(dist, key=lambda k: dist[k]) if dist else None
    if end is None:
        return ([], 0.0)

    # Reconstruct path
    path: List[str] = []
    cur = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]  # type: ignore
    path.reverse()
    return (path, dist[end])


