from __future__ import annotations

from typing import Generic, Iterable, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..extensions import db


T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, session: Optional[Session] = None) -> None:
        self.session = session or db.session

    def add(self, entity: T) -> T:
        self.session.add(entity)
        return entity

    def get(self, model: type[T], id_: str) -> Optional[T]:
        return self.session.get(model, id_)

    def list(self, model: type[T]) -> Iterable[T]:
        return self.session.scalars(select(model)).all()

    def delete(self, entity: T) -> None:
        self.session.delete(entity)

    def commit(self) -> None:
        self.session.commit()


