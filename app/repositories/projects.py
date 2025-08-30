from __future__ import annotations

from sqlalchemy import select

from . import BaseRepository
from ..models import Project


class ProjectRepository(BaseRepository[Project]):
    def by_id(self, id_: str) -> Project | None:
        return self.session.get(Project, id_)

    def by_name(self, name: str) -> Project | None:
        return self.session.scalars(select(Project).where(Project.name == name)).first()

    def list_all(self) -> list[Project]:
        return self.session.scalars(select(Project)).all()

