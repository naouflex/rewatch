import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import moment from "moment";
import PlainButton from "@/components/PlainButton";
import PlusOutlinedIcon from "@ant-design/icons/PlusOutlined";
import DeleteOutlinedIcon from "@ant-design/icons/DeleteOutlined";

import "./AssistantThreadSidebar.less";

function threadLabel(thread) {
  return thread.title && thread.title !== "New chat" ? thread.title : thread.preview || "New chat";
}

export default function AssistantThreadSidebar({
  threads,
  activeId,
  loading,
  onSelect,
  onCreate,
  onDelete,
}) {
  return (
    <aside className="assistant-thread-sidebar">
      <div className="assistant-thread-sidebar-header">
        <h3>Chats</h3>
        <PlainButton aria-label="New chat" onClick={onCreate}>
          <PlusOutlinedIcon />
        </PlainButton>
      </div>
      <div className="assistant-thread-sidebar-list">
        {loading && <div className="assistant-thread-sidebar-empty">Loading…</div>}
        {!loading && threads.length === 0 && (
          <div className="assistant-thread-sidebar-empty">No conversations yet.</div>
        )}
        {threads.map(thread => (
          <div
            key={thread.id}
            className={cx("assistant-thread-item", { active: thread.id === activeId })}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(thread.id)}
            onKeyDown={event => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(thread.id);
              }
            }}
          >
            <div className="assistant-thread-item-body">
              <div className="assistant-thread-item-title">{threadLabel(thread)}</div>
              {thread.preview && <div className="assistant-thread-item-preview">{thread.preview}</div>}
              <div className="assistant-thread-item-time">{moment(thread.updated_at).fromNow()}</div>
            </div>
            <PlainButton
              aria-label="Delete chat"
              className="assistant-thread-item-delete"
              onClick={event => {
                event.stopPropagation();
                onDelete(thread.id);
              }}
            >
              <DeleteOutlinedIcon />
            </PlainButton>
          </div>
        ))}
      </div>
    </aside>
  );
}

AssistantThreadSidebar.propTypes = {
  threads: PropTypes.arrayOf(PropTypes.object).isRequired,
  activeId: PropTypes.string,
  loading: PropTypes.bool,
  onSelect: PropTypes.func.isRequired,
  onCreate: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
};

AssistantThreadSidebar.defaultProps = {
  activeId: null,
  loading: false,
};
