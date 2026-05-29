<template>
  <div class="home">
    <div class="title-row">
      <div class="page-title">发送邮件</div>
      <n-button text type="error" size="small" @click="handleClear">
        <template #icon><SvgIcon name="trash" /></template>
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
          <SvgIcon name="person" :size="24" />
        </div>
        <div class="type-label">账号创建/重置</div>
        <div class="type-desc">发送账号和密码信息</div>
      </div>
      <div
        class="type-card"
        :class="{ active: emailType === 'subscription' }"
        @click="switchType('subscription')"
      >
        <div class="type-icon">
          <SvgIcon name="cube" :size="24" />
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
        <n-input v-model:value="recipient" placeholder="user@example.com" size="large" clearable :status="recipientError ? 'error' : undefined" />
        <span v-if="recipientError" class="field-error">{{ recipientError }}</span>
      </div>
      <div class="form-col">
        <label class="field-label">抄送 CC</label>
        <n-input v-model:value="cc" placeholder="cc@example.com（多人用逗号分隔）" size="large" clearable :status="ccError ? 'error' : undefined" />
        <span v-if="ccError" class="field-error">{{ ccError }}</span>
      </div>
    </div>

    <!-- Dynamic form -->
    <AccountForm v-if="emailType === 'account'" v-model="formData" />
    <SubscriptionForm v-else v-model="formData" />

    <!-- Email body editor -->
    <div class="preview-card">
      <div class="preview-header">邮件正文（富文本编辑）</div>
      <RichTextEditor
        ref="rteRef"
        v-model="body"
        @update:model-value="onBodyEdited"
      />
    </div>

    <!-- Preview button -->
    <div class="preview-btn-row">
      <n-button size="large" @click="previewVisible = true">
        <template #icon><SvgIcon name="eye" /></template>
        预览邮件
      </n-button>
    </div>

    <!-- Preview modal -->
    <n-modal v-model:show="previewVisible" preset="card" title="邮件预览" style="max-width:720px">
      <div v-if="body" class="preview-body" v-html="previewHtml"></div>
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
      <template #icon><SvgIcon name="send" /></template>
      发送邮件
    </n-button>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onActivated, onBeforeUnmount } from "vue";
import { NInput, NSelect, NButton, NModal, useMessage } from "naive-ui";
import SvgIcon from "@/components/SvgIcon.vue";
import RichTextEditor from "@/components/RichTextEditor.vue";
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

const rteRef = ref(null);
const formData = ref({});
const templates = ref([]);
const signatures = ref([]);
const bodySource = ref("");

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(str) {
  return EMAIL_RE.test(str.trim());
}

const recipientError = computed(() => {
  if (!recipient.value) return "";
  if (!isValidEmail(recipient.value)) return "邮箱格式不正确";
  return "";
});

const ccError = computed(() => {
  if (!cc.value) return "";
  const invalid = cc.value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .filter((addr) => !isValidEmail(addr));
  if (invalid.length > 0) return `以下地址格式不正确：${invalid.join("、")}`;
  return "";
});

const templateOptions = computed(() =>
  templates.value
    .filter((t) => t.type === emailType.value)
    .map((t) => ({ label: t.name, value: t.id }))
);

const signatureOptions = computed(() =>
  signatures.value.map((s) => ({ label: s.name, value: s.id }))
);

const previewHtml = computed(() => {
  let html = body.value || "";
  if (selectedSignatureId.value) {
    const sig = signatures.value.find((s) => s.id === selectedSignatureId.value);
    if (sig && sig.content) {
      html += "<hr>" + sig.content;
    }
  }
  return html;
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

  try {
    const tpl = JSON.parse(templateContent);
    if (tpl && typeof tpl === "object" && "item" in tpl) {
      return renderNewFormat(tpl);
    }
  } catch { /* legacy format */ }

  let html = templateContent;
  if (emailType.value === "account") {
    const accounts = formData.value.accounts || [];
    const lines = accounts
      .filter((a) => a.account || a.password || a.account_type)
      .map((a, i) => `${i + 1}. ${a.account} / ${a.password} / ${a.account_type}`);
    html = html.replaceAll("{account_list}", lines.join("<br>") || "（无）");
  } else {
    const subs = formData.value.subscriptions || [];
    const lines = subs
      .filter((s) => s.subscription_id || s.subscription_name)
      .map((s, i) => `${i + 1}. ${s.subscription_id} - ${s.subscription_name}`);
    html = html.replaceAll("{subscription_list}", lines.join("<br>") || "（无）");
  }
  return html;
}

function renderNewFormat(tpl) {
  let header = tpl.header || "";
  const itemTpl = tpl.item || "";
  const footer = tpl.footer || "";

  if (emailType.value === "account") {
    const accounts = formData.value.accounts || [];
    const count = accounts.filter((a) => a.account || a.password || a.account_type).length;
    header = header.replaceAll("{account_plural}", count === 1 ? "account" : "accounts");
    header = header.replaceAll("{have_has}", count === 1 ? "has" : "have");

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
    return parts.join("");
  } else {
    const subs = formData.value.subscriptions || [];
    const count = subs.filter((s) => s.subscription_id || s.subscription_name).length;
    header = header.replaceAll("{subscription_plural}", count === 1 ? "subscription" : "subscriptions");
    header = header.replaceAll("{have_has}", count === 1 ? "has" : "have");

    const items = subs
      .filter((s) => s.subscription_id || s.subscription_name)
      .map((s) => {
        let part = itemTpl;
        part = part.replaceAll("{subscription_id}", s.subscription_id || "");
        part = part.replaceAll("{subscription_name}", s.subscription_name || "");
        return part;
      });

    const parts = [header, ...items, footer].filter((p) => p.trim());
    return parts.join("");
  }
}

// Substitute new-format markers in plain text (no-template fallback)
function substitutePlainMarkers(text) {
  if (emailType.value === "account") {
    const accounts = (formData.value.accounts || []).filter((a) => a.account || a.password || a.account_type);
    text = text.replaceAll("{account_plural}", accounts.length === 1 ? "account" : "accounts");
    text = text.replaceAll("{have_has}", accounts.length === 1 ? "has" : "have");
    text = text.replaceAll("{account_list}", accounts
      .map((a, i) => `${i + 1}. ${a.account} / ${a.password} / ${a.account_type}`)
      .join("<br>") || "（无）");
    if (accounts.length >= 1) {
      text = text.replaceAll("{username}", accounts[0].account || "");
      text = text.replaceAll("{password}", accounts[0].password || "");
      text = text.replaceAll("{account_type}", accounts[0].account_type || "");
    }
  } else {
    const subs = (formData.value.subscriptions || []).filter((s) => s.subscription_id || s.subscription_name);
    text = text.replaceAll("{subscription_plural}", subs.length === 1 ? "subscription" : "subscriptions");
    text = text.replaceAll("{have_has}", subs.length === 1 ? "has" : "have");
    text = text.replaceAll("{subscription_list}", subs
      .map((s, i) => `${i + 1}. ${s.subscription_id} - ${s.subscription_name}`)
      .join("<br>") || "（无）");
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
    "{have_has}",
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
  if (recipientError.value) {
    message.warning("收件人邮箱格式不正确");
    return;
  }
  if (ccError.value) {
    message.warning(ccError.value);
    return;
  }
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
    // Attachments
    const files = rteRef.value?.getAttachments() || [];
    if (files.length) {
      payload.attachments = await Promise.all(
        files.map(
          (f) =>
            new Promise((resolve) => {
              const reader = new FileReader();
              reader.onload = (e) => {
                resolve({
                  filename: f.name,
                  content_base64: e.target.result.split(",")[1],
                });
              };
              reader.readAsDataURL(f);
            })
        )
      );
    }

    await sendEmail(payload);
    message.success("邮件发送成功");
    handleClear();
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

.field-error {
  display: block;
  font-size: 12px;
  color: #d03050;
  margin-top: 4px;
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
  font-size: 16px;
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
