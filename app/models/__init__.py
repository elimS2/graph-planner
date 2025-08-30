from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, Table, Column
from sqlalchemy.orm import relationship, Mapped, mapped_column
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import db


def generate_uuid() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[str] = mapped_column(db.String, default=lambda: datetime.utcnow().isoformat() + "Z", nullable=False)


# Association table for many-to-many Node <-> Tag
node_tag = Table(
    "node_tag",
    db.metadata,
    Column("node_id", db.String, ForeignKey("node.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", db.String, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)


class User(UserMixin, db.Model, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(db.String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(db.String, nullable=False)
    role: Mapped[str] = mapped_column(db.String, nullable=False, default="user")
    password_hash: Mapped[str] = mapped_column(db.String, nullable=True)

    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="user", cascade="all, delete-orphan")

    # Password helpers
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class Project(db.Model, TimestampMixin):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(db.String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    archived: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)

    nodes = relationship("Node", back_populates="project", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="project", cascade="all, delete-orphan")


class Node(db.Model, TimestampMixin):
    __tablename__ = "node"

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(db.String, ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(db.String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    status: Mapped[str] = mapped_column(db.String, default="planned", nullable=False)
    importance_score: Mapped[float] = mapped_column(db.Float, default=0.0, nullable=False)
    planned_hours: Mapped[float] = mapped_column(db.Float, default=0.0, nullable=False)
    actual_hours: Mapped[float] = mapped_column(db.Float, default=0.0, nullable=False)
    planned_cost: Mapped[float] = mapped_column(db.Float, default=0.0, nullable=False)
    actual_cost: Mapped[float] = mapped_column(db.Float, default=0.0, nullable=False)
    assignee_id: Mapped[Optional[str]] = mapped_column(db.String, ForeignKey("user.id"), nullable=True)
    parent_id: Mapped[Optional[str]] = mapped_column(db.String, ForeignKey("node.id", ondelete="SET NULL"), nullable=True)
    is_group: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)

    project = relationship("Project", back_populates="nodes")
    assignee = relationship("User", foreign_keys=[assignee_id])

    parent = relationship("Node", remote_side=[id], back_populates="children")
    children = relationship("Node", back_populates="parent", cascade="all")

    outgoing_edges = relationship("Edge", foreign_keys="Edge.source_node_id", back_populates="source_node", cascade="all, delete-orphan")
    incoming_edges = relationship("Edge", foreign_keys="Edge.target_node_id", back_populates="target_node", cascade="all, delete-orphan")

    comments = relationship("Comment", back_populates="node", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="node", cascade="all, delete-orphan")
    cost_entries = relationship("CostEntry", back_populates="node", cascade="all, delete-orphan")

    tags = relationship("Tag", secondary=node_tag, back_populates="nodes")


class Edge(db.Model, TimestampMixin):
    __tablename__ = "edge"

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(db.String, ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    source_node_id: Mapped[str] = mapped_column(db.String, ForeignKey("node.id", ondelete="CASCADE"), nullable=False)
    target_node_id: Mapped[str] = mapped_column(db.String, ForeignKey("node.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(db.String, default="dependency", nullable=False)
    weight: Mapped[float] = mapped_column(db.Float, default=1.0, nullable=False)

    project = relationship("Project", back_populates="edges")
    source_node = relationship("Node", foreign_keys=[source_node_id], back_populates="outgoing_edges")
    target_node = relationship("Node", foreign_keys=[target_node_id], back_populates="incoming_edges")

    __table_args__ = (
        CheckConstraint("source_node_id <> target_node_id", name="ck_edge_not_self_loop"),
    )


class TimeEntry(db.Model):
    __tablename__ = "time_entry"

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=generate_uuid)
    node_id: Mapped[str] = mapped_column(db.String, ForeignKey("node.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(db.String, ForeignKey("user.id"), nullable=False)
    started_at: Mapped[Optional[str]] = mapped_column(db.String, nullable=True)
    ended_at: Mapped[Optional[str]] = mapped_column(db.String, nullable=True)
    hours: Mapped[float] = mapped_column(db.Float, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)

    node = relationship("Node", back_populates="time_entries")
    user = relationship("User", back_populates="time_entries")


class CostEntry(db.Model):
    __tablename__ = "cost_entry"

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=generate_uuid)
    node_id: Mapped[str] = mapped_column(db.String, ForeignKey("node.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(db.Float, nullable=False)
    currency: Mapped[str] = mapped_column(db.String, default="USD", nullable=False)
    note: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    incurred_at: Mapped[str] = mapped_column(db.String, nullable=False)

    node = relationship("Node", back_populates="cost_entries")


class Comment(db.Model, TimestampMixin):
    __tablename__ = "comment"

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=generate_uuid)
    node_id: Mapped[str] = mapped_column(db.String, ForeignKey("node.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(db.String, ForeignKey("user.id"), nullable=False)
    body: Mapped[str] = mapped_column(db.Text, nullable=False)

    node = relationship("Node", back_populates="comments")
    user = relationship("User", back_populates="comments")


class Tag(db.Model):
    __tablename__ = "tag"

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(db.String, unique=True, nullable=False)

    nodes = relationship("Node", secondary=node_tag, back_populates="tags")


class NodeLayout(db.Model):
    __tablename__ = "node_layout"

    node_id: Mapped[str] = mapped_column(db.String, ForeignKey("node.id", ondelete="CASCADE"), primary_key=True)
    x: Mapped[float] = mapped_column(db.Float, nullable=False, default=0.0)
    y: Mapped[float] = mapped_column(db.Float, nullable=False, default=0.0)
    updated_at: Mapped[str] = mapped_column(db.String, default=lambda: datetime.utcnow().isoformat() + "Z", nullable=False)



