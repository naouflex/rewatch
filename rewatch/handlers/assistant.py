import json
import logging
import queue
import threading

from flask import Response, copy_current_request_context, request, stream_with_context
from flask_restful import abort

from rewatch import models, settings
from rewatch.assistant import storage
from rewatch.assistant.decision_graph import merge_thread_decision_graph
from rewatch.assistant.previews import render_dashboard_svg, render_query_svg, render_visualization_svg
from rewatch.assistant.service import chat
from rewatch.assistant.query_generation import generate_query
from rewatch.handlers.base import BaseResource, get_object_or_404
from rewatch.models import db
from rewatch.permissions import require_access, view_only

logger = logging.getLogger(__name__)


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


def _user_api_key(user):
    api_key = user.api_key
    if api_key:
        return api_key
    user.regenerate_api_key()
    db.session.commit()
    return user.api_key


def _parse_chat_payload(payload):
    thread_id = payload.get("thread_id")
    message = (payload.get("message") or "").strip()
    page_context = payload.get("page_context")

    if not message and payload.get("messages"):
        for item in reversed(payload["messages"]):
            if item.get("role") == "user" and item.get("content"):
                message = item["content"].strip()
                break

    if not message:
        abort(400, message="message is required.")
    if page_context is not None and not isinstance(page_context, dict):
        page_context = None
    return thread_id, message, page_context


def _prepare_thread(current_user, current_org, thread_id, message):
    if thread_id:
        thread = storage.get_thread(thread_id, current_user, current_org)
    else:
        thread = storage.create_thread(current_user, current_org)
        thread_id = thread.id

    storage.add_message(thread_id, "user", message)
    history = storage.list_messages(thread_id, current_user, current_org)
    llm_messages = storage.fit_messages_for_llm(history)
    return thread, thread_id, llm_messages


def _finalize_chat(current_user, current_org, thread_id, message, result, resource):
    storage.add_message(
        thread_id,
        "assistant",
        result["reply"],
        decision_graph=result.get("decision_graph"),
    )
    thread = storage.touch_thread(thread_id, current_user, current_org, user_message=message)
    resource.record_event({"action": "assistant_chat", "object_id": thread_id, "object_type": "assistant"})
    return {
        "thread_id": thread_id,
        "title": thread.title,
        "reply": result["reply"],
        "messages": storage.list_messages(thread_id, current_user, current_org),
    }


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


class AssistantThreadDecisionGraphResource(BaseResource):
    def get(self, thread_id):
        _ensure_assistant_enabled(self.current_user)
        messages = storage.list_messages(thread_id, self.current_user, self.current_org)
        return merge_thread_decision_graph(messages, thread_id)


class AssistantGenerateQueryResource(BaseResource):
    def post(self):
        _ensure_assistant_enabled(self.current_user)

        payload = request.get_json(force=True) or {}
        prompt = (payload.get("prompt") or "").strip()
        if not prompt:
            abort(400, message="prompt is required.")

        data_source_id = payload.get("data_source_id")
        if not data_source_id:
            abort(400, message="data_source_id is required.")

        data_source = get_object_or_404(models.DataSource.get_by_id_and_org, data_source_id, self.current_org)
        require_access(data_source, self.current_user, view_only)

        data_source_type = payload.get("data_source_type") or data_source.type
        data_source_name = payload.get("data_source_name") or data_source.name
        syntax = payload.get("syntax") or data_source.syntax or "sql"
        schema = payload.get("schema")
        existing_query = payload.get("existing_query")

        try:
            query_text = generate_query(
                prompt=prompt,
                data_source_type=data_source_type,
                data_source_name=data_source_name,
                syntax=syntax,
                schema=schema if isinstance(schema, list) else None,
                existing_query=existing_query,
            )
        except ValueError as exc:
            abort(400, message=str(exc))
        except Exception as exc:
            abort(500, message=str(exc))

        self.record_event(
            {
                "action": "assistant_generate_query",
                "object_id": data_source_id,
                "object_type": "data_source",
            }
        )
        return {"query": query_text}


class AssistantChatResource(BaseResource):
    def post(self):
        _ensure_assistant_enabled(self.current_user)

        payload = request.get_json(force=True) or {}
        thread_id, message, page_context = _parse_chat_payload(payload)
        thread, thread_id, llm_messages = _prepare_thread(self.current_user, self.current_org, thread_id, message)

        try:
            result = chat(
                messages=llm_messages,
                base_url=_assistant_base_url(),
                api_key=_user_api_key(self.current_user),
                help_base_url=_help_base_url(),
                page_context=page_context,
            )
        except Exception as exc:
            db.session.rollback()
            abort(500, message=str(exc))

        return _finalize_chat(self.current_user, self.current_org, thread_id, message, result, self)


class AssistantChatStreamResource(BaseResource):
    def post(self):
        _ensure_assistant_enabled(self.current_user)

        payload = request.get_json(force=True) or {}
        thread_id, message, page_context = _parse_chat_payload(payload)
        thread, thread_id, llm_messages = _prepare_thread(self.current_user, self.current_org, thread_id, message)

        user_api_key = _user_api_key(self.current_user)
        chat_base_url = _assistant_base_url()
        help_base_url = _help_base_url()

        events: queue.Queue = queue.Queue()
        result_holder: dict = {}
        error_holder: dict = {}

        def on_activity(event):
            events.put(event)

        def run_chat():
            try:
                # Background thread shares the request context but needs its own session.
                db.session.remove()
                result_holder["result"] = chat(
                    messages=llm_messages,
                    base_url=chat_base_url,
                    api_key=user_api_key,
                    help_base_url=help_base_url,
                    on_activity=on_activity,
                    page_context=page_context,
                )
                # Persist the reply even if the client disconnects mid-stream.
                result_holder["response"] = _finalize_chat(
                    self.current_user,
                    self.current_org,
                    thread_id,
                    message,
                    result_holder["result"],
                    self,
                )
            except Exception as exc:
                logger.exception("Assistant stream worker failed")
                error_holder["error"] = exc
                try:
                    db.session.rollback()
                except Exception:
                    pass
            finally:
                events.put({"type": "_done"})

        worker = threading.Thread(target=copy_current_request_context(run_chat), daemon=True)
        worker.start()

        def generate():
            while True:
                event = events.get()
                if event.get("type") == "_done":
                    break
                yield f"data: {json.dumps(event)}\n\n"

            if error_holder.get("error"):
                payload = {"type": "error", "message": str(error_holder["error"])}
                yield f"data: {json.dumps(payload)}\n\n"
                return

            response = result_holder.get("response")
            if response:
                yield f"data: {json.dumps({'type': 'complete', **response})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )


class AssistantVisualizationPreviewResource(BaseResource):
    def get(self, visualization_id):
        _ensure_assistant_enabled(self.current_user)
        visualization = get_object_or_404(
            models.Visualization.get_by_id_and_org,
            visualization_id,
            self.current_org,
        )
        query = visualization.query_rel
        require_access(query, self.current_user, view_only)
        svg = render_visualization_svg(visualization, query)
        return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "private, max-age=120"})


class AssistantQueryPreviewResource(BaseResource):
    def get(self, query_id):
        _ensure_assistant_enabled(self.current_user)
        query = get_object_or_404(models.Query.get_by_id_and_org, query_id, self.current_org)
        require_access(query, self.current_user, view_only)
        svg = render_query_svg(query)
        return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "private, max-age=120"})


class AssistantDashboardPreviewResource(BaseResource):
    def get(self, dashboard_id):
        _ensure_assistant_enabled(self.current_user)
        dashboard = get_object_or_404(models.Dashboard.get_by_id_and_org, dashboard_id, self.current_org)
        require_access(dashboard, self.current_user, view_only)
        svg = render_dashboard_svg(dashboard)
        return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "private, max-age=120"})
