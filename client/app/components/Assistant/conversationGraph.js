const TYPE_LABELS = {
  user: "Your message",
  root: "Analyzing",
  step: "Planning",
  decision: "Decision",
  tool: "Tool",
  outcome: "Assistant reply",
  status: "Update",
};

const COLLAPSED_TITLE_LINES = 3;
const COLLAPSED_META_LINES = 2;
const TEXT_TOGGLE_HEIGHT = 16;

function hasMoreLines(fullLines, collapsedLines) {
  if (fullLines.length > collapsedLines.length) {
    return true;
  }
  return fullLines.join(" ").length > collapsedLines.join(" ").length + 2;
}

function normalizeContent(text) {
  return (text || "").trim().replace(/\n/g, " ") || "Message";
}

function wrapText(text, maxChars, maxLines = Infinity) {
  const words = (text || "").trim().split(/\s+/).filter(Boolean);
  if (!words.length) {
    return ["—"];
  }

  const lines = [];
  let current = "";

  words.forEach(word => {
    const next = current ? `${current} ${word}` : word;
    if (next.length <= maxChars) {
      current = next;
      return;
    }

    if (current) {
      lines.push(current);
      current = word;
    } else {
      lines.push(`${word.slice(0, maxChars - 1)}…`);
      current = "";
    }

      if (lines.length >= maxLines && Number.isFinite(maxLines)) {
      current = "";
    }
  });

  if (current && (lines.length < maxLines || !Number.isFinite(maxLines))) {
    lines.push(current);
  }

  if (Number.isFinite(maxLines) && lines.length > maxLines) {
    return lines.slice(0, maxLines);
  }

  if (
    Number.isFinite(maxLines) &&
    lines.length === maxLines &&
    words.join(" ").length > lines.join(" ").length
  ) {
    const last = lines[maxLines - 1];
    lines[maxLines - 1] = last.length > maxChars - 1 ? `${last.slice(0, maxChars - 2)}…` : `${last}…`;
  }

  return lines.length ? lines : ["—"];
}

function summarizeArguments(args) {
  if (!args || typeof args !== "object") {
    return null;
  }

  const entries = Object.entries(args);
  if (!entries.length) {
    return null;
  }

  return entries
    .map(([key, value]) => {
      const raw = typeof value === "string" ? value : JSON.stringify(value);
      return `${key}: ${raw}`;
    })
    .join("\n");
}

function buildMemberDetailLines(node) {
  const lines = [`${TYPE_LABELS[node.type] || node.type}: ${node.label || "—"}`];
  if (node.detail) {
    lines.push(node.detail.trim());
  }
  if (node.tool) {
    lines.push(`Action: ${node.tool.replace(/_/g, " ")}`);
  }
  if (node.tools?.length) {
    lines.push(`Considering: ${node.tools.map(tool => tool.replace(/_/g, " ")).join(", ")}`);
  }
  if (node.result_summary) {
    lines.push(`Result: ${node.result_summary}`);
  }
  if (node.error) {
    lines.push(`Error: ${node.error}`);
  }
  const argsLine = summarizeArguments(node.arguments);
  if (argsLine) {
    lines.push(argsLine);
  }
  if (node.reply_content) {
    lines.push(node.reply_content);
  }
  return lines;
}

function buildTooltip(node, detailLines) {
  const parts = [TYPE_LABELS[node.type] || node.type];
  if (node.label) {
    parts.push(node.label);
  }
  if (node.reply_content && node.reply_content !== node.label) {
    parts.push(node.reply_content);
  }
  detailLines.forEach(line => {
    if (!parts.includes(line)) {
      parts.push(line);
    }
  });
  if (node.error && !parts.includes(node.error)) {
    parts.push(node.error);
  }
  return parts.join("\n");
}

export function buildNodeDetailContent(node, { groupMembers = null } = {}) {
  if (node?.isGroup && groupMembers?.length) {
    return groupMembers.map(member => buildMemberDetailLines(member).join("\n")).join("\n\n—\n\n");
  }

  if (!node) {
    return "";
  }

  return buildMemberDetailLines(node).join("\n");
}

function isComposingReply(node) {
  return node.type === "decision" && /composing final reply/i.test(node.label || "");
}

function isReplyAnchor(node) {
  return node.type === "user" || node.type === "outcome" || isComposingReply(node);
}

function isAnchorNode(node) {
  return isReplyAnchor(node);
}

function isCollapsibleAction(node) {
  return !isAnchorNode(node);
}

function sortTurnNodes(turnNodes, nodeOrder) {
  return [...turnNodes].sort((left, right) => {
    if (left.type === "outcome" && right.type !== "outcome") {
      return 1;
    }
    if (right.type === "outcome" && left.type !== "outcome") {
      return -1;
    }
    return (nodeOrder.get(left.id) ?? 0) - (nodeOrder.get(right.id) ?? 0);
  });
}

export function identifyActionGroups(nodes = []) {
  const nodeOrder = new Map();
  nodes.forEach((node, index) => {
    nodeOrder.set(node.id, index);
  });

  const turns = [...new Set(nodes.map(node => node.turn ?? 0))].sort((a, b) => a - b);
  const groups = [];

  turns.forEach(turn => {
    const turnNodes = nodes.filter(node => (node.turn ?? 0) === turn);
    const sorted = sortTurnNodes(turnNodes, nodeOrder);
    let current = null;

    sorted.forEach(node => {
      if (!isCollapsibleAction(node)) {
        if (current?.nodes.length >= 2) {
          groups.push(current);
        }
        current = null;
        return;
      }

      if (!current) {
        current = {
          id: `group-turn${turn}-${groups.length}`,
          turn,
          nodes: [],
          nodeIds: [],
        };
      }

      current.nodes.push(node);
      current.nodeIds.push(node.id);
    });

    if (current?.nodes.length >= 2) {
      groups.push(current);
    }
  });

  return groups;
}

function summarizeActionGroup(group) {
  const toolCount = group.nodes.filter(node => node.type === "tool").length;
  const decisionCount = group.nodes.filter(node => node.type === "decision").length;
  const otherCount = group.nodes.length - toolCount - decisionCount;
  const parts = [];

  if (toolCount) {
    parts.push(`${toolCount} tool${toolCount === 1 ? "" : "s"}`);
  }
  if (decisionCount) {
    parts.push(`${decisionCount} decision${decisionCount === 1 ? "" : "s"}`);
  }
  if (otherCount) {
    parts.push(`${otherCount} step${otherCount === 1 ? "" : "s"}`);
  }

  const previewNode =
    [...group.nodes].reverse().find(node => node.type === "tool") ||
    group.nodes[group.nodes.length - 1];

  return {
    parts: parts.join(" · ") || `${group.nodes.length} actions`,
    preview: previewNode?.label || "",
    tooltip: group.nodes.map(node => buildMemberDetailLines(node).join("\n")).join("\n\n"),
  };
}

function getGroupHeaderPresentation(group) {
  return {
    id: `${group.id}__header`,
    type: "group",
    isGroup: true,
    isGroupHeader: true,
    groupId: group.id,
    isExpanded: true,
    isUser: false,
    typeLabel: "Actions",
    label: `${group.nodes.length} actions expanded`,
    titleLines: [`${group.nodes.length} actions shown`],
    metaLines: ["Click to wrap again"],
    width: 214,
    height: 52,
    tooltip: `Wrap ${group.nodes.length} actions\n${summarizeActionGroup(group).tooltip}`,
    contentX: 34,
    memberCount: group.nodes.length,
    turn: group.turn,
  };
}

function getGroupPresentation(group) {
  const summary = summarizeActionGroup(group);

  return {
    id: group.id,
    type: "group",
    isGroup: true,
    isGroupHeader: false,
    groupId: group.id,
    isExpanded: false,
    isUser: false,
    typeLabel: "Actions",
    label: `${group.nodes.length} actions`,
    titleLines: wrapText(summary.parts, 30, 2),
    metaLines: summary.preview ? wrapText(summary.preview, 32, 2) : [],
    width: 214,
    height: 84,
    tooltip: summary.tooltip,
    detailContent: summary.tooltip,
    contentX: 34,
    memberIds: group.nodeIds,
    memberCount: group.nodes.length,
    turn: group.turn,
  };
}

export function getNodePresentation(node, { textExpanded = false } = {}) {
  const isUser = node.type === "user";
  const isOutcome = node.type === "outcome";
  const isComposing = isComposingReply(node);
  const typeLabel = TYPE_LABELS[node.type] || node.type;
  const detailLines = [];

  if (!isUser) {
    if (node.detail) {
      detailLines.push(node.detail.trim());
    }
    if (node.tool) {
      detailLines.push(`Action: ${node.tool.replace(/_/g, " ")}`);
    }
    if (node.tools?.length) {
      detailLines.push(`Considering: ${node.tools.map(tool => tool.replace(/_/g, " ")).join(", ")}`);
    }
    if (node.result_summary) {
      detailLines.push(`Result: ${node.result_summary}`);
    }
    if (node.error) {
      detailLines.push(`Error: ${node.error}`);
    }
    const argsLine = summarizeArguments(node.arguments);
    if (argsLine) {
      detailLines.push(argsLine);
    }
    if (node.reply_content && node.reply_content !== node.detail) {
      detailLines.push(node.reply_content);
    }
    if (node.status === "running") {
      detailLines.push("In progress…");
    } else if (node.round) {
      detailLines.push(`Round ${node.round}`);
    }
  }

  const primaryText =
    isOutcome && node.reply_content
      ? node.reply_content
      : isComposing && node.detail
        ? node.detail
        : isUser
          ? node.label
          : node.label || typeLabel;

  const titleMaxChars = isUser ? 34 : 32;
  const fullTitleLines = wrapText(primaryText || typeLabel, titleMaxChars, Infinity);
  const collapsedTitleLines = wrapText(primaryText || typeLabel, titleMaxChars, COLLAPSED_TITLE_LINES);
  const fullMetaLines = detailLines.flatMap(line => wrapText(line, 32, Infinity));
  const collapsedMetaLines = detailLines.flatMap(line => wrapText(line, 32, COLLAPSED_META_LINES));

  const titleHasMore = hasMoreLines(fullTitleLines, collapsedTitleLines);
  const metaHasMore = hasMoreLines(fullMetaLines, collapsedMetaLines);
  const isTextCollapsible = titleHasMore || metaHasMore;
  const titleLines = textExpanded ? fullTitleLines : collapsedTitleLines;
  const metaLines = textExpanded ? fullMetaLines : collapsedMetaLines;

  const width = isUser || isOutcome ? 268 : 228;
  const headerHeight = isUser ? 24 : 18;
  const titleHeight = titleLines.length * 14;
  const metaHeight = metaLines.length ? 8 + metaLines.length * 13 : 0;
  const toggleHeight = isTextCollapsible ? TEXT_TOGGLE_HEIGHT : 0;
  const minHeight = isUser || isOutcome || isComposing ? 88 : 68;
  const height = Math.max(minHeight, 12 + headerHeight + titleHeight + metaHeight + toggleHeight + 12);

  return {
    isUser,
    isOutcome,
    isComposing,
    typeLabel,
    titleLines,
    metaLines,
    width,
    height,
    tooltip: buildTooltip(node, detailLines),
    detailContent: buildNodeDetailContent(node),
    contentX: isUser ? 40 : 12,
    isTextCollapsible,
    textExpanded,
    showMoreLabel: isTextCollapsible && !textExpanded ? "show more" : null,
    showLessLabel: isTextCollapsible && textExpanded ? "show less" : null,
  };
}

export function mergeConversationGraph(messages = [], { threadId = null, liveGraph = null, liveTurnIndex = null } = {}) {
  const nodes = [];
  let previousAnchorId = null;
  let turnIndex = 0;

  const appendTurnNodes = (turnNodes, anchorId, turn) => {
    const idMap = {};
    let turnOutcomeId = null;

    turnNodes.forEach(node => {
      const newId = `turn${turn}_${node.id}`;
      idMap[node.id] = newId;

      let newParentId = anchorId;
      if (node.parent_id && idMap[node.parent_id]) {
        newParentId = idMap[node.parent_id];
      } else if (node.parent_id) {
        newParentId = anchorId;
      }

      nodes.push({
        ...node,
        id: newId,
        parent_id: newParentId,
        turn,
      });

      if (node.type === "outcome") {
        turnOutcomeId = newId;
      }
    });

    return turnOutcomeId || idMap[turnNodes[turnNodes.length - 1]?.id] || anchorId;
  };

  messages.forEach(message => {
    if (message.role === "user") {
      const userId = `turn${turnIndex}_user`;
      nodes.push({
        id: userId,
        parent_id: previousAnchorId,
        type: "user",
        label: normalizeContent(message.content),
        content: message.content || "",
        status: "done",
        turn: turnIndex,
        turn_label: `Turn ${turnIndex + 1}`,
      });
      previousAnchorId = userId;
      return;
    }

    if (message.role !== "assistant") {
      return;
    }

    const turnNodes = message.decision_graph?.nodes || [];
    if (turnNodes.length) {
      previousAnchorId = appendTurnNodes(turnNodes, previousAnchorId, turnIndex);
      if (message.content) {
        const replyText = message.content.trim();
        for (let index = nodes.length - 1; index >= 0; index -= 1) {
          if (nodes[index].turn === turnIndex && nodes[index].type === "outcome") {
            nodes[index].reply_content = replyText;
            nodes[index].detail = replyText;
            break;
          }
        }
      }
    }
    turnIndex += 1;
  });

  if (liveGraph?.nodes?.length) {
    const liveTurn = liveTurnIndex ?? turnIndex;
    const liveAnchor = previousAnchorId;
    appendTurnNodes(
      liveGraph.nodes.map(node => ({
        ...node,
        id: `live_${node.id}`,
        parent_id: node.parent_id ? `live_${node.parent_id}` : null,
      })),
      liveAnchor,
      liveTurn
    );
  }

  return {
    thread_id: threadId,
    nodes,
  };
}

export function layoutConversationGraph(nodes = [], { expandedGroups = new Set(), expandedTextNodes = new Set() } = {}) {
  if (!nodes.length) {
    return { nodes: [], edges: [], turns: [], groups: [], width: 0, height: 0 };
  }

  const actionGroups = identifyActionGroups(nodes);
  const groupByNodeId = new Map();
  actionGroups.forEach(group => {
    group.nodeIds.forEach(nodeId => {
      groupByNodeId.set(nodeId, group);
    });
  });

  const hiddenNodeIds = new Set();
  actionGroups.forEach(group => {
    if (!expandedGroups.has(group.id)) {
      group.nodeIds.forEach(nodeId => hiddenNodeIds.add(nodeId));
    }
  });

  const turns = [...new Set(nodes.map(node => node.turn ?? 0))].sort((a, b) => a - b);
  const nodesByTurn = {};
  turns.forEach(turn => {
    nodesByTurn[turn] = nodes.filter(node => (node.turn ?? 0) === turn);
  });

  const NODE_WIDTH = 268;
  const NODE_HEIGHT = 68;
  const COL_GAP = 80;
  const ROW_GAP = 24;
  const PADDING_X = 40;
  const PADDING_Y = 56;
  const HEADER_HEIGHT = 28;

  const presentationById = {};
  nodes.forEach(node => {
    presentationById[node.id] = getNodePresentation(node, {
      textExpanded: expandedTextNodes.has(node.id),
    });
  });

  actionGroups.forEach(group => {
    presentationById[group.id] = getGroupPresentation(group);
    presentationById[`${group.id}__header`] = getGroupHeaderPresentation(group);
  });

  const nodeOrder = new Map();
  nodes.forEach((node, index) => {
    nodeOrder.set(node.id, index);
  });

  const buildTurnRows = turnNodes => {
    const sorted = sortTurnNodes(turnNodes, nodeOrder);
    const rows = [];
    const renderedGroups = new Set();

    sorted.forEach(node => {
      const group = groupByNodeId.get(node.id);
      if (group && expandedGroups.has(group.id)) {
        if (node.id === group.nodeIds[0]) {
          rows.push({ kind: "group-header", id: `${group.id}__header`, group });
        }
        rows.push({ kind: "node", id: node.id, node });
        return;
      }

      if (group && !expandedGroups.has(group.id)) {
        if (node.id !== group.nodeIds[0] || renderedGroups.has(group.id)) {
          return;
        }
        renderedGroups.add(group.id);
        rows.push({ kind: "group", id: group.id, group });
        return;
      }

      if (hiddenNodeIds.has(node.id)) {
        return;
      }

      rows.push({ kind: "node", id: node.id, node });
    });

    return rows;
  };

  const columnLayouts = turns.map((turn, turnIndex) => {
    const turnNodes = nodesByTurn[turn];
    const rows = buildTurnRows(turnNodes);

    const colHeight =
      rows.reduce((total, row, rowIndex) => {
        const rowHeight = presentationById[row.id]?.height || NODE_HEIGHT;
        const gap = rowIndex > 0 ? ROW_GAP : 0;
        return total + gap + rowHeight;
      }, 0) || NODE_HEIGHT;

    const visibleNodeIds = rows.flatMap(row => {
      if (row.kind === "group" || row.kind === "group-header") {
        return [row.id, ...(row.group?.nodeIds || [])];
      }
      return row.node ? [row.node.id] : [row.id];
    });
    const colWidth = Math.max(
      ...visibleNodeIds.map(nodeId => presentationById[nodeId]?.width || NODE_WIDTH),
      NODE_WIDTH
    );

    return {
      turn,
      turnIndex,
      rows,
      colHeight,
      colWidth,
    };
  });

  let colOffsetX = PADDING_X;
  columnLayouts.forEach(column => {
    column.colX = colOffsetX;
    colOffsetX += column.colWidth + COL_GAP;
  });

  const maxColHeight = Math.max(...columnLayouts.map(column => column.colHeight), NODE_HEIGHT);
  const canvasHeight = maxColHeight + PADDING_Y * 2 + HEADER_HEIGHT;
  const canvasWidth =
    PADDING_X * 2 +
    columnLayouts.reduce((sum, column) => sum + column.colWidth, 0) +
    Math.max(0, columnLayouts.length - 1) * COL_GAP;

  const positioned = [];
  const positionById = {};

  columnLayouts.forEach(column => {
    const { rows, colX, colHeight } = column;
    let yCursor = PADDING_Y + HEADER_HEIGHT + (maxColHeight - colHeight) / 2;

    rows.forEach((row, rowIndex) => {
      const presentation = presentationById[row.id];
      const positionedNode = {
        ...(row.kind === "node" ? row.node : {}),
        ...presentation,
        x: colX,
        y: yCursor,
        column: column.turnIndex,
        sequence: rowIndex,
      };
      positioned.push(positionedNode);
      positionById[row.id] = positionedNode;
      yCursor += presentation.height;
      if (rowIndex < rows.length - 1) {
        yCursor += ROW_GAP;
      }
    });
  });

  const resolveVisibleId = nodeId => {
    if (!hiddenNodeIds.has(nodeId)) {
      return nodeId;
    }
    const group = groupByNodeId.get(nodeId);
    return group?.id || nodeId;
  };

  const edgeKeys = new Set();
  const edges = [];

  nodes.forEach(node => {
    if (!node.parent_id) {
      return;
    }

    const parentId = resolveVisibleId(node.parent_id);
    const childId = resolveVisibleId(node.id);
    if (parentId === childId) {
      return;
    }

    const parent = positionById[parentId];
    const child = positionById[childId];
    if (!parent || !child) {
      return;
    }

    const edgeKey = `${parentId}->${childId}`;
    if (edgeKeys.has(edgeKey)) {
      return;
    }
    edgeKeys.add(edgeKey);

    const crossColumn = parent.column !== child.column;
    if (crossColumn) {
      edges.push({
        id: edgeKey,
        type: "horizontal",
        x1: parent.x + parent.width,
        y1: parent.y + parent.height / 2,
        x2: child.x,
        y2: child.y + child.height / 2,
      });
      return;
    }

    edges.push({
      id: edgeKey,
      type: "vertical",
      x1: parent.x + parent.width / 2,
      y1: parent.y + parent.height,
      x2: child.x + child.width / 2,
      y2: child.y,
    });
  });

  const turnMarkers = columnLayouts.map(column => ({
    turn: column.turn,
    x: column.colX,
    width: column.colWidth,
    label: `Turn ${column.turn + 1}`,
  }));

  return {
    nodes: positioned,
    edges,
    turns: turnMarkers,
    groups: actionGroups,
    width: canvasWidth,
    height: canvasHeight,
    timelineY: PADDING_Y + HEADER_HEIGHT + maxColHeight / 2,
    columnWidth: NODE_WIDTH + COL_GAP,
  };
}
