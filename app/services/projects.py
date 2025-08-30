from __future__ import annotations

from dataclasses import dataclass

from ..models import Project
from ..repositories.projects import ProjectRepository
from . import BaseService, ServiceResult


@dataclass
class ProjectCreateInput:
    name: str
    description: str | None = None


class ProjectService(BaseService):
    def __init__(self, repo: ProjectRepository | None = None) -> None:
        self.repo = repo or ProjectRepository()

    def create(self, data: ProjectCreateInput) -> ServiceResult:
        if not data.name:
            return ServiceResult(False, error="name is required")
        project = Project(name=data.name, description=data.description)
        self.repo.add(project)
        self.commit()
        return ServiceResult(True, data=project)

    def list_all(self) -> list[Project]:
        return self.repo.list_all()

