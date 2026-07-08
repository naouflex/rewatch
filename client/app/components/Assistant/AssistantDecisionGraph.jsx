import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import CheckOutlined from "@ant-design/icons/CheckOutlined";
import CloseCircleOutlined from "@ant-design/icons/CloseCircleOutlined";
import LoadingOutlined from "@ant-design/icons/LoadingOutlined";
import BranchesOutlined from "@ant-design/icons/BranchesOutlined";
import ToolOutlined from "@ant-design/icons/ToolOutlined";
import BulbOutlined from "@ant-design/icons/BulbOutlined";

import "./AssistantDecisionGraph.less";

function buildTree(nodes) {
  if (!nodes?.length) {
    return [];
  }
  const byId = {};
  const roots = [];

  nodes.forEach(node => {
    byId[node.id] = { ...node, children: [] };
  });

  nodes.forEach(node => {
    const entry = byId[node.id];
    if (node.parent_id && byId[node.parent_id]) {
      byId[node.parent_id].children.push(entry);
    } else {
      roots.push(entry);
    }
  });

  return roots;
}

function nodeIcon(node) {
  if (node.status === "running") {
    return <LoadingOutlined spin aria-hidden="true" />;
  }
  if (node.status === "error") {
    return <CloseCircleOutlined aria-hidden="true" />;
  }
  if (node.type === "tool") {
    return <ToolOutlined aria-hidden="true" />;
  }
  if (node.type === "decision") {
    return <BulbOutlined aria-hidden="true" />;
  }
  if (node.status === "done") {
    return <CheckOutlined aria-hidden="true" />;
  }
  return <BranchesOutlined aria-hidden="true" />;
}

function GraphNode({ node, depth = 0 }) {
  return (
    <li className={cx("assistant-decision-graph__node", node.type, node.status)} style={{ "--depth": depth }}>
      <div className="assistant-decision-graph__node-row">
        <span className="assistant-decision-graph__node-icon">{nodeIcon(node)}</span>
        <div className="assistant-decision-graph__node-body">
          <div className="assistant-decision-graph__node-label">{node.label}</div>
          {node.detail && <div className="assistant-decision-graph__node-detail">{node.detail}</div>}
          {node.result_summary && (
            <div className="assistant-decision-graph__node-result">{node.result_summary}</div>
          )}
          {node.error && <div className="assistant-decision-graph__node-error">{node.error}</div>}
          {node.tools?.length > 0 && (
            <div className="assistant-decision-graph__node-tools">{node.tools.join(", ")}</div>
          )}
        </div>
      </div>
      {node.children?.length > 0 && (
        <ul className="assistant-decision-graph__children">
          {node.children.map(child => (
            <GraphNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  );
}

GraphNode.propTypes = {
  node: PropTypes.shape({
    id: PropTypes.string.isRequired,
    type: PropTypes.string,
    label: PropTypes.string.isRequired,
    status: PropTypes.string,
    detail: PropTypes.string,
    result_summary: PropTypes.string,
    error: PropTypes.string,
    tools: PropTypes.arrayOf(PropTypes.string),
    children: PropTypes.array, // eslint-disable-line react/forbid-prop-types
  }).isRequired,
  depth: PropTypes.number,
};

GraphNode.defaultProps = {
  depth: 0,
};

export default function AssistantDecisionGraph({ graph, live, defaultExpanded }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const tree = useMemo(() => buildTree(graph?.nodes || []), [graph]);

  if (!tree.length) {
    return null;
  }

  return (
    <div className={cx("assistant-decision-graph", { live })}>
      <button
        type="button"
        className="assistant-decision-graph__toggle"
        onClick={() => setExpanded(prev => !prev)}
        aria-expanded={expanded}
      >
        <BranchesOutlined aria-hidden="true" />
        <span>{live ? "Decision graph" : "Actions taken"}</span>
        <span className="assistant-decision-graph__count">{graph.nodes.length}</span>
      </button>
      {expanded && (
        <ul className="assistant-decision-graph__tree">
          {tree.map(node => (
            <GraphNode key={node.id} node={node} />
          ))}
        </ul>
      )}
    </div>
  );
}

AssistantDecisionGraph.propTypes = {
  graph: PropTypes.shape({
    nodes: PropTypes.arrayOf(PropTypes.object),
  }),
  live: PropTypes.bool,
  defaultExpanded: PropTypes.bool,
};

AssistantDecisionGraph.defaultProps = {
  graph: null,
  live: false,
  defaultExpanded: true,
};
