import React, { useCallback, useEffect, useState } from "react";
import MessageOutlined from "@ant-design/icons/MessageOutlined";
import CloseOutlined from "@ant-design/icons/CloseOutlined";
import AssistantChat from "@/components/Assistant/AssistantChat";
import { clientConfig } from "@/services/auth";
import Assistant from "@/services/assistant";

import "./index.less";

export default function AssistantBubble() {
  const [enabled, setEnabled] = useState(!!clientConfig.assistantEnabled);
  const [open, setOpen] = useState(false);
  const [threadId, setThreadId] = useState(Assistant.getStoredThreadId());

  useEffect(() => {
    if (clientConfig.assistantEnabled) {
      setEnabled(true);
      return undefined;
    }
    Assistant.status()
      .then(status => setEnabled(!!status.enabled))
      .catch(() => setEnabled(false));
    return undefined;
  }, []);

  const handleThreadChange = useCallback(id => {
    setThreadId(id);
    Assistant.setStoredThreadId(id);
  }, []);

  if (!enabled) {
    return null;
  }

  return (
    <div className="assistant-bubble-root">
      {open && (
        <div className="assistant-bubble-panel" role="dialog" aria-label="Rewatch Assistant">
          <AssistantChat
            compact
            threadId={threadId}
            onThreadIdChange={handleThreadChange}
            onClose={() => setOpen(false)}
            showOpenFullPage
          />
        </div>
      )}

      <button
        type="button"
        className={`assistant-bubble-toggle${open ? " open" : ""}`}
        aria-label={open ? "Close assistant" : "Open assistant"}
        onClick={() => setOpen(prev => !prev)}
      >
        {open ? <CloseOutlined /> : <MessageOutlined />}
      </button>
    </div>
  );
}
