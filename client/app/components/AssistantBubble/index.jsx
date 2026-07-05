import React, { useCallback, useEffect, useRef, useState } from "react";
import MessageOutlined from "@ant-design/icons/MessageOutlined";
import CloseOutlined from "@ant-design/icons/CloseOutlined";
import PlainButton from "@/components/PlainButton";
import HtmlContent from "@redash/viz/lib/components/HtmlContent";
import { markdown } from "markdown";
import { clientConfig } from "@/services/auth";
import Assistant from "@/services/assistant";

import "./index.less";

const WELCOME = {
  role: "assistant",
  content:
    "Hi! I'm the Rewatch assistant. I can explain query data, help you write SQL, create dashboards and alerts, and answer questions from the docs. What would you like to do?",
};

function renderMarkdown(text) {
  try {
    return markdown.toHTML(text || "");
  } catch (e) {
    return text;
  }
}

export default function AssistantBubble() {
  const [enabled, setEnabled] = useState(!!clientConfig.assistantEnabled);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

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
    if (open && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, open, loading]);

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) {
      return;
    }

    setError(null);
    setInput("");
    const userMessage = { role: "user", content: text };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setLoading(true);

    try {
      const response = await Assistant.chat(nextMessages);
      setMessages(response.messages || [...nextMessages, { role: "assistant", content: response.reply }]);
    } catch (err) {
      const detail = err?.response?.data?.message || err.message || "Something went wrong.";
      setError(detail);
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: `Sorry, I ran into an error: ${detail}` },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages]);

  const onKeyDown = useCallback(
    event => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    },
    [sendMessage]
  );

  if (!enabled) {
    return null;
  }

  return (
    <div className="assistant-bubble-root">
      {open && (
        <div className="assistant-bubble-panel" role="dialog" aria-label="Rewatch Assistant">
          <div className="assistant-bubble-header">
            <div>
              <h4>Rewatch Assistant</h4>
              <div className="subtitle">Queries · Dashboards · Alerts · Docs</div>
            </div>
            <PlainButton aria-label="Close assistant" onClick={() => setOpen(false)}>
              <CloseOutlined />
            </PlainButton>
          </div>

          <div className="assistant-bubble-messages">
            {messages.map((msg, index) => (
              <div
                key={`${msg.role}-${index}`}
                className={`assistant-bubble-message ${msg.role}`}
              >
                {msg.role === "assistant" ? (
                  <HtmlContent className="markdown">{renderMarkdown(msg.content)}</HtmlContent>
                ) : (
                  msg.content
                )}
              </div>
            ))}
            {loading && <div className="assistant-bubble-message assistant loading">Thinking…</div>}
            <div ref={messagesEndRef} />
          </div>

          {error && (
            <div className="assistant-bubble-message assistant" style={{ margin: "0 12px 8px", fontSize: 12 }}>
              {error}
            </div>
          )}

          <div className="assistant-bubble-input">
            <textarea
              ref={inputRef}
              rows={2}
              placeholder="Ask about your data, create a query…"
              value={input}
              disabled={loading}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKeyDown}
            />
            <button type="button" className="send" disabled={loading || !input.trim()} onClick={sendMessage}>
              Send
            </button>
          </div>
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
