import React, { useCallback, useEffect, useState } from "react";
import MessageOutlined from "@ant-design/icons/MessageOutlined";
import CloseOutlined from "@ant-design/icons/CloseOutlined";
import AssistantChat from "@/components/Assistant/AssistantChat";
import { useCurrentRoute } from "@/components/ApplicationArea/Router";
import { clientConfig } from "@/services/auth";
import location from "@/services/location";
import Assistant from "@/services/assistant";

import "./index.less";

export default function AssistantBubble() {
  const currentRoute = useCurrentRoute();
  const [enabled, setEnabled] = useState(!!clientConfig.assistantEnabled);
  const [open, setOpen] = useState(() => Assistant.getStoredBubbleOpen());
  const [threadId, setThreadId] = useState(Assistant.getStoredThreadId());

  const setBubbleOpen = useCallback(nextOpen => {
    setOpen(nextOpen);
    Assistant.setStoredBubbleOpen(nextOpen);
  }, []);

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

  const onAssistantPage =
    currentRoute?.id === "Assistant" || location.path === "/assistant" || location.path.startsWith("/assistant/");

  if (!enabled || onAssistantPage) {
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
            onClose={() => setBubbleOpen(false)}
            showOpenFullPage
          />
        </div>
      )}

      <button
        type="button"
        className={`assistant-bubble-toggle${open ? " open" : ""}`}
        aria-label={open ? "Close assistant" : "Open assistant"}
        onClick={() => setBubbleOpen(prev => !prev)}
      >
        {open ? <CloseOutlined /> : <MessageOutlined />}
      </button>
    </div>
  );
}
