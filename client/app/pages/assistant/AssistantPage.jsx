import React, { useCallback, useEffect, useState } from "react";
import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import AssistantChat from "@/components/Assistant/AssistantChat";
import AssistantThreadSidebar from "@/components/Assistant/AssistantThreadSidebar";
import { clientConfig } from "@/services/auth";
import Assistant from "@/services/assistant";
import routes from "@/services/routes";

import "@/components/Assistant/AssistantChat.less";

function AssistantPage() {
  const [enabled, setEnabled] = useState(!!clientConfig.assistantEnabled);
  const [threads, setThreads] = useState([]);
  const [threadsLoading, setThreadsLoading] = useState(true);
  const [activeThreadId, setActiveThreadId] = useState(Assistant.getStoredThreadId());

  const refreshThreads = useCallback(async () => {
    setThreadsLoading(true);
    try {
      const data = await Assistant.listThreads();
      setThreads(data);
      setActiveThreadId(currentId => {
        if (currentId && !data.some(thread => thread.id === currentId)) {
          const nextId = data[0]?.id || null;
          Assistant.setStoredThreadId(nextId);
          return nextId;
        }
        if (!currentId && data.length) {
          Assistant.setStoredThreadId(data[0].id);
          return data[0].id;
        }
        return currentId;
      });
    } finally {
      setThreadsLoading(false);
    }
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

  useEffect(() => {
    if (enabled) {
      refreshThreads();
    }
  }, [enabled, refreshThreads]);

  const handleSelectThread = useCallback(id => {
    setActiveThreadId(id);
    Assistant.setStoredThreadId(id);
  }, []);

  const handleCreateThread = useCallback(async () => {
    const thread = await Assistant.createThread();
    await refreshThreads();
    handleSelectThread(thread.id);
  }, [handleSelectThread, refreshThreads]);

  const handleDeleteThread = useCallback(
    async id => {
      await Assistant.deleteThread(id);
      const remaining = threads.filter(thread => thread.id !== id);
      if (activeThreadId === id) {
        const nextId = remaining[0]?.id || null;
        setActiveThreadId(nextId);
        Assistant.setStoredThreadId(nextId);
      }
      await refreshThreads();
    },
    [activeThreadId, refreshThreads, threads]
  );

  if (!enabled) {
    return (
      <div className="page-assistant">
        <div className="container">
          <p className="text-muted">
            The assistant is not configured. Set <code>REDASH_OPENAI_API_KEY</code> in the server environment and
            restart Rewatch.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-assistant">
      <div className="container m-b-20">
        <div className="assistant-page-layout">
        <AssistantThreadSidebar
          threads={threads}
          activeId={activeThreadId}
          loading={threadsLoading}
          onSelect={handleSelectThread}
          onCreate={handleCreateThread}
          onDelete={handleDeleteThread}
        />
        <div className="assistant-page-main">
          <AssistantChat
            threadId={activeThreadId}
            onThreadIdChange={handleSelectThread}
            onThreadsChanged={refreshThreads}
          />
        </div>
        </div>
      </div>
    </div>
  );
}

routes.register(
  "Assistant",
  routeWithUserSession({
    path: "/assistant",
    title: "Assistant",
    render: pageProps => <AssistantPage {...pageProps} />,
  })
);

export default AssistantPage;
