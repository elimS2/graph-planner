from __future__ import annotations

from sqlalchemy import select

from . import BaseRepository
from ..models import Edge


class EdgeRepository(BaseRepository[Edge]):
    def by_id(self, id_: str) -> Edge | None:
        return self.session.get(Edge, id_)

    def list_by_project(self, project_id: str) -> list[Edge]:
        return self.session.scalars(select(Edge).where(Edge.project_id == project_id)).all()

