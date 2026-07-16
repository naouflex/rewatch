"""Database persistence for assistant chat threads."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from rewatch.assistant.llm_config import assistant_max_llm_chars, assistant_max_llm_messages
from rewatch.models import AssistantMessage, AssistantThread, db

MAX_THREADS = 30
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
        if not thread.messages.count():
            continue
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


def list_messages(thread_id: str, user, org) -> list[dict[str, Any]]:
    thread = get_thread(thread_id, user, org)
    results = []
    for message in thread.messages.order_by(AssistantMessage.id):
        item: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.decision_graph:
            item["decision_graph"] = message.decision_graph
        results.append(item)
    return results


def add_message(
    thread_id: str,
    role: str,
    content: str,
    decision_graph: Optional[dict[str, Any]] = None,
) -> AssistantMessage:
    message = AssistantMessage(
        thread_id=thread_id,
        role=role,
        content=content,
        decision_graph=decision_graph,
    )
    db.session.add(message)
    db.session.flush()
    return message


def save_user_message(thread_id: str, content: str) -> AssistantMessage:
    """Persist the user turn before a long-running assistant reply starts."""
    message = add_message(thread_id, "user", content)
    db.session.commit()
    return message


def touch_thread(
    thread_id: str,
    user,
    org,
    user_message: Optional[str] = None,
) -> AssistantThread:
    thread = get_thread(thread_id, user, org)
    if thread.title == DEFAULT_TITLE and user_message:
        thread.title = _title_from_message(user_message)
    from rewatch.utils import utcnow

    thread.updated_at = utcnow()
    db.session.commit()
    return thread


def fit_messages_for_llm(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    max_messages = assistant_max_llm_messages()
    max_chars = assistant_max_llm_chars()
    trimmed = messages[-max_messages:]
    total = sum(len(m.get("content") or "") for m in trimmed)
    # Drop oldest messages first, but never the newest one — it carries the
    # user's current request.
    while len(trimmed) > 1 and total > max_chars:
        total -= len(trimmed.pop(0).get("content") or "")
    if trimmed and total > max_chars:
        newest = dict(trimmed[-1])
        newest["content"] = (newest.get("content") or "")[:max_chars]
        trimmed[-1] = newest
    return trimmed


def prepare_messages_for_llm(messages: list[dict[str, Any]]) -> tuple[list[dict[str, str]], Optional[str]]:
    """Trim chat history and build prior-turn tool context for the LLM."""
    from rewatch.assistant.session_context import format_session_context

    text_messages = [
        {"role": message["role"], "content": message["content"]}
        for message in messages
        if message.get("role") in ("user", "assistant") and message.get("content")
    ]
    session_context = format_session_context(messages)
    return fit_messages_for_llm(text_messages), session_context
