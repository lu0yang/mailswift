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

export function testSmtp(data) {
  return api.post("/settings/test-smtp", data || {});
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

// Templates
export function getTemplates(type) {
  return api.get("/templates", { params: type ? { type } : {} });
}

export function createTemplate(data) {
  return api.post("/templates", data);
}

export function updateTemplate(id, data) {
  return api.put(`/templates/${id}`, data);
}

export function deleteTemplate(id) {
  return api.delete(`/templates/${id}`);
}

// Signatures
export function getSignatures() {
  return api.get("/signatures");
}

export function createSignature(data) {
  return api.post("/signatures", data);
}

export function updateSignature(id, data) {
  return api.put(`/signatures/${id}`, data);
}

export function deleteSignature(id) {
  return api.delete(`/signatures/${id}`);
}

export default api;
