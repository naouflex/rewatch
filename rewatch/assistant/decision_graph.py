"""Build and stream a decision graph for assistant turns."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

ActivityCallback = Callable[[dict[str, Any]], None]


def _now_ms() -> int:
    return int(time.time() * 1000)


class DecisionGraph:
    """Tracks assistant planning steps, tool actions, and outcomes as a graph."""

    def __init__(self, on_activity: Optional[ActivityCallback] = None):
        self._on_activity = on_activity
        self._counter = 0
        self.nodes: list[dict[str, Any]] = []
        self._root_id: Optional[str] = None
        self._step_id: Optional[str] = None

    def _next_id(self) -> str:
        self._counter += 1
        return f"g{self._counter}"

    def _append(self, node: dict[str, Any]) -> dict[str, Any]:
        self.nodes.append(node)
        self._emit()
        return node

    def _emit(self) -> None:
        if self._on_activity:
            self._on_activity({"type": "graph", "nodes": self.nodes})

    def _update(self, node_id: str, **fields: Any) -> None:
        for node in self.nodes:
            if node["id"] == node_id:
                node.update(fields)
                break
        self._emit()

    def start(self, label: str = "Analyzing your request") -> str:
        node_id = self._next_id()
        self._root_id = node_id
        self._append(
            {
                "id": node_id,
                "parent_id": None,
                "type": "root",
                "label": label,
                "status": "running",
                "started_at": _now_ms(),
            }
        )
        return node_id

    def add_status(self, message: str) -> str:
        parent_id = self._step_id or self._root_id
        node_id = self._next_id()
        self._append(
            {
                "id": node_id,
                "parent_id": parent_id,
                "type": "status",
                "label": message,
                "status": "done",
                "started_at": _now_ms(),
                "finished_at": _now_ms(),
            }
        )
        return node_id

    def start_step(self, round_idx: int, label: str = "Planning next step") -> str:
        parent_id = self._root_id
        node_id = self._next_id()
        self._step_id = node_id
        self._append(
            {
                "id": node_id,
                "parent_id": parent_id,
                "type": "step",
                "label": label if round_idx > 0 else "Planning response",
                "status": "running",
                "round": round_idx + 1,
                "started_at": _now_ms(),
            }
        )
        return node_id

    def finish_step(self) -> None:
        if not self._step_id:
            return
        self._update(self._step_id, status="done", finished_at=_now_ms())
        self._step_id = None

    def add_decision(
        self,
        *,
        label: str,
        detail: Optional[str] = None,
        tool_names: Optional[list[str]] = None,
    ) -> str:
        parent_id = self._step_id or self._root_id
        node_id = self._next_id()
        self._append(
            {
                "id": node_id,
                "parent_id": parent_id,
                "type": "decision",
                "label": label,
                "detail": (detail or "").strip() or None,
                "tools": tool_names or [],
                "status": "done",
                "started_at": _now_ms(),
                "finished_at": _now_ms(),
            }
        )
        return node_id

    def start_tool(
        self,
        *,
        node_id: str,
        tool: str,
        label: str,
        arguments: Optional[dict[str, Any]] = None,
    ) -> str:
        parent_id = self._step_id or self._root_id
        graph_id = self._next_id()
        self._append(
            {
                "id": graph_id,
                "parent_id": parent_id,
                "type": "tool",
                "ref_id": node_id,
                "tool": tool,
                "label": label,
                "arguments": arguments or {},
                "status": "running",
                "started_at": _now_ms(),
            }
        )
        return graph_id

    def finish_tool(
        self,
        graph_id: str,
        *,
        label: Optional[str] = None,
        result_summary: Optional[str] = None,
        error: Optional[str] = None,
        resource_ids: Optional[dict[str, int]] = None,
    ) -> None:
        fields: dict[str, Any] = {
            "status": "error" if error else "done",
            "finished_at": _now_ms(),
        }
        if label:
            fields["label"] = label
        if result_summary:
            fields["result_summary"] = result_summary
        if error:
            fields["error"] = error
        if resource_ids:
            fields["resource_ids"] = resource_ids
        self._update(graph_id, **fields)

    def complete(self, *, label: str = "Reply ready", parent_id: Optional[str] = None) -> str:
        if self._step_id:
            self.finish_step()
        if self._root_id:
            self._update(self._root_id, status="done", finished_at=_now_ms(), label=label)

        resolved_parent = parent_id or self._root_id
        node_id = self._next_id()
        self._append(
            {
                "id": node_id,
                "parent_id": resolved_parent,
                "type": "outcome",
                "label": label,
                "status": "done",
                "started_at": _now_ms(),
                "finished_at": _now_ms(),
            }
        )
        return node_id

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": self.nodes}


def _truncate_text(text: str, limit: int = 96) -> str:
    value = (text or "").strip().replace("\n", " ")
    if len(value) <= limit:
        return value or "Message"
    return value[: limit - 1] + "…"


def merge_thread_decision_graph(messages: list[dict[str, Any]], thread_id: str) -> dict[str, Any]:
    """Merge per-turn decision graphs into one conversation-level graph."""
    nodes: list[dict[str, Any]] = []
    previous_anchor_id: Optional[str] = None
    turn_index = 0

    for message in messages:
        role = message.get("role")
        if role == "user":
            user_id = f"turn{turn_index}_user"
            nodes.append(
                {
                    "id": user_id,
                    "parent_id": previous_anchor_id,
                    "type": "user",
                    "label": _truncate_text(message.get("content") or "", limit=10000),
                    "content": message.get("content") or "",
                    "status": "done",
                    "turn": turn_index,
                    "turn_label": f"Turn {turn_index + 1}",
                }
            )
            previous_anchor_id = user_id
            continue

        if role != "assistant":
            continue

        turn_nodes = (message.get("decision_graph") or {}).get("nodes") or []
        if not turn_nodes:
            turn_index += 1
            continue

        id_map: dict[str, str] = {}
        turn_outcome_id: Optional[str] = None
        for node in turn_nodes:
            old_id = node["id"]
            new_id = f"turn{turn_index}_{old_id}"
            id_map[old_id] = new_id

            parent_id = node.get("parent_id")
            if parent_id and parent_id in id_map:
                new_parent_id = id_map[parent_id]
            elif parent_id is None:
                new_parent_id = previous_anchor_id
            else:
                new_parent_id = previous_anchor_id

            nodes.append(
                {
                    **node,
                    "id": new_id,
                    "parent_id": new_parent_id,
                    "turn": turn_index,
                }
            )
            if node.get("type") == "outcome":
                turn_outcome_id = new_id

        reply_text = (message.get("content") or "").strip()
        if reply_text and turn_outcome_id:
            for node in nodes:
                if node["id"] == turn_outcome_id:
                    node["reply_content"] = reply_text
                    node["detail"] = reply_text
                    break

        previous_anchor_id = turn_outcome_id or next(reversed(id_map.values()), previous_anchor_id)
        turn_index += 1

    return {"thread_id": thread_id, "nodes": nodes}
