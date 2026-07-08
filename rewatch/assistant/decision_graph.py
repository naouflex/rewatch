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
        self._update(graph_id, **fields)

    def complete(self, *, label: str = "Reply ready") -> str:
        if self._step_id:
            self.finish_step()
        if self._root_id:
            self._update(self._root_id, status="done", finished_at=_now_ms(), label=label)

        parent_id = self._root_id
        node_id = self._next_id()
        self._append(
            {
                "id": node_id,
                "parent_id": parent_id,
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
