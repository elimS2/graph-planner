from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..extensions import db


@dataclass
class ServiceResult:
    ok: bool
    data: object | None = None
    error: str | None = None


class BaseService:
    def commit(self) -> None:
        db.session.commit()


