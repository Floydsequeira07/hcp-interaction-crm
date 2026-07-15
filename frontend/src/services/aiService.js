import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});
export const chatWithAI = (message) =>
  API.post("/ai/chat", {
    message,
  });