const BASE = "/api";

// ── 默认预设域名（全局共享）─────────────────────────────
export const DEFAULT_DOMAINS = ["@oe.21vianet.com", "@microsoft.com"];

// ── Token & Password 管理 ──────────────────────────────

const TOKEN_KEY = "mailswift_token";
const PWD_KEY = "mailswift_ews_password";

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function removeToken() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(PWD_KEY);
}

export function isLoggedIn() {
  return !!getToken();
}

export function getEwsPassword() {
  return sessionStorage.getItem(PWD_KEY) || "";
}

export function setEwsPassword(pwd) {
  sessionStorage.setItem(PWD_KEY, pwd);
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

export function getMe() {
  return req("/auth/me");
}

// ── Business APIs ────────────────────────────────────────

export function sendEmail(data) {
  // 发邮件时自动带上 sessionStorage 中的密码
  return req("/send", { method: "POST", body: { ...data, ews_password: getEwsPassword() } });
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

export function lookupIncident(ticketId) {
  return req(`/incident-store/lookup?ticket_id=${encodeURIComponent(ticketId)}`);
}

export function resetApp() {
  return req("/reset", { method: "POST" });
}

export function getDomains() {
  return req("/domains");
}

export function updateDomains(domains) {
  return req("/domains", { method: "POST", body: { domains } });
}
