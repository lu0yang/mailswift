<template>
  <div class="home">
    <div class="page-title">发送邮件</div>

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
      />
    </div>

    <!-- Live preview -->
    <div class="preview-card">
      <div class="preview-header">邮件预览</div>
      <div class="preview-body" v-html="htmlPreview"></div>
      <div v-if="!body" class="preview-empty">输入正文后此处显示实时预览</div>
    </div>

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

    <!-- BCC self -->
    <div class="bcc-row">
      <n-checkbox v-model:checked="bccSelf">抄送自己一份</n-checkbox>
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
import { ref, computed, watch, onMounted } from "vue";
import { NInput, NSelect, NButton, NIcon, NCheckbox, useMessage } from "naive-ui";
import { PersonOutline, CubeOutline, SendOutline } from "@vicons/ionicons5";
import { marked } from "marked";
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
const bccSelf = ref(false);
const body = ref("");
const sending = ref(false);

const formData = ref({});
const templates = ref([]);
const signatures = ref([]);

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

// ── Template rendering ──────────────

function renderTemplateContent(templateContent) {
  let result = templateContent;
  if (emailType.value === "account") {
    const accounts = formData.value.accounts || [];
    const lines = accounts
      .filter((a) => a.account || a.password || a.account_type)
      .map((a, i) => `${i + 1}. ${a.account} / ${a.password} / ${a.account_type}`);
    result = result.replace("{account_list}", lines.join("\n") || "（无）");
  } else {
    const subs = formData.value.subscriptions || [];
    const lines = subs
      .filter((s) => s.subscription_id || s.subscription_name)
      .map((s, i) => `${i + 1}. ${s.subscription_id} - ${s.subscription_name}`);
    result = result.replace("{subscription_list}", lines.join("\n") || "（无）");
  }
  return result;
}

// ── Event handlers ──────────────────

function switchType(type) {
  if (emailType.value === type) return;
  saveDraft();
  emailType.value = type;
  selectedTemplateId.value = null;
  body.value = "";
  formData.value = {};
  loadDraft();
}

function onTemplateChange(id) {
  if (!id) {
    body.value = "";
    return;
  }
  const t = templates.value.find((tp) => tp.id === id);
  if (t) {
    body.value = renderTemplateContent(t.content);
  }
}

// Re-render body when formData changes (if a template is selected)
watch([formData, emailType], () => {
  if (!selectedTemplateId.value) return;
  const t = templates.value.find((tp) => tp.id === selectedTemplateId.value);
  if (t) {
    body.value = renderTemplateContent(t.content);
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
    bccSelf: bccSelf.value,
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
    bccSelf.value = draft.bccSelf || false;
    body.value = draft.body || "";
    formData.value = draft.formData || {};
  } catch { /* ignore */ }
}

// Auto-save draft every 3 seconds
let draftTimer = null;
watch([emailType, selectedTemplateId, selectedSignatureId, subject, recipient, cc, bccSelf, body, formData], () => {
  clearTimeout(draftTimer);
  draftTimer = setTimeout(saveDraft, 3000);
}, { deep: true });

// ── Send ────────────────────────────

async function handleSend() {
  sending.value = true;
  try {
    const payload = {
      email_type: emailType.value,
      recipient: recipient.value,
      cc: cc.value,
      subject: subject.value,
      body: body.value,
      bcc_self: bccSelf.value,
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

.page-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.4px;
  margin-bottom: 28px;
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

.bcc-row {
  margin-bottom: 20px;
}
</style>
