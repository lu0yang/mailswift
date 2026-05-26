import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

export function getSettings() {
  return api.get("/settings");
}

export function updateSettings(data) {
  return api.post("/settings", data);
}

export function sendEmail(data) {
  return api.post("/send", data);
}

export function getHistory(params) {
  return api.get("/history", { params });
}

export function deleteHistory(id) {
  return api.delete(`/history/${id}`);
}

export default api;
