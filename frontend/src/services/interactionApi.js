import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

export const saveInteraction = (data) =>
  API.post("/interaction/", data);

export const updateInteraction = (id, data) =>
  API.put(`/interaction/${id}`, data);