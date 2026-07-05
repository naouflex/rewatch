import React, { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import HtmlContent from "@redash/viz/lib/components/HtmlContent";
import { markdown } from "markdown";
import Link from "@/components/Link";
import PlainButton from "@/components/PlainButton";
import CloseOutlined from "@ant-design/icons/CloseOutlined";
import Assistant from "@/services/assistant";

import "./AssistantChat.less";

const WELCOME = {
  role: "assistant",
  content:
    "Hi! I'm the Rewatch assistant. I can explain query data, help you write SQL, create dashboards and alerts, and answer questions from the docs. What would you like to do?",
};

const SUGGESTIONS = [
  "List my data sources",
  "Search my queries",
  "How do I set up an alert?",
  "Explain query 1",
];

function renderMarkdown(text) {
  try {
    return markdown.toHTML(text || "");
  } catch (e) {
    return text;
  }
}

export default function AssistantChat({
  compact,
  threadId,
  onThreadIdChange,
  onThreadsChanged,
  onClose,
  showOpenFullPage,
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const loadThread = useCallback(async id => {
    if (!id) {
      setMessages([WELCOME]);
      return;
    }
    const history = await Assistant.getMessages(id);
    setMessages(history.length ? history : [WELCOME]);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setBootstrapping(true);
    loadThread(threadId)
      .catch(() => {
        if (!cancelled) {
          setMessages([WELCOME]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setBootstrapping(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [threadId, loadThread]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

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
      setMessages(prev => [...prev, { role: "user", content: text }]);
      setLoading(true);

      try {
        const response = await Assistant.chat({ threadId, message: text });
        if (response.thread_id && response.thread_id !== threadId) {
          onThreadIdChange(response.thread_id);
          Assistant.setStoredThreadId(response.thread_id);
        }
        setMessages(response.messages || []);
        if (onThreadsChanged) {
          onThreadsChanged();
        }
      } catch (err) {
        const detail = err?.response?.data?.message || err.message || "Something went wrong.";
        setError(detail);
        setMessages(prev => [...prev, { role: "assistant", content: `Sorry, I ran into an error: ${detail}` }]);
      } finally {
        setLoading(false);
      }
    },
    [input, loading, onThreadIdChange, onThreadsChanged, threadId]
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

  const showEmpty = !bootstrapping && messages.length <= 1 && messages[0]?.role === "assistant";

  return (
    <div className={cx("assistant-chat", { compact })}>
      <div className="assistant-chat-header">
        <div>
          <h4>Rewatch Assistant</h4>
          <div className="subtitle">Queries · Dashboards · Alerts · Docs</div>
        </div>
        <div className="assistant-chat-header-actions">
          {showOpenFullPage && (
            <Link href="assistant" className="btn btn-default btn-sm">
              Open full page
            </Link>
          )}
          {onClose && (
            <PlainButton aria-label="Close assistant" onClick={onClose}>
              <CloseOutlined />
            </PlainButton>
          )}
        </div>
      </div>

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
                <HtmlContent className="markdown">{renderMarkdown(msg.content)}</HtmlContent>
              ) : (
                msg.content
              )}
            </div>
          ))
        )}
        {loading && <div className="assistant-chat-message assistant loading">Thinking…</div>}
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
  onClose: PropTypes.func,
  showOpenFullPage: PropTypes.bool,
};

AssistantChat.defaultProps = {
  compact: false,
  threadId: null,
  onThreadsChanged: null,
  onClose: null,
  showOpenFullPage: false,
};
