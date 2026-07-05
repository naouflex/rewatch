import { axios } from "@/services/axios";

const Assistant = {
  status: () => axios.get("api/assistant/status"),
  chat: messages => axios.post("api/assistant/chat", { messages }),
};

export default Assistant;
