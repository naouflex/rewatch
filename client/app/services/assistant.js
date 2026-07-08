import { axios } from "@/services/axios";

const THREAD_STORAGE_KEY = "rewatch_assistant_thread";
const BUBBLE_OPEN_STORAGE_KEY = "rewatch_assistant_bubble_open";

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

async function consumeSseStream(response, onEvent) {
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.message || message;
    } catch (e) {
      // ignore parse errors
    }
    throw new Error(message);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    chunks.forEach(chunk => {
      const line = chunk
        .split("\n")
        .find(entry => entry.startsWith("data: "));
      if (!line) {
        return;
      }
      onEvent(JSON.parse(line.slice(6)));
    });
  }
}

const Assistant = {
  status: () => axios.get("api/assistant/status"),
  listThreads: () => axios.get("api/assistant/threads"),
  createThread: () => axios.post("api/assistant/threads"),
  deleteThread: threadId => axios.delete(`api/assistant/threads/${threadId}`),
  getMessages: threadId => axios.get(`api/assistant/threads/${threadId}/messages`),
  getThreadDecisionGraph: threadId => axios.get(`api/assistant/threads/${threadId}/decision_graph`),
  chat: ({ threadId, message, pageContext }) => axios.post("api/assistant/chat", { thread_id: threadId, message, page_context: pageContext }),
  generateQuery: ({
    prompt,
    dataSourceId,
    dataSourceType,
    dataSourceName,
    syntax,
    schema,
    existingQuery,
  }) =>
    axios.post("api/assistant/generate-query", {
      prompt,
      data_source_id: dataSourceId,
      data_source_type: dataSourceType,
      data_source_name: dataSourceName,
      syntax,
      schema,
      existing_query: existingQuery,
    }),
  chatStream: async ({ threadId, message, pageContext, onEvent }) => {
    const response = await fetch("api/assistant/chat/stream", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        "X-CSRF-TOKEN": readCookie("csrf_token"),
      },
      body: JSON.stringify({ thread_id: threadId, message, page_context: pageContext }),
    });

    let result = null;
    await consumeSseStream(response, event => {
      if (event.type === "thread_started" && event.thread_id) {
        Assistant.setStoredThreadId(event.thread_id);
      } else if (event.type === "complete") {
        if (event.thread_id) {
          Assistant.setStoredThreadId(event.thread_id);
        }
        result = event;
      } else if (event.type === "error") {
        throw new Error(event.message || "Assistant request failed.");
      } else if (onEvent) {
        onEvent(event);
      }
    });

    if (!result) {
      throw new Error("Assistant stream ended without a response.");
    }
    return result;
  },
  getStoredThreadId: () => window.sessionStorage.getItem(THREAD_STORAGE_KEY),
  setStoredThreadId: threadId => {
    if (threadId) {
      window.sessionStorage.setItem(THREAD_STORAGE_KEY, threadId);
    } else {
      window.sessionStorage.removeItem(THREAD_STORAGE_KEY);
    }
  },
  getStoredBubbleOpen: () => window.sessionStorage.getItem(BUBBLE_OPEN_STORAGE_KEY) === "1",
  setStoredBubbleOpen: open => {
    if (open) {
      window.sessionStorage.setItem(BUBBLE_OPEN_STORAGE_KEY, "1");
    } else {
      window.sessionStorage.removeItem(BUBBLE_OPEN_STORAGE_KEY);
    }
  },
};

export default Assistant;
