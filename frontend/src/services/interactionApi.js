import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

export const saveInteraction = (data) =>
  API.post("/interaction/", data);

export const updateInteraction = (id, data) =>
  API.put(`/interaction/${id}`, data);