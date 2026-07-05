"""Database persistence for assistant chat threads."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from redash.models import AssistantMessage, AssistantThread, db

MAX_THREADS = 30
MAX_LLM_MESSAGES = 36
MAX_LLM_CHARS = 28000
DEFAULT_TITLE = "New chat"


def _title_from_message(content: str) -> str:
    line = (content or "").strip().split("\n", 1)[0]
    if len(line) <= 80:
        return line or DEFAULT_TITLE
    return line[:77] + "..."


def _preview(content: str, limit: int = 120) -> str:
    text = (content or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def create_thread(user, org) -> AssistantThread:
    thread = AssistantThread(
        id=str(uuid.uuid4()),
        user_id=user.id,
        org_id=org.id,
        title=DEFAULT_TITLE,
    )
    db.session.add(thread)
    db.session.commit()
    return thread


def get_thread(thread_id: str, user, org) -> AssistantThread:
    thread = (
        AssistantThread.query.filter(
            AssistantThread.id == thread_id,
            AssistantThread.user_id == user.id,
            AssistantThread.org_id == org.id,
        )
        .one_or_none()
    )
    if thread is None:
        from flask_restful import abort

        abort(404, message="Thread not found.")
    return thread


def list_threads(user, org, limit: int = MAX_THREADS) -> list[dict[str, Any]]:
    threads = (
        AssistantThread.query.filter(
            AssistantThread.user_id == user.id,
            AssistantThread.org_id == org.id,
        )
        .order_by(AssistantThread.updated_at.desc())
        .limit(limit)
        .all()
    )
    results = []
    for thread in threads:
        last_user = (
            thread.messages.filter(AssistantMessage.role == "user")
            .order_by(AssistantMessage.id.desc())
            .first()
        )
        results.append(
            {
                "id": thread.id,
                "title": thread.title,
                "updated_at": thread.updated_at,
                "preview": _preview(last_user.content) if last_user else "",
            }
        )
    return results


def delete_thread(thread_id: str, user, org) -> None:
    thread = get_thread(thread_id, user, org)
    db.session.delete(thread)
    db.session.commit()


def list_messages(thread_id: str, user, org) -> list[dict[str, str]]:
    thread = get_thread(thread_id, user, org)
    return [{"role": m.role, "content": m.content} for m in thread.messages.order_by(AssistantMessage.id)]


def add_message(thread_id: str, role: str, content: str) -> AssistantMessage:
    message = AssistantMessage(thread_id=thread_id, role=role, content=content)
    db.session.add(message)
    db.session.flush()
    return message


def touch_thread(thread: AssistantThread, user_message: Optional[str] = None) -> None:
    if thread.title == DEFAULT_TITLE and user_message:
        thread.title = _title_from_message(user_message)
    from redash.utils import utcnow

    thread.updated_at = utcnow()
    db.session.add(thread)
    db.session.commit()


def fit_messages_for_llm(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    trimmed = messages[-MAX_LLM_MESSAGES:]
    total = sum(len(m.get("content") or "") for m in trimmed)
    while trimmed and total > MAX_LLM_CHARS:
        trimmed.pop(0)
        total = sum(len(m.get("content") or "") for m in trimmed)
    return trimmed
