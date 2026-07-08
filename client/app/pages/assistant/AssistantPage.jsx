import React, { useCallback, useEffect, useMemo, useState } from "react";
import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import AssistantChat from "@/components/Assistant/AssistantChat";
import AssistantConversationGraphModal from "@/components/Assistant/AssistantConversationGraphModal";
import AssistantThreadSidebar from "@/components/Assistant/AssistantThreadSidebar";
import { mergeConversationGraph } from "@/components/Assistant/conversationGraph";
import { clientConfig } from "@/services/auth";
import Assistant from "@/services/assistant";
import routes from "@/services/routes";

import "@/components/Assistant/AssistantChat.less";

function AssistantPage() {
  const [enabled, setEnabled] = useState(!!clientConfig.assistantEnabled);
  const [threads, setThreads] = useState([]);
  const [threadsLoading, setThreadsLoading] = useState(true);
  const [activeThreadId, setActiveThreadId] = useState(Assistant.getStoredThreadId());
  const [conversationMessages, setConversationMessages] = useState([]);
  const [liveGraph, setLiveGraph] = useState(null);
  const [graphModalOpen, setGraphModalOpen] = useState(false);

  const conversationGraph = useMemo(() => {
    if (!activeThreadId) {
      return { thread_id: null, nodes: [] };
    }
    const liveTurnIndex = conversationMessages.filter(message => message.role === "assistant").length;
    return mergeConversationGraph(conversationMessages, {
      threadId: activeThreadId,
      liveGraph,
      liveTurnIndex,
    });
  }, [activeThreadId, conversationMessages, liveGraph]);

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
    setConversationMessages([]);
    setLiveGraph(null);
    setGraphModalOpen(false);
    Assistant.setStoredThreadId(id);
  }, []);

  const handleCreateThread = useCallback(async () => {
    const thread = await Assistant.createThread();
    await refreshThreads();
    setConversationMessages([]);
    setLiveGraph(null);
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
            onMessagesChange={setConversationMessages}
            onLiveGraphChange={setLiveGraph}
            onOpenConversationGraph={() => setGraphModalOpen(true)}
            conversationGraphNodeCount={conversationGraph.nodes.length}
          />
        </div>
        </div>
        <AssistantConversationGraphModal
          open={graphModalOpen}
          onClose={() => setGraphModalOpen(false)}
          graph={conversationGraph}
          emptyLabel={
            activeThreadId
              ? "Send a message to start building this conversation graph."
              : "Select or start a chat to view its decision graph."
          }
        />
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
