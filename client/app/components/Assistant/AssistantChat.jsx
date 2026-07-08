import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import moment from "moment";
import HtmlContent from "@rewatch/viz/lib/components/HtmlContent";
import { markdown } from "markdown";
import Link from "@/components/Link";
import PlainButton from "@/components/PlainButton";
import CloseOutlined from "@ant-design/icons/CloseOutlined";
import HistoryOutlined from "@ant-design/icons/HistoryOutlined";
import PlusOutlined from "@ant-design/icons/PlusOutlined";
import DeleteOutlined from "@ant-design/icons/DeleteOutlined";
import ApartmentOutlined from "@ant-design/icons/ApartmentOutlined";
import { useCurrentRoute } from "@/components/ApplicationArea/Router";
import Assistant from "@/services/assistant";
import { buildAssistantPageContext } from "@/services/assistantPageContext";
import AssistantThinking from "@/components/Assistant/AssistantThinking";
import AssistantDecisionGraph from "@/components/Assistant/AssistantDecisionGraph";

import "./AssistantChat.less";

const WELCOME = {
  role: "assistant",
  content:
    "Hi! I'm the Rewatch assistant. I can explain query data, help you write SQL, create dashboards and alerts, and answer questions from the docs. What would you like to do?",
};

const SUGGESTIONS = [
  "List my data sources",
  "Create a map from public JSON URL data",
  "Search the web for Postgres window functions",
  "Create a line chart dashboard",
];

function isAwaitingReply(messages) {
  if (!messages?.length) {
    return false;
  }
  return messages[messages.length - 1].role === "user";
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function normalizeAssistantLinks(text) {
  if (!text) {
    return text;
  }
  return text
    .replace(/(https?:\/\/[^\s)\]]+)\/#\//gi, "$1/")
    .replace(/\]\(\/#\//g, "](/")
    .replace(/(?<![:/])\/#\//g, "/");
}

function renderMarkdown(text) {
  try {
    return markdown.toHTML(normalizeAssistantLinks(text || ""));
  } catch (e) {
    return text;
  }
}

export default function AssistantChat({
  compact,
  threadId,
  onThreadIdChange,
  onThreadsChanged,
  onMessagesChange,
  onLiveGraphChange,
  onOpenConversationGraph,
  conversationGraphNodeCount,
  onClose,
  showOpenFullPage,
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [thinkingStatus, setThinkingStatus] = useState("Thinking…");
  const [thinkingActivities, setThinkingActivities] = useState([]);
  const [thinkingGraph, setThinkingGraph] = useState(null);
  const [draftReply, setDraftReply] = useState("");
  const [bootstrapping, setBootstrapping] = useState(true);
  const [error, setError] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyThreads, setHistoryThreads] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const streamActiveRef = useRef(false);
  const pollGenerationRef = useRef(0);
  const skipThreadReloadRef = useRef(false);
  const currentRoute = useCurrentRoute();
  const pageContext = useMemo(() => buildAssistantPageContext(currentRoute), [currentRoute]);

  useEffect(() => {
    if (!onMessagesChange) {
      return;
    }
    const conversationMessages = messages.filter(
      message => !(message.role === "assistant" && message.content === WELCOME.content && messages.length <= 1)
    );
    onMessagesChange(conversationMessages);
  }, [messages, onMessagesChange]);

  useEffect(() => {
    if (onLiveGraphChange) {
      onLiveGraphChange(thinkingGraph);
    }
  }, [thinkingGraph, onLiveGraphChange]);

  const pollForPendingReply = useCallback(async (id, generation) => {
    setLoading(true);
    setThinkingStatus("Assistant is still working…");
    setThinkingActivities([]);
    setThinkingGraph(null);
    setDraftReply("");
    setError(null);

    try {
      for (let attempt = 0; attempt < 120; attempt += 1) {
        if (pollGenerationRef.current !== generation) {
          return;
        }
        await sleep(2000);
        if (pollGenerationRef.current !== generation) {
          return;
        }
        try {
          const history = await Assistant.getMessages(id);
          if (pollGenerationRef.current !== generation) {
            return;
          }
          if (!isAwaitingReply(history)) {
            setMessages(history.length ? history : [WELCOME]);
            return;
          }
        } catch (err) {
          // Ignore transient errors while the server finishes the reply.
        }
      }
      if (pollGenerationRef.current === generation) {
        setError("The assistant is taking longer than expected. Try refreshing or sending your message again.");
      }
    } finally {
      if (pollGenerationRef.current === generation) {
        setLoading(false);
        setThinkingStatus("Thinking…");
        setThinkingActivities([]);
        setThinkingGraph(null);
        setDraftReply("");
      }
    }
  }, []);

  const loadThread = useCallback(
    async (id, generation) => {
      if (!id) {
        setMessages([WELCOME]);
        return;
      }
      try {
        const history = await Assistant.getMessages(id);
        if (pollGenerationRef.current !== generation) {
          return;
        }
        const nextMessages = history.length ? history : [WELCOME];
        setMessages(nextMessages);
        if (isAwaitingReply(nextMessages)) {
          await pollForPendingReply(id, generation);
        }
      } catch (err) {
        const status = err?.response?.status;
        if (status === 404) {
          Assistant.setStoredThreadId(null);
          onThreadIdChange(null);
        }
        setMessages([WELCOME]);
        throw err;
      }
    },
    [onThreadIdChange, pollForPendingReply]
  );

  useEffect(() => {
    if (skipThreadReloadRef.current) {
      skipThreadReloadRef.current = false;
      return undefined;
    }

    const generation = pollGenerationRef.current + 1;
    pollGenerationRef.current = generation;
    let cancelled = false;
    setBootstrapping(true);
    loadThread(threadId, generation)
      .catch(() => {
        if (!cancelled && pollGenerationRef.current === generation) {
          setMessages([WELCOME]);
        }
      })
      .finally(() => {
        if (!cancelled && pollGenerationRef.current === generation) {
          setBootstrapping(false);
        }
      });
    return () => {
      cancelled = true;
      pollGenerationRef.current += 1;
    };
  }, [threadId, loadThread]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading, thinkingActivities, draftReply]);

  const refreshHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const data = await Assistant.listThreads();
      setHistoryThreads(data);
    } catch (err) {
      setHistoryThreads([]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const toggleHistory = useCallback(() => {
    setHistoryOpen(prev => {
      if (!prev) {
        refreshHistory();
      }
      return !prev;
    });
  }, [refreshHistory]);

  const selectHistoryThread = useCallback(
    id => {
      Assistant.setStoredThreadId(id);
      onThreadIdChange(id);
      setHistoryOpen(false);
    },
    [onThreadIdChange]
  );

  const startNewChat = useCallback(() => {
    Assistant.setStoredThreadId(null);
    onThreadIdChange(null);
    setHistoryOpen(false);
  }, [onThreadIdChange]);

  const deleteHistoryThread = useCallback(
    async id => {
      try {
        await Assistant.deleteThread(id);
      } catch (err) {
        // thread may already be gone; refresh regardless
      }
      if (id === threadId) {
        Assistant.setStoredThreadId(null);
        onThreadIdChange(null);
      }
      if (onThreadsChanged) {
        onThreadsChanged();
      }
      refreshHistory();
    },
    [threadId, onThreadIdChange, onThreadsChanged, refreshHistory]
  );

  const handleStreamEvent = useCallback(event => {
    if (event.type === "graph") {
      setThinkingGraph({ nodes: event.nodes || [] });
      return;
    }
    if (event.type === "status") {
      setThinkingStatus(event.message);
      return;
    }
    if (event.type === "reply_delta") {
      setDraftReply(prev => prev + (event.text || ""));
      return;
    }
    if (event.type === "reply_reset") {
      setDraftReply("");
      return;
    }
    if (event.type === "tool_start") {
      setThinkingActivities(prev => {
        const next = prev.filter(item => item.id !== event.id);
        return [...next, { id: event.id, tool: event.tool, label: event.label, status: "running" }];
      });
      return;
    }
    if (event.type === "tool_done") {
      setThinkingActivities(prev =>
        prev.map(item => (item.id === event.id ? { ...item, status: "done" } : item))
      );
    }
  }, []);

  const runChat = useCallback(
    async ({ threadId: currentThreadId, message }) =>
      Assistant.chatStream({ threadId: currentThreadId, message, pageContext, onEvent: handleStreamEvent }),
    [handleStreamEvent, pageContext]
  );

  useEffect(() => {
    if (inputRef.current && !compact) {
      inputRef.current.focus();
    }
  }, [threadId, compact]);

  const sendMessage = useCallback(
    async rawText => {
      const text = (rawText || input).trim();
      if (!text || loading) {
        return;
      }

      setError(null);
      setInput("");
      setHistoryOpen(false);
      setThinkingStatus("Analyzing your request…");
      setThinkingActivities([]);
      setThinkingGraph(null);
      setDraftReply("");
      setMessages(prev => [...prev, { role: "user", content: text }]);
      streamActiveRef.current = true;
      setLoading(true);

      try {
        let response;
        try {
          response = await runChat({ threadId, message: text });
        } catch (err) {
          const detail = err?.message || "";
          if (threadId && detail.toLowerCase().includes("thread not found")) {
            Assistant.setStoredThreadId(null);
            onThreadIdChange(null);
            response = await runChat({ message: text });
          } else {
            throw err;
          }
        }
        setMessages(response.messages || []);
        if (response.thread_id && response.thread_id !== threadId) {
          skipThreadReloadRef.current = true;
          Assistant.setStoredThreadId(response.thread_id);
          onThreadIdChange(response.thread_id);
        }
        if (onThreadsChanged) {
          onThreadsChanged();
        }
      } catch (err) {
        const detail = err?.response?.data?.message || err.message || "Something went wrong.";
        setError(detail);
        setMessages(prev => [...prev, { role: "assistant", content: `Sorry, I ran into an error: ${detail}` }]);
      } finally {
        streamActiveRef.current = false;
        setLoading(false);
        setThinkingActivities([]);
        setThinkingStatus("Thinking…");
        setDraftReply("");
      }
    },
    [input, loading, onThreadIdChange, onThreadsChanged, runChat, threadId]
  );

  const onKeyDown = useCallback(
    event => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    },
    [sendMessage]
  );

  const showEmpty =
    !bootstrapping &&
    !messages.some(message => message.role === "user") &&
    messages.length <= 1 &&
    messages[0]?.role === "assistant";

  return (
    <div className={cx("assistant-chat", { compact })}>
      <div className="assistant-chat-header">
        <div>
          <h4>Rewatch Assistant</h4>
          <div className="subtitle">Queries · Charts · Dashboards · Alerts · Web · ML</div>
        </div>
        <div className="assistant-chat-header-actions">
          {onOpenConversationGraph && (
            <button
              type="button"
              className="assistant-header-btn assistant-header-btn--graph"
              onClick={onOpenConversationGraph}
              disabled={!threadId}>
              <ApartmentOutlined aria-hidden="true" />
              <span>Decision graph</span>
              {conversationGraphNodeCount > 0 && (
                <span className="assistant-header-btn__badge">{conversationGraphNodeCount}</span>
              )}
            </button>
          )}
          {showOpenFullPage && (
            <Link href="assistant" className="assistant-header-btn">
              Open full page
            </Link>
          )}
          {compact && (
            <PlainButton aria-label="New chat" title="New chat" onClick={startNewChat}>
              <PlusOutlined />
            </PlainButton>
          )}
          {compact && (
            <PlainButton
              aria-label="Chat history"
              title="Chat history"
              className={cx({ active: historyOpen })}
              onClick={toggleHistory}>
              <HistoryOutlined />
            </PlainButton>
          )}
          {onClose && (
            <PlainButton aria-label="Close assistant" onClick={onClose}>
              <CloseOutlined />
            </PlainButton>
          )}
        </div>
      </div>

      {historyOpen && (
        <div className="assistant-chat-history">
          <div className="assistant-chat-history-header">
            <span>Recent chats</span>
            <button type="button" className="assistant-chat-history-new" onClick={startNewChat}>
              <PlusOutlined /> New chat
            </button>
          </div>
          {historyLoading ? (
            <div className="assistant-chat-history-empty">Loading…</div>
          ) : historyThreads.length === 0 ? (
            <div className="assistant-chat-history-empty">No conversations yet.</div>
          ) : (
            <div className="assistant-chat-history-list">
              {historyThreads.map(thread => (
                <div
                  key={thread.id}
                  role="button"
                  tabIndex={0}
                  className={cx("assistant-chat-history-item", { active: thread.id === threadId })}
                  onClick={() => selectHistoryThread(thread.id)}
                  onKeyDown={event => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      selectHistoryThread(thread.id);
                    }
                  }}>
                  <div className="assistant-chat-history-item-body">
                    <div className="assistant-chat-history-item-title">
                      {thread.title && thread.title !== "New chat" ? thread.title : thread.preview || "New chat"}
                    </div>
                    <div className="assistant-chat-history-item-time">{moment(thread.updated_at).fromNow()}</div>
                  </div>
                  <PlainButton
                    aria-label="Delete chat"
                    className="assistant-chat-history-item-delete"
                    onClick={event => {
                      event.stopPropagation();
                      deleteHistoryThread(thread.id);
                    }}>
                    <DeleteOutlined />
                  </PlainButton>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="assistant-chat-messages">
        {bootstrapping ? (
          <div className="assistant-chat-message assistant loading">Loading conversation…</div>
        ) : showEmpty ? (
          <div className="assistant-chat-empty">
            <div>{WELCOME.content}</div>
            <div className="prompts">
              {SUGGESTIONS.map(prompt => (
                <button
                  key={prompt}
                  type="button"
                  className="prompt-chip"
                  onClick={() => sendMessage(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={`${msg.role}-${index}`} className={`assistant-chat-message ${msg.role}`}>
              {msg.role === "assistant" ? (
                <>
                  <HtmlContent className="markdown">{renderMarkdown(msg.content)}</HtmlContent>
                  {msg.decision_graph && (
                    <AssistantDecisionGraph graph={msg.decision_graph} defaultExpanded={false} />
                  )}
                </>
              ) : (
                msg.content
              )}
            </div>
          ))
        )}
        {loading && draftReply && (
          <div className="assistant-chat-message assistant">
            <HtmlContent className="markdown">{renderMarkdown(draftReply)}</HtmlContent>
          </div>
        )}
        {loading && !draftReply && (
          <>
            <AssistantThinking status={thinkingStatus} activities={thinkingActivities} />
            {thinkingGraph && <AssistantDecisionGraph graph={thinkingGraph} live defaultExpanded />}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="assistant-chat-message assistant" style={{ margin: "0 16px 8px", fontSize: 12 }}>
          {error}
        </div>
      )}

      <div className="assistant-chat-input">
        <textarea
          ref={inputRef}
          rows={compact ? 2 : 3}
          placeholder="Ask about your data, create a query…"
          value={input}
          disabled={loading || bootstrapping}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button
          type="button"
          className="send"
          disabled={loading || bootstrapping || !input.trim()}
          onClick={() => sendMessage()}
        >
          Send
        </button>
      </div>
    </div>
  );
}

AssistantChat.propTypes = {
  compact: PropTypes.bool,
  threadId: PropTypes.string,
  onThreadIdChange: PropTypes.func.isRequired,
  onThreadsChanged: PropTypes.func,
  onMessagesChange: PropTypes.func,
  onLiveGraphChange: PropTypes.func,
  onOpenConversationGraph: PropTypes.func,
  conversationGraphNodeCount: PropTypes.number,
  onClose: PropTypes.func,
  showOpenFullPage: PropTypes.bool,
};

AssistantChat.defaultProps = {
  compact: false,
  threadId: null,
  onThreadsChanged: null,
  onMessagesChange: null,
  onLiveGraphChange: null,
  onOpenConversationGraph: null,
  conversationGraphNodeCount: 0,
  onClose: null,
  showOpenFullPage: false,
};
