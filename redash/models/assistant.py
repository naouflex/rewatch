"""Persisted assistant chat threads and messages."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import backref

from redash.models.base import Column, db, key_type
from redash.models.mixins import BelongsToOrgMixin, TimestampMixin


class AssistantThread(TimestampMixin, BelongsToOrgMixin, db.Model):
    __tablename__ = "assistant_threads"

    id = Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(key_type("User"), db.ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title = Column(db.String(80), default="New chat")

    user = db.relationship(
        "User",
        backref=backref("assistant_threads", lazy="dynamic"),
        foreign_keys=[user_id],
    )
    messages = db.relationship(
        "AssistantMessage",
        backref="thread",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="AssistantMessage.id",
    )


class AssistantMessage(TimestampMixin, db.Model):
    __tablename__ = "assistant_messages"

    id = Column(db.Integer, primary_key=True)
    thread_id = Column(
        db.String(36),
        db.ForeignKey("assistant_threads.id", ondelete="CASCADE"),
        index=True,
    )
    role = Column(db.String(16))
    content = Column(db.Text)
