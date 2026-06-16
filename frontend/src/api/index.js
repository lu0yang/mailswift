const BASE = "/api";

// ── Token 管理 ──────────────────────────────────────────

const TOKEN_KEY = "mailswift_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isLoggedIn() {
  return !!getToken();
}

async function req(path, { method = "GET", body, params } = {}) {
  let url = `${BASE}${path}`;
  if (params) {
    const qs = new URLSearchParams(params).toString();
    if (qs) url += `?${qs}`;
  }
  const opts = { method };
  opts.headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) {
    opts.headers["Authorization"] = `Bearer ${token}`;
  }
  if (body) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) {
      removeToken();
      window.location.hash = "#/login";
    }
    const err = new Error(json.detail || `HTTP ${res.status}`);
    err.response = { data: json, status: res.status };
    throw err;
  }
  return { data: json };
}

// ── Auth APIs ────────────────────────────────────────────

export function login(email, password) {
  return req("/auth/login", { method: "POST", body: { email, password } });
}

export function register(email, password) {
  return req("/auth/register", { method: "POST", body: { email, password } });
}

export function autoLogin(email, apiKey) {
  return req("/auth/auto-login", { method: "POST", body: { email, api_key: apiKey } });
}

export function getMe() {
  return req("/auth/me");
}

export function getSettings() {
  return req("/settings");
}

export function updateSettings(data) {
  return req("/settings", { method: "POST", body: data });
}

export function testConnection(data) {
  return req("/settings/test-connection", { method: "POST", body: data || {} });
}

export function sendEmail(data) {
  return req("/send", { method: "POST", body: data });
}

export function getHistory(params) {
  return req("/history", { params });
}

export function deleteHistory(id) {
  return req(`/history/${id}`, { method: "DELETE" });
}

export function getTemplates(type) {
  return req("/templates", { params: type ? { type } : undefined });
}

export function createTemplate(data) {
  return req("/templates", { method: "POST", body: data });
}

export function updateTemplate(id, data) {
  return req(`/templates/${id}`, { method: "PUT", body: data });
}

export function deleteTemplate(id) {
  return req(`/templates/${id}`, { method: "DELETE" });
}

export function getSignatures() {
  return req("/signatures");
}

export function createSignature(data) {
  return req("/signatures", { method: "POST", body: data });
}

export function updateSignature(id, data) {
  return req(`/signatures/${id}`, { method: "PUT", body: data });
}

export function deleteSignature(id) {
  return req(`/signatures/${id}`, { method: "DELETE" });
}

export function encodeImage(url) {
  return req("/encode-image", { method: "POST", body: { url } });
}

export function getAccounts() {
  return req("/accounts");
}

export function switchAccount(id) {
  return req(`/accounts/${id}/switch`, { method: "POST" });
}

export function deleteAccount(id) {
  return req(`/accounts/${id}`, { method: "DELETE" });
}

export function lookupIncident(ticketId) {
  return req(`/incident-store/lookup?ticket_id=${encodeURIComponent(ticketId)}`);
}

export function resetApp() {
  return req("/reset", { method: "POST" });
}
