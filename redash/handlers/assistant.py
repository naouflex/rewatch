from flask import request
from flask_restful import abort

from redash import settings
from redash.assistant.service import chat
from redash.handlers.base import BaseResource


def _assistant_base_url():
    if settings.HOST:
        return settings.HOST.rstrip("/")
    return request.url_root.rstrip("/")


def _help_base_url():
    return (settings.HELP_BASE_URL or "https://naoufel.io").rstrip("/")


class AssistantStatusResource(BaseResource):
    def get(self):
        return {
            "enabled": bool(settings.ASSISTANT_ENABLED and settings.OPENAI_API_KEY),
            "model": settings.OPENAI_MODEL if settings.OPENAI_API_KEY else None,
        }


class AssistantChatResource(BaseResource):
    def post(self):
        if not settings.ASSISTANT_ENABLED:
            abort(503, message="Assistant is disabled.")
        if not settings.OPENAI_API_KEY:
            abort(503, message="OpenAI API key is not configured.")
        if self.current_user.is_api_user():
            abort(403, message="Assistant is not available for API key sessions.")

        payload = request.get_json(force=True) or {}
        messages = payload.get("messages") or []
        if not messages or messages[-1].get("role") != "user":
            abort(400, message="messages must end with a user message.")

        # Keep only user/assistant roles from the client.
        clean_messages = [
            {"role": m["role"], "content": m.get("content", "")}
            for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]

        try:
            result = chat(
                messages=clean_messages,
                base_url=_assistant_base_url(),
                api_key=self.current_user.api_key,
                help_base_url=_help_base_url(),
            )
        except Exception as exc:
            abort(500, message=str(exc))

        self.record_event({"action": "assistant_chat", "object_type": "assistant"})
        return result
