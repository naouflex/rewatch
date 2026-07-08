import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import ApartmentOutlined from "@ant-design/icons/ApartmentOutlined";
import ZoomInOutlined from "@ant-design/icons/ZoomInOutlined";
import ZoomOutOutlined from "@ant-design/icons/ZoomOutOutlined";
import CompressOutlined from "@ant-design/icons/CompressOutlined";
import NodeCollapseOutlined from "@ant-design/icons/NodeCollapseOutlined";
import NodeExpandOutlined from "@ant-design/icons/NodeExpandOutlined";

import { identifyActionGroups, layoutConversationGraph } from "./conversationGraph";

import "./AssistantConversationGraph2D.less";

const MIN_ZOOM = 0.35;
const MAX_ZOOM = 2.5;
const ZOOM_STEP = 1.15;

function clampZoom(value) {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value));
}

function nodeClasses(node) {
  return cx("assistant-conversation-graph__node", node.type, node.status, {
    "is-live": node.id?.includes("live_"),
    "is-user": node.isUser,
    "is-group": node.isGroup,
    "is-group-header": node.isGroupHeader,
    "is-interactive": node.isGroup || node.isGroupHeader || node.isTextCollapsible,
    "is-text-expanded": node.textExpanded,
  });
}

function ConversationGraphNode({ node, onToggleGroup, onToggleText }) {
  const titleStartY = node.isUser ? 40 : node.isGroup ? 34 : 34;
  const metaStartY = titleStartY + node.titleLines.length * 14 + 4;
  const bodyX = node.isUser ? 8 : 0;
  const bodyWidth = node.width - (node.isUser ? 8 : 0);
  const toggleY = node.height - 10;

  const handleClick = event => {
    event.stopPropagation();
    if ((node.isGroup || node.isGroupHeader) && onToggleGroup) {
      onToggleGroup(node.groupId);
    }
  };

  const handleTextToggle = event => {
    event.stopPropagation();
    if (onToggleText) {
      onToggleText(node.id);
    }
  };

  const actionLabel = node.isGroupHeader ? "▾ wrap" : node.isGroup ? "▸ expand" : null;

  return (
    <g
      transform={`translate(${node.x}, ${node.y})`}
      className={nodeClasses(node)}
      style={node.isGroup || node.isGroupHeader ? { pointerEvents: "all", cursor: "pointer" } : undefined}
      onPointerDown={node.isGroup || node.isGroupHeader ? event => event.stopPropagation() : undefined}
      onClick={node.isGroup || node.isGroupHeader ? handleClick : undefined}
      role={node.isGroup || node.isGroupHeader ? "button" : undefined}
      aria-label={
        node.isGroupHeader
          ? `Wrap ${node.memberCount} actions`
          : node.isGroup
            ? `Expand ${node.memberCount} actions`
            : undefined
      }>
      <title>{node.tooltip}</title>
      {node.isUser && (
        <>
          <rect className="assistant-conversation-graph__node-stripe" x="0" y="0" width="8" height={node.height} rx="4" />
          <circle className="assistant-conversation-graph__node-avatar" cx="24" cy="20" r="12" />
          <text className="assistant-conversation-graph__node-avatar-label" x="24" y="24" textAnchor="middle">
            You
          </text>
        </>
      )}
      <rect
        className="assistant-conversation-graph__node-bg"
        x={bodyX}
        y="0"
        width={bodyWidth}
        height={node.height}
        rx={node.isUser ? "10" : "8"}
      />
      <text className="assistant-conversation-graph__node-type" x={node.contentX} y={node.isUser ? 18 : 16}>
        {node.isUser ? "YOUR MESSAGE" : node.isGroupHeader ? "WRAPPED ACTIONS" : node.isGroup ? "WRAPPED ACTIONS" : node.typeLabel}
      </text>
      {actionLabel && (
        <text className="assistant-conversation-graph__node-expand" x={node.width - 14} y={18} textAnchor="end">
          {actionLabel}
        </text>
      )}
      {node.isUser && node.turn_label && !actionLabel && (
        <text className="assistant-conversation-graph__node-turn" x={node.width - 14} y={18} textAnchor="end">
          {node.turn_label}
        </text>
      )}
      {node.titleLines.map((line, index) => (
        <text
          key={`${node.id}-title-${index}`}
          className="assistant-conversation-graph__node-label"
          x={node.contentX}
          y={titleStartY + index * 14}>
          {line}
        </text>
      ))}
      {node.metaLines.map((line, index) => (
        <text
          key={`${node.id}-meta-${index}`}
          className={cx("assistant-conversation-graph__node-meta", {
            "is-error": line.startsWith("Error:"),
            "is-result": line.startsWith("Result:"),
          })}
          x={node.contentX}
          y={metaStartY + index * 13}>
          {line}
        </text>
      ))}
      {(node.showMoreLabel || node.showLessLabel) && (
        <text
          className="assistant-conversation-graph__node-toggle"
          x={node.contentX}
          y={toggleY}
          style={{ pointerEvents: "all", cursor: "pointer" }}
          onPointerDown={handleTextToggle}
          onClick={handleTextToggle}>
          {node.showMoreLabel || node.showLessLabel}
        </text>
      )}
    </g>
  );
}

ConversationGraphNode.propTypes = {
  node: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  onToggleGroup: PropTypes.func,
  onToggleText: PropTypes.func,
};

ConversationGraphNode.defaultProps = {
  onToggleGroup: null,
  onToggleText: null,
};

function edgePath(edge) {
  if (edge.type === "horizontal") {
    const gap = Math.max(36, (edge.x2 - edge.x1) * 0.45);
    const c1x = edge.x1 + gap;
    const c2x = edge.x2 - gap;
    return `M ${edge.x1} ${edge.y1} C ${c1x} ${edge.y1}, ${c2x} ${edge.y2}, ${edge.x2} ${edge.y2}`;
  }

  const midY = edge.y1 + (edge.y2 - edge.y1) / 2;
  return `M ${edge.x1} ${edge.y1} C ${edge.x1} ${midY}, ${edge.x2} ${midY}, ${edge.x2} ${edge.y2}`;
}

export default function AssistantConversationGraph2D({ graph, loading, emptyLabel, embedded }) {
  const [expandedGroups, setExpandedGroups] = useState(() => new Set());
  const [expandedTextNodes, setExpandedTextNodes] = useState(() => new Set());
  const actionGroups = useMemo(() => identifyActionGroups(graph?.nodes || []), [graph]);
  const layout = useMemo(
    () => layoutConversationGraph(graph?.nodes || [], { expandedGroups, expandedTextNodes }),
    [graph, expandedGroups, expandedTextNodes]
  );
  const [zoom, setZoom] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const canvasWrapRef = useRef(null);
  const pendingScrollRef = useRef(null);
  const dragStateRef = useRef(null);

  const zoomAt = useCallback(
    (pointX, pointY, nextZoom) => {
      const wrap = canvasWrapRef.current;
      if (!wrap) {
        return;
      }

      const clampedZoom = clampZoom(nextZoom);
      if (clampedZoom === zoom) {
        return;
      }

      const ratio = clampedZoom / zoom;
      pendingScrollRef.current = {
        scrollLeft: (wrap.scrollLeft + pointX) * ratio - pointX,
        scrollTop: (wrap.scrollTop + pointY) * ratio - pointY,
      };
      setZoom(clampedZoom);
    },
    [zoom]
  );

  const zoomIn = useCallback(() => {
    const wrap = canvasWrapRef.current;
    if (!wrap) {
      return;
    }
    zoomAt(wrap.clientWidth / 2, wrap.clientHeight / 2, zoom * ZOOM_STEP);
  }, [zoom, zoomAt]);

  const zoomOut = useCallback(() => {
    const wrap = canvasWrapRef.current;
    if (!wrap) {
      return;
    }
    zoomAt(wrap.clientWidth / 2, wrap.clientHeight / 2, zoom / ZOOM_STEP);
  }, [zoom, zoomAt]);

  const resetZoom = useCallback(() => {
    pendingScrollRef.current = { scrollLeft: 0, scrollTop: 0 };
    setZoom(1);
  }, []);

  useEffect(() => {
    setExpandedGroups(new Set());
    setExpandedTextNodes(new Set());
  }, [graph?.thread_id]);

  const toggleGroup = useCallback(groupId => {
    setExpandedGroups(current => {
      const next = new Set(current);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  }, []);

  const toggleText = useCallback(nodeId => {
    setExpandedTextNodes(current => {
      const next = new Set(current);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  const collapseAllGroups = useCallback(() => {
    setExpandedGroups(new Set());
  }, []);

  const expandAllGroups = useCallback(() => {
    setExpandedGroups(new Set(actionGroups.map(group => group.id)));
  }, [actionGroups]);

  const endDrag = useCallback(() => {
    dragStateRef.current = null;
    setIsDragging(false);
  }, []);

  const handlePointerDown = useCallback(event => {
    if (event.button !== 0) {
      return;
    }

    if (
      event.target.closest(
        ".assistant-conversation-graph__zoom-controls, .assistant-conversation-graph__timeline-hint, button, .assistant-conversation-graph__node.is-interactive, .assistant-conversation-graph__node-toggle"
      )
    ) {
      return;
    }

    const wrap = canvasWrapRef.current;
    if (!wrap) {
      return;
    }

    dragStateRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      scrollLeft: wrap.scrollLeft,
      scrollTop: wrap.scrollTop,
    };
    setIsDragging(true);
    wrap.setPointerCapture(event.pointerId);
    event.preventDefault();
  }, []);

  const handlePointerMove = useCallback(event => {
    const drag = dragStateRef.current;
    const wrap = canvasWrapRef.current;
    if (!drag || !wrap || drag.pointerId !== event.pointerId) {
      return;
    }

    wrap.scrollLeft = drag.scrollLeft - (event.clientX - drag.startX);
    wrap.scrollTop = drag.scrollTop - (event.clientY - drag.startY);
    event.preventDefault();
  }, []);

  const handlePointerUp = useCallback(
    event => {
      const drag = dragStateRef.current;
      const wrap = canvasWrapRef.current;
      if (!drag || drag.pointerId !== event.pointerId) {
        return;
      }

      wrap?.releasePointerCapture(event.pointerId);
      endDrag();
    },
    [endDrag]
  );

  useLayoutEffect(() => {
    const wrap = canvasWrapRef.current;
    const pendingScroll = pendingScrollRef.current;
    if (!wrap || !pendingScroll) {
      return;
    }

    wrap.scrollLeft = pendingScroll.scrollLeft;
    wrap.scrollTop = pendingScroll.scrollTop;
    pendingScrollRef.current = null;
  }, [zoom]);

  useEffect(() => {
    const wrap = canvasWrapRef.current;
    if (!wrap || layout.nodes.length === 0) {
      return undefined;
    }

    const onWheel = event => {
      const rect = wrap.getBoundingClientRect();
      const pointX = event.clientX - rect.left;
      const pointY = event.clientY - rect.top;

      if (event.shiftKey) {
        event.preventDefault();
        wrap.scrollLeft += event.deltaY || event.deltaX;
        return;
      }

      event.preventDefault();
      const direction = event.deltaY < 0 ? 1 : -1;
      const nextZoom = direction > 0 ? zoom * ZOOM_STEP : zoom / ZOOM_STEP;
      zoomAt(pointX, pointY, nextZoom);
    };

    wrap.addEventListener("wheel", onWheel, { passive: false });
    return () => wrap.removeEventListener("wheel", onWheel);
  }, [layout.nodes.length, zoom, zoomAt]);

  const scaledWidth = layout.width * zoom;
  const scaledHeight = layout.height * zoom;
  const zoomPercent = Math.round(zoom * 100);

  return (
    <div className={cx("assistant-conversation-graph", { "is-embedded": embedded })}>
      {!embedded && (
        <div className="assistant-conversation-graph__header">
          <ApartmentOutlined aria-hidden="true" />
          <div>
            <h3>Conversation graph</h3>
            <p>Decisions and actions across this chat</p>
          </div>
          {layout.nodes.length > 0 && (
            <span className="assistant-conversation-graph__count">{layout.nodes.length}</span>
          )}
        </div>
      )}

      <div
        className={cx("assistant-conversation-graph__canvas-wrap", {
          "is-pannable": layout.nodes.length > 0,
          "is-dragging": isDragging,
        })}
        ref={canvasWrapRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}>
        {loading && <div className="assistant-conversation-graph__empty">Loading graph…</div>}
        {!loading && layout.nodes.length === 0 && (
          <div className="assistant-conversation-graph__empty">{emptyLabel}</div>
        )}
        {!loading && layout.nodes.length > 0 && (
          <>
            <div className="assistant-conversation-graph__timeline-hint">
              Drag to pan · scroll to zoom · Shift + scroll through time · click wrapped actions or show more
            </div>
            <div className="assistant-conversation-graph__zoom-controls">
              {actionGroups.length > 0 && (
                <>
                  <button
                    type="button"
                    className="assistant-conversation-graph__zoom-btn"
                    onClick={collapseAllGroups}
                    aria-label="Wrap all action groups"
                    title="Wrap actions">
                    <NodeCollapseOutlined />
                  </button>
                  <button
                    type="button"
                    className="assistant-conversation-graph__zoom-btn"
                    onClick={expandAllGroups}
                    aria-label="Unwrap all action groups"
                    title="Unwrap actions">
                    <NodeExpandOutlined />
                  </button>
                </>
              )}
              <button type="button" className="assistant-conversation-graph__zoom-btn" onClick={zoomOut} aria-label="Zoom out">
                <ZoomOutOutlined />
              </button>
              <span className="assistant-conversation-graph__zoom-label">{zoomPercent}%</span>
              <button type="button" className="assistant-conversation-graph__zoom-btn" onClick={zoomIn} aria-label="Zoom in">
                <ZoomInOutlined />
              </button>
              <button
                type="button"
                className="assistant-conversation-graph__zoom-btn"
                onClick={resetZoom}
                aria-label="Reset zoom"
                title="Reset zoom">
                <CompressOutlined />
              </button>
            </div>
            <svg
              className="assistant-conversation-graph__canvas"
              width={scaledWidth}
              height={scaledHeight}
              viewBox={`0 0 ${layout.width} ${layout.height}`}
              role="img"
              aria-label="Assistant conversation decision graph"
            >
              <defs>
                <marker
                  id="assistant-graph-arrow"
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" className="assistant-conversation-graph__arrow-head" />
                </marker>
              </defs>

              {layout.timelineY != null && layout.turns?.length > 1 && (
                <line
                  x1={layout.turns[0].x}
                  y1={layout.timelineY}
                  x2={layout.width - 36}
                  y2={layout.timelineY}
                  className="assistant-conversation-graph__timeline-rail"
                />
              )}

              {layout.turns?.map(turn => (
                <g key={`turn-${turn.turn}`} className="assistant-conversation-graph__turn-marker">
                  <text
                    x={turn.x + turn.width / 2}
                    y={30}
                    textAnchor="middle"
                    className="assistant-conversation-graph__turn-label">
                    {turn.label}
                  </text>
                  <line
                    x1={turn.x + turn.width / 2}
                    y1={38}
                    x2={turn.x + turn.width / 2}
                    y2={layout.height - 20}
                    className="assistant-conversation-graph__turn-divider"
                  />
                </g>
              ))}

              {layout.edges.map(edge => (
                <path
                  key={edge.id}
                  d={edgePath(edge)}
                  className={cx("assistant-conversation-graph__edge", edge.type)}
                  markerEnd="url(#assistant-graph-arrow)"
                />
              ))}
            {layout.nodes.map(node => (
              <ConversationGraphNode key={node.id} node={node} onToggleGroup={toggleGroup} onToggleText={toggleText} />
            ))}
          </svg>
          </>
        )}
      </div>
    </div>
  );
}

AssistantConversationGraph2D.propTypes = {
  graph: PropTypes.shape({
    thread_id: PropTypes.string,
    nodes: PropTypes.arrayOf(PropTypes.object),
  }),
  loading: PropTypes.bool,
  emptyLabel: PropTypes.string,
  embedded: PropTypes.bool,
};

AssistantConversationGraph2D.defaultProps = {
  graph: null,
  loading: false,
  emptyLabel: "Start the conversation to build the graph.",
  embedded: false,
};
