import React from "react";
import PropTypes from "prop-types";
import Modal from "antd/lib/modal";

import AssistantConversationGraph2D from "./AssistantConversationGraph2D";

import "@/components/ModalShell/modal-shell.less";
import "./AssistantConversationGraphModal.less";

function renderModalTitle(title, description) {
  if (!description) {
    return title;
  }

  return (
    <div className="modal-shell__title-block">
      <div className="modal-shell__title">{title}</div>
      <div className="modal-shell__description">{description}</div>
    </div>
  );
}

export default function AssistantConversationGraphModal({ open, onClose, graph, emptyLabel }) {
  const nodeCount = graph?.nodes?.length || 0;

  return (
    <Modal
      open={open}
      title={renderModalTitle(
        "Conversation graph",
        nodeCount > 0
          ? `${nodeCount} steps — drag or Shift+scroll horizontally through the timeline`
          : "Decisions and actions across this chat"
      )}
      onCancel={onClose}
      footer={null}
      width="min(1100px, 94vw)"
      className="modal-shell assistant-conversation-graph-modal"
      rootClassName="modal-shell-root modal-shell-root--xl assistant-conversation-graph-modal-root"
      destroyOnClose>
      <div className="modal-shell__body assistant-conversation-graph-modal__body">
        <AssistantConversationGraph2D graph={graph} embedded emptyLabel={emptyLabel} />
      </div>
    </Modal>
  );
}

AssistantConversationGraphModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  graph: PropTypes.shape({
    thread_id: PropTypes.string,
    nodes: PropTypes.arrayOf(PropTypes.object),
  }),
  emptyLabel: PropTypes.string,
};

AssistantConversationGraphModal.defaultProps = {
  graph: null,
  emptyLabel: "Start the conversation to build the graph.",
};
