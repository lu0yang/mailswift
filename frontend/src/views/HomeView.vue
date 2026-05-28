<template>
  <div class="home">
    <div class="title-row">
      <div class="page-title">发送邮件</div>
      <n-button text type="error" size="small" @click="handleClear">
        <template #icon><n-icon><trash-outline /></n-icon></template>
        一键清理
      </n-button>
    </div>

    <!-- Email type switcher -->
    <div class="type-switcher">
      <div
        class="type-card"
        :class="{ active: emailType === 'account' }"
        @click="switchType('account')"
      >
        <div class="type-icon">
          <n-icon size="24"><person-outline /></n-icon>
        </div>
        <div class="type-label">账号创建</div>
        <div class="type-desc">发送账号和密码信息</div>
      </div>
      <div
        class="type-card"
        :class="{ active: emailType === 'subscription' }"
        @click="switchType('subscription')"
      >
        <div class="type-icon">
          <n-icon size="24"><cube-outline /></n-icon>
        </div>
        <div class="type-label">订阅创建</div>
        <div class="type-desc">发送订阅信息</div>
      </div>
    </div>

    <!-- Template selector -->
    <div class="form-field">
      <label class="field-label">邮件模板</label>
      <n-select
        v-model:value="selectedTemplateId"
        :options="templateOptions"
        placeholder="选择模板（可选）"
        size="large"
        clearable
        @update:value="onTemplateChange"
      />
    </div>

    <!-- Subject & Recipient -->
    <div class="form-field">
      <label class="field-label">邮件标题 *</label>
      <n-input v-model:value="subject" placeholder="邮件标题" size="large" clearable />
    </div>

    <div class="form-row">
      <div class="form-col">
        <label class="field-label">收件人 *</label>
        <n-input v-model:value="recipient" placeholder="user@example.com" size="large" clearable />
      </div>
      <div class="form-col">
        <label class="field-label">抄送 CC</label>
        <n-input v-model:value="cc" placeholder="cc@example.com（多人用逗号分隔）" size="large" clearable />
      </div>
    </div>

    <!-- Dynamic form -->
    <AccountForm v-if="emailType === 'account'" v-model="formData" />
    <SubscriptionForm v-else v-model="formData" />

    <!-- Email body editor -->
    <div class="preview-card">
      <div class="preview-header">邮件正文（Markdown，可编辑）</div>
      <n-input
        v-model:value="body"
        type="textarea"
        :autosize="{ minRows: 6, maxRows: 20 }"
        size="large"
        placeholder="在此编辑邮件正文，支持 Markdown 语法…"
        @update:value="onBodyEdited"
      />
    </div>

    <!-- Preview button -->
    <div class="preview-btn-row">
      <n-button size="large" @click="previewVisible = true">
        <template #icon><n-icon><eye-outline /></n-icon></template>
        预览邮件
      </n-button>
    </div>

    <!-- Preview modal -->
    <n-modal v-model:show="previewVisible" preset="card" title="邮件预览" style="max-width:720px">
      <div v-if="body" class="preview-body" v-html="htmlPreview"></div>
      <div v-else class="preview-empty">暂无正文内容</div>
    </n-modal>

    <!-- Signature selector -->
    <div class="form-field">
      <label class="field-label">邮件签名</label>
      <n-select
        v-model:value="selectedSignatureId"
        :options="signatureOptions"
        placeholder="选择签名（可选）"
        size="large"
        clearable
      />
    </div>

    <!-- Send -->
    <n-button
      type="primary"
      size="large"
      :loading="sending"
      :disabled="!canSend"
      block
      @click="handleSend"
    >
      <template #icon><n-icon><send-outline /></n-icon></template>
      发送邮件
    </n-button>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onActivated, onBeforeUnmount } from "vue";
import { NInput, NSelect, NButton, NIcon, NModal, useMessage } from "naive-ui";
import { PersonOutline, CubeOutline, SendOutline, EyeOutline, TrashOutline } from "@vicons/ionicons5";
import { marked } from "marked";
import TurndownService from "turndown";
import AccountForm from "@/components/AccountForm.vue";
import SubscriptionForm from "@/components/SubscriptionForm.vue";
import { sendEmail, getTemplates, getSignatures } from "@/api";

const message = useMessage();
const emailType = ref("account");
const selectedTemplateId = ref(null);
const selectedSignatureId = ref(null);
const subject = ref("");
const recipient = ref("");
const cc = ref("");
const body = ref("");
const userEditedBody = ref(false);
const previewVisible = ref(false);
const sending = ref(false);

const formData = ref({});
const templates = ref([]);
const signatures = ref([]);
const bodySource = ref("");

const turndown = new TurndownService({ linkStyle: "referenced", headingStyle: "atx" });

const templateOptions = computed(() =>
  templates.value
    .filter((t) => t.type === emailType.value)
    .map((t) => ({ label: t.name, value: t.id }))
);

const signatureOptions = computed(() =>
  signatures.value.map((s) => ({ label: s.name, value: s.id }))
);

const htmlPreview = computed(() => {
  if (!body.value) return "";
  return marked.parse(body.value);
});

const canSend = computed(() => {
  if (!subject.value || !recipient.value) return false;
  if (emailType.value === "account") {
    const accounts = formData.value.accounts;
    return accounts && accounts.length > 0 && accounts.some((a) => a.account && a.password && a.account_type);
  }
  const subs = formData.value.subscriptions;
  return subs && subs.length > 0 && subs.some((s) => s.subscription_id || s.subscription_name);
});

// ── Lifecycle ───────────────────────

onMounted(async () => {
  try {
    const [tRes, sRes] = await Promise.all([getTemplates(), getSignatures()]);
    templates.value = tRes.data;
    signatures.value = sRes.data;
  } catch { /* ignore */ }
  loadDraft();
});

onActivated(async () => {
  try {
    const [tRes, sRes] = await Promise.all([getTemplates(), getSignatures()]);
    templates.value = tRes.data;
    signatures.value = sRes.data;
    if (selectedTemplateId.value) {
      const t = templates.value.find((tp) => tp.id === selectedTemplateId.value);
      if (t) {
        bodySource.value = t.content;
        userEditedBody.value = false;
        body.value = renderTemplateContent(t.content);
      }
    }
  } catch { /* ignore */ }
});

// ── Template rendering ──────────────

function renderTemplateContent(templateContent) {
  if (!templateContent) return "";

  // Try new JSON format: {"header": "...", "item": "...", "footer": "..."}
  try {
    const tpl = JSON.parse(templateContent);
    if (tpl && typeof tpl === "object" && "item" in tpl) {
      return renderNewFormat(tpl);
    }
  } catch { /* legacy format */ }

  // Legacy format: {account_list} / {subscription_list} markers in HTML
  let html = templateContent;
  if (emailType.value === "account") {
    const accounts = formData.value.accounts || [];
    const lines = accounts
      .filter((a) => a.account || a.password || a.account_type)
      .map((a, i) => `${i + 1}. ${a.account} / ${a.password} / ${a.account_type}`);
    html = html.replace("{account_list}", lines.join("<br>") || "（无）");
  } else {
    const subs = formData.value.subscriptions || [];
    const lines = subs
      .filter((s) => s.subscription_id || s.subscription_name)
      .map((s, i) => `${i + 1}. ${s.subscription_id} - ${s.subscription_name}`);
    html = html.replace("{subscription_list}", lines.join("<br>") || "（无）");
  }
  return turndown.turndown(html);
}

function renderNewFormat(tpl) {
  let header = tpl.header || "";
  const itemTpl = tpl.item || "";
  const footer = tpl.footer || "";

  if (emailType.value === "account") {
    const accounts = formData.value.accounts || [];
    const count = accounts.filter((a) => a.account || a.password || a.account_type).length;
    header = header.replaceAll("{account_plural}", count === 1 ? "account" : "accounts");

    const items = accounts
      .filter((a) => a.account || a.password || a.account_type)
      .map((a) => {
        let part = itemTpl;
        part = part.replaceAll("{username}", a.account || "");
        part = part.replaceAll("{password}", a.password || "");
        part = part.replaceAll("{account_type}", a.account_type || "");
        return part;
      });

    const parts = [header, ...items, footer].filter((p) => p.trim());
    // Convert HTML (from rich text editor) to Markdown for the textarea
    return turndown.turndown(parts.join("\n\n"));
  } else {
    const subs = formData.value.subscriptions || [];
    const count = subs.filter((s) => s.subscription_id || s.subscription_name).length;
    header = header.replaceAll("{subscription_plural}", count === 1 ? "subscription" : "subscriptions");

    const items = subs
      .filter((s) => s.subscription_id || s.subscription_name)
      .map((s) => {
        let part = itemTpl;
        part = part.replaceAll("{subscription_id}", s.subscription_id || "");
        part = part.replaceAll("{subscription_name}", s.subscription_name || "");
        return part;
      });

    const parts = [header, ...items, footer].filter((p) => p.trim());
    return turndown.turndown(parts.join("\n\n"));
  }
}

// Substitute new-format markers in plain text (no-template fallback)
function substitutePlainMarkers(text) {
  if (emailType.value === "account") {
    const accounts = (formData.value.accounts || []).filter((a) => a.account || a.password || a.account_type);
    text = text.replaceAll("{account_plural}", accounts.length === 1 ? "account" : "accounts");
    text = text.replace("{account_list}", accounts
      .map((a, i) => `${i + 1}. ${a.account} / ${a.password} / ${a.account_type}`)
      .join("  \n") || "（无）");
    // Per-item markers: only makes sense for single-account manual typing.
    // For multiple, just show the first — the backend will render properly.
    if (accounts.length >= 1) {
      text = text.replaceAll("{username}", accounts[0].account || "");
      text = text.replaceAll("{password}", accounts[0].password || "");
      text = text.replaceAll("{account_type}", accounts[0].account_type || "");
    }
  } else {
    const subs = (formData.value.subscriptions || []).filter((s) => s.subscription_id || s.subscription_name);
    text = text.replaceAll("{subscription_plural}", subs.length === 1 ? "subscription" : "subscriptions");
    text = text.replace("{subscription_list}", subs
      .map((s, i) => `${i + 1}. ${s.subscription_id} - ${s.subscription_name}`)
      .join("  \n") || "（无）");
    if (subs.length >= 1) {
      text = text.replaceAll("{subscription_id}", subs[0].subscription_id || "");
      text = text.replaceAll("{subscription_name}", subs[0].subscription_name || "");
    }
  }
  return text;
}

// ── Event handlers ──────────────────

function switchType(type) {
  if (emailType.value === type) return;
  saveDraft();
  emailType.value = type;
  selectedTemplateId.value = null;
  bodySource.value = "";
  body.value = "";
  userEditedBody.value = false;
  formData.value = {};
  loadDraft();
}

function handleClear() {
  selectedTemplateId.value = null;
  selectedSignatureId.value = null;
  subject.value = "";
  recipient.value = "";
  cc.value = "";
  body.value = "";
  bodySource.value = "";
  userEditedBody.value = false;
  formData.value = {};
  clearDraft();
}

function onTemplateChange(id) {
  if (!id) {
    bodySource.value = "";
    body.value = "";
    return;
  }
  const t = templates.value.find((tp) => tp.id === id);
  if (t) {
    bodySource.value = t.content;
    userEditedBody.value = false;
    body.value = renderTemplateContent(t.content);
  }
}

function onBodyEdited() {
  // @update:value only fires for user input, not programmatic changes
  userEditedBody.value = true;
}

// Re-render body when formData changes
watch([formData, emailType], () => {
  if (selectedTemplateId.value) {
    // Template selected: re-render from template content (unless user edited manually)
    if (userEditedBody.value) return;
    const t = templates.value.find((tp) => tp.id === selectedTemplateId.value);
    if (t) {
      bodySource.value = t.content;
      body.value = renderTemplateContent(t.content);
    }
    return;
  }
  // No template selected — auto-detect manually typed variables in the body.
  // This path always runs; userEditedBody doesn't block it because the user
  // explicitly typed variables and expects sync.
  const markers = [
    "{account_list}", "{subscription_list}",
    "{account_plural}", "{subscription_plural}",
    "{username}", "{password}", "{account_type}",
    "{subscription_id}", "{subscription_name}",
  ];
  if (body.value && markers.some((m) => body.value.includes(m))) {
    bodySource.value = body.value;
    body.value = substitutePlainMarkers(bodySource.value);
  }
}, { deep: true });

// ── Draft persistence ───────────────

const DRAFT_KEY_PREFIX = "mailswift_draft_";

function draftKey() {
  return DRAFT_KEY_PREFIX + emailType.value;
}

function saveDraft() {
  const draft = {
    emailType: emailType.value,
    selectedTemplateId: selectedTemplateId.value,
    selectedSignatureId: selectedSignatureId.value,
    subject: subject.value,
    recipient: recipient.value,
    cc: cc.value,
    body: body.value,
    formData: formData.value,
  };
  try {
    localStorage.setItem(draftKey(), JSON.stringify(draft));
  } catch { /* quota exceeded, ignore */ }
}

function loadDraft() {
  try {
    const raw = localStorage.getItem(draftKey());
    if (!raw) return;
    const draft = JSON.parse(raw);
    selectedTemplateId.value = draft.selectedTemplateId || null;
    selectedSignatureId.value = draft.selectedSignatureId || null;
    subject.value = draft.subject || "";
    recipient.value = draft.recipient || "";
    cc.value = draft.cc || "";
    body.value = draft.body || "";
    formData.value = draft.formData || {};
  } catch { /* ignore */ }
}

// Auto-save draft every 3 seconds
let draftTimer = null;
watch([emailType, selectedTemplateId, selectedSignatureId, subject, recipient, cc, body, formData], () => {
  clearTimeout(draftTimer);
  draftTimer = setTimeout(saveDraft, 3000);
}, { deep: true });

onBeforeUnmount(() => {
  clearTimeout(draftTimer);
});

// ── Send ────────────────────────────

async function handleSend() {
  if (sending.value) return;  // guard against double-click
  sending.value = true;
  try {
    const payload = {
      email_type: emailType.value,
      recipient: recipient.value,
      cc: cc.value,
      subject: subject.value,
      body: body.value,
      template_id: selectedTemplateId.value || null,
      signature_id: selectedSignatureId.value || null,
    };
    if (emailType.value === "account") {
      payload.accounts = (formData.value.accounts || []).map((a) => ({
        account: a.account,
        password: a.password,
        account_type: a.account_type,
      }));
      payload.subscriptions = [];
    } else {
      payload.accounts = [];
      payload.subscriptions = (formData.value.subscriptions || []).map((s) => ({
        subscription_id: s.subscription_id,
        subscription_name: s.subscription_name,
      }));
    }
    const res = await sendEmail(payload);
    const archiveMsg = res.data.archive_status === "archived" ? "，已存档至已发送" : "";
    message.success("邮件发送成功" + archiveMsg);
    clearDraft();
  } catch (err) {
    message.error(err.response?.data?.detail || "发送失败");
  } finally {
    sending.value = false;
  }
}

function clearDraft() {
  try {
    localStorage.removeItem(draftKey());
  } catch { /* ignore */ }
}
</script>

<style scoped>
.home {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.4px;
  margin-bottom: 0;
}

.type-switcher {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 28px;
}

.type-card {
  padding: 20px;
  border-radius: 14px;
  border: 2px solid transparent;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.type-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.type-card.active {
  border-color: #0071e3;
  background: #f0f7ff;
}

.type-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #f5f5f7;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  color: #6e6e73;
}

.type-card.active .type-icon {
  background: #0071e3;
  color: #fff;
}

.type-label {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.type-desc {
  font-size: 13px;
  color: #86868b;
}

.form-field {
  margin-bottom: 20px;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin-bottom: 6px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.preview-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.preview-header {
  font-size: 12px;
  font-weight: 600;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.preview-body {
  font-size: 14px;
  line-height: 1.7;
  color: #1d1d1f;
  word-break: break-word;
}

.preview-body :deep(a) {
  color: #0071e3;
}

.preview-body :deep(img) {
  max-width: 100%;
}

.preview-body :deep(p) {
  margin: 0 0 8px;
}

.preview-body :deep(ul),
.preview-body :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.preview-empty {
  font-size: 14px;
  color: #86868b;
  text-align: center;
  padding: 20px 0;
}

.preview-btn-row {
  margin-bottom: 24px;
}
</style>
