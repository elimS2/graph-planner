from __future__ import annotations

from sqlalchemy import select

from . import BaseRepository
from ..models import Node


class NodeRepository(BaseRepository[Node]):
    def by_id(self, id_: str) -> Node | None:
        return self.session.get(Node, id_)

    def list_by_project(self, project_id: str) -> list[Node]:
        return self.session.scalars(select(Node).where(Node.project_id == project_id)).all()

