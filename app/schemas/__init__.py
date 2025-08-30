from __future__ import annotations

from marshmallow import Schema, fields


class ProjectSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True)
    archived = fields.Boolean()
    created_at = fields.String(dump_only=True)


class NodeSchema(Schema):
    id = fields.String(dump_only=True)
    project_id = fields.String(required=True, load_only=True)
    title = fields.String(required=True)
    description = fields.String(allow_none=True)
    status = fields.String()
    importance_score = fields.Float(dump_only=True)
    planned_hours = fields.Float()
    actual_hours = fields.Float(dump_only=True)
    planned_cost = fields.Float()
    actual_cost = fields.Float(dump_only=True)
    assignee_id = fields.String(allow_none=True)
    parent_id = fields.String(allow_none=True)
    is_group = fields.Boolean()
    created_at = fields.String(dump_only=True)
    priority = fields.String()


class EdgeSchema(Schema):
    id = fields.String(dump_only=True)
    project_id = fields.String(required=True, load_only=True)
    source_node_id = fields.String(required=True)
    target_node_id = fields.String(required=True)
    type = fields.String()
    weight = fields.Float()
    created_at = fields.String(dump_only=True)


class CommentSchema(Schema):
    id = fields.String(dump_only=True)
    node_id = fields.String(required=True, load_only=True)
    user_id = fields.String(required=True)
    body = fields.String(required=True)
    created_at = fields.String(dump_only=True)


class TimeEntrySchema(Schema):
    id = fields.String(dump_only=True)
    node_id = fields.String(required=True, load_only=True)
    user_id = fields.String(required=True)
    started_at = fields.String(allow_none=True)
    ended_at = fields.String(allow_none=True)
    hours = fields.Float(required=True)
    note = fields.String(allow_none=True)


class CostEntrySchema(Schema):
    id = fields.String(dump_only=True)
    node_id = fields.String(required=True, load_only=True)
    amount = fields.Float(required=True)
    currency = fields.String()
    note = fields.String(allow_none=True)
    incurred_at = fields.String(required=True)


class StatusChangeSchema(Schema):
    id = fields.String(dump_only=True)
    node_id = fields.String(required=True, load_only=True)
    old_status = fields.String(required=True)
    new_status = fields.String(required=True)
    created_at = fields.String(dump_only=True)


