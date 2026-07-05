import { axios } from "@/services/axios";

const THREAD_STORAGE_KEY = "rewatch_assistant_thread";

const Assistant = {
  status: () => axios.get("api/assistant/status"),
  listThreads: () => axios.get("api/assistant/threads"),
  createThread: () => axios.post("api/assistant/threads"),
  deleteThread: threadId => axios.delete(`api/assistant/threads/${threadId}`),
  getMessages: threadId => axios.get(`api/assistant/threads/${threadId}/messages`),
  chat: ({ threadId, message }) => axios.post("api/assistant/chat", { thread_id: threadId, message }),
  getStoredThreadId: () => window.sessionStorage.getItem(THREAD_STORAGE_KEY),
  setStoredThreadId: threadId => {
    if (threadId) {
      window.sessionStorage.setItem(THREAD_STORAGE_KEY, threadId);
    } else {
      window.sessionStorage.removeItem(THREAD_STORAGE_KEY);
    }
  },
};

export default Assistant;
