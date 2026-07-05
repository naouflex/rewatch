from flask import request
from flask_restful import abort

from redash import settings
from redash.assistant import storage
from redash.assistant.service import chat
from redash.handlers.base import BaseResource
from redash.models import db


def _assistant_base_url():
    if settings.HOST:
        return settings.HOST.rstrip("/")
    return request.url_root.rstrip("/")


def _help_base_url():
    return (settings.HELP_BASE_URL or "https://naoufel.io").rstrip("/")


def _ensure_assistant_enabled(current_user):
    if not settings.ASSISTANT_ENABLED:
        abort(503, message="Assistant is disabled.")
    if not settings.OPENAI_API_KEY:
        abort(503, message="OpenAI API key is not configured.")
    if current_user.is_api_user():
        abort(403, message="Assistant is not available for API key sessions.")


class AssistantStatusResource(BaseResource):
    def get(self):
        return {
            "enabled": bool(settings.ASSISTANT_ENABLED and settings.OPENAI_API_KEY),
            "model": settings.OPENAI_MODEL if settings.OPENAI_API_KEY else None,
        }


class AssistantThreadListResource(BaseResource):
    def get(self):
        _ensure_assistant_enabled(self.current_user)
        return storage.list_threads(self.current_user, self.current_org)

    def post(self):
        _ensure_assistant_enabled(self.current_user)
        thread = storage.create_thread(self.current_user, self.current_org)
        self.record_event({"action": "assistant_thread_create", "object_id": thread.id, "object_type": "assistant"})
        return {"id": thread.id, "title": thread.title, "updated_at": thread.updated_at, "preview": ""}


class AssistantThreadResource(BaseResource):
    def delete(self, thread_id):
        _ensure_assistant_enabled(self.current_user)
        storage.delete_thread(thread_id, self.current_user, self.current_org)
        self.record_event({"action": "assistant_thread_delete", "object_id": thread_id, "object_type": "assistant"})
        return {"deleted": True}


class AssistantThreadMessagesResource(BaseResource):
    def get(self, thread_id):
        _ensure_assistant_enabled(self.current_user)
        return storage.list_messages(thread_id, self.current_user, self.current_org)


class AssistantChatResource(BaseResource):
    def post(self):
        _ensure_assistant_enabled(self.current_user)

        payload = request.get_json(force=True) or {}
        thread_id = payload.get("thread_id")
        message = (payload.get("message") or "").strip()

        # Legacy bubble payload: last user turn from a messages array.
        if not message and payload.get("messages"):
            for item in reversed(payload["messages"]):
                if item.get("role") == "user" and item.get("content"):
                    message = item["content"].strip()
                    break

        if not message:
            abort(400, message="message is required.")

        if thread_id:
            thread = storage.get_thread(thread_id, self.current_user, self.current_org)
        else:
            thread = storage.create_thread(self.current_user, self.current_org)
            thread_id = thread.id

        storage.add_message(thread_id, "user", message)
        history = storage.list_messages(thread_id, self.current_user, self.current_org)
        llm_messages = storage.fit_messages_for_llm(history)

        try:
            result = chat(
                messages=llm_messages,
                base_url=_assistant_base_url(),
                api_key=self.current_user.api_key,
                help_base_url=_help_base_url(),
            )
        except Exception as exc:
            db.session.rollback()
            abort(500, message=str(exc))

        storage.add_message(thread_id, "assistant", result["reply"])
        storage.touch_thread(thread, user_message=message)
        db.session.refresh(thread)

        self.record_event({"action": "assistant_chat", "object_id": thread_id, "object_type": "assistant"})
        return {
            "thread_id": thread_id,
            "title": thread.title,
            "reply": result["reply"],
            "messages": storage.list_messages(thread_id, self.current_user, self.current_org),
        }
