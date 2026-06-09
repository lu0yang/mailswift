<template>
  <div class="home">
    <div class="title-row">
      <div class="page-title">发送邮件</div>
      <div class="title-actions">
        <n-button text size="small" @click="handleSaveDraft" :disabled="!isDirty">
          <template #icon><SvgIcon name="save" /></template>
          暂存草稿
        </n-button>
        <n-button text type="error" size="small" @click="handleClear">
          <template #icon><SvgIcon name="trash" /></template>
          一键清理
        </n-button>
      </div>
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
      <div
        class="type-card"
        :class="{ active: emailType === 'high_priority' }"
        @click="switchType('high_priority')"
      >
        <div class="type-icon">
          <SvgIcon name="alert" :size="24" />
        </div>
        <div class="type-label">High Priority</div>
        <div class="type-desc">发送 Incident 通知</div>
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

    <!-- 关联单号查询 (HP non-INITIAL only) -->
    <div v-if="emailType === 'high_priority' && hpStatusPrefix !== 'INITIAL'" class="lookup-section">
      <div class="lookup-row">
        <n-input
          v-model:value="lookupTicketId"
          placeholder="输入关联 Ticket ID 查询 INITIAL 事件"
          size="large"
          :input-props="{ autocomplete: 'off' }"
          style="flex:1"
        />
        <n-button type="primary" size="large" :loading="lookupLoading" @click="handleLookupIncident">
          查询并复用
        </n-button>
      </div>
      <div v-if="lookupResult && lookupResult.found" class="lookup-hint lookup-hint-success">
        ✅ 已从 INITIAL 事件 [{{ lookupResult.ticketId }}] 中复用以下字段：收件人、抄送、Severity、Category、Title、Description、Start Date &amp; Time、Impact、Operations Manager、Incident Bridge
      </div>
      <div v-if="lookupResult && !lookupResult.found" class="lookup-hint lookup-hint-warn">
        ⚠️ 未找到关联事件，请手动填写表单信息
      </div>
    </div>

    <!-- Subject & Recipient -->
    <div v-if="emailType !== 'high_priority'" class="form-field">
      <label class="field-label">邮件标题 *</label>
      <div class="field-wrapper">
        <n-input
          v-model:value="subject"
          placeholder="邮件标题"
          size="large"
          clearable
          :input-props="{ autocomplete: 'off' }"
          @focus="cancelDropdownHide(); subjectDropdownShow = filteredSubjectHistory.length > 0"
          @blur="hideDropdownWithDelay(subjectDropdownShow)"
        />
        <div v-if="subjectDropdownShow" class="history-dropdown">
          <div
            v-for="item in filteredSubjectHistory"
            :key="item"
            class="history-dropdown-item"
            @mousedown.prevent="subject = item; subjectDropdownShow = false"
          >
            {{ item }}
          </div>
          <div v-if="filteredSubjectHistory.length === 0" class="history-dropdown-empty">
            无匹配记录
          </div>
        </div>
      </div>
    </div>

    <div class="form-row">
      <div class="form-col">
        <label class="field-label">收件人 *</label>
        <div class="field-wrapper">
          <div class="pill-input-shell" :class="{ 'pill-input-error': recipientError }">
            <span v-for="(addr, i) in recipientTags" :key="i" class="pill-tag" :class="{ editing: editRecipientIdx === i }" @dblclick="editRecipientIdx = i">
              <template v-if="editRecipientIdx === i">
                <input
                  v-model="recipientTags[i]"
                  class="pill-edit-input"
                  @keyup.enter="editRecipientIdx = -1"
                  @blur="editRecipientIdx = -1"
                  @click.stop
                />
              </template>
              <template v-else>
                {{ addr }}<button class="pill-tag-x" @click="recipientTags.splice(i, 1)">×</button>
              </template>
            </span>
            <div class="pill-auto">
              <n-input
                v-model:value="recipientInput"
                placeholder="输入邮箱，回车添加"
                size="small"
                :input-props="{ autocomplete: 'off' }"
                @keyup.enter.prevent="addRecipientTag()"
                @focus="cancelDropdownHide(); recipientDropdownShow = filteredRecipientHistory.length > 0"
                @blur="addRecipientTag(); hideDropdownWithDelay(recipientDropdownShow)"
              />
            </div>
          </div>
          <div v-if="recipientDropdownShow" class="history-dropdown">
            <div
              v-for="item in filteredRecipientHistory"
              :key="item"
              class="history-dropdown-item"
              @mousedown.prevent="recipientInput = item; recipientDropdownShow = false"
            >
              {{ item }}
            </div>
            <div v-if="filteredRecipientHistory.length === 0" class="history-dropdown-empty">
              无匹配记录
            </div>
          </div>
        </div>
        <span v-if="recipientError" class="field-error">{{ recipientError }}</span>
      </div>
      <div class="form-col">
        <label class="field-label">抄送 CC</label>
        <div class="field-wrapper">
          <div class="pill-input-shell">
            <span v-for="(addr, i) in ccTags" :key="i" class="pill-tag" :class="{ editing: editCcIdx === i }" @dblclick="editCcIdx = i">
              <template v-if="editCcIdx === i">
                <input
                  v-model="ccTags[i]"
                  class="pill-edit-input"
                  @keyup.enter="editCcIdx = -1"
                  @blur="editCcIdx = -1"
                  @click.stop
                />
              </template>
              <template v-else>
                {{ addr }}<button class="pill-tag-x" @click="ccTags.splice(i, 1)">×</button>
              </template>
            </span>
            <div class="pill-auto">
              <n-input
                v-model:value="ccInput"
                placeholder="输入邮箱，回车添加"
                size="small"
                :input-props="{ autocomplete: 'off' }"
                @keyup.enter.prevent="addCcTag()"
                @focus="cancelDropdownHide(); ccDropdownShow = filteredCcHistory.length > 0"
                @blur="addCcTag(); hideDropdownWithDelay(ccDropdownShow)"
              />
            </div>
          </div>
          <div v-if="ccDropdownShow" class="history-dropdown">
            <div
              v-for="item in filteredCcHistory"
              :key="item"
              class="history-dropdown-item"
              @mousedown.prevent="ccInput = item; ccDropdownShow = false"
            >
              {{ item }}
            </div>
            <div v-if="filteredCcHistory.length === 0" class="history-dropdown-empty">
              无匹配记录
            </div>
          </div>
        </div>
        <span v-if="ccError" class="field-error">{{ ccError }}</span>
      </div>
    </div>

    <!-- Dynamic form -->
    <AccountForm v-if="emailType === 'account'" v-model="formData" />
    <SubscriptionForm v-else-if="emailType === 'subscription'" v-model="formData" />
    <HighPriorityForm v-else-if="emailType === 'high_priority'" v-model="formData">
      <!-- UPDATED: Update between Impact and Operations Manager -->
      <template v-if="hpStatusPrefix === 'UPDATED'" #after-impact>
        <div class="form-field">
          <label class="field-label">Update *</label>
          <RichTextEditor
            ref="updateEditorRef"
            v-model="updateHtml"
          />
        </div>
      </template>
      <!-- MITIGATED: Update after Operations Manager, before Resolution -->
      <template v-if="hpStatusPrefix === 'MITIGATED'" #after-operations>
        <div class="form-field">
          <label class="field-label">Update *</label>
          <RichTextEditor
            ref="updateMitigatedEditorRef"
            v-model="updateHtml"
          />
        </div>
      </template>
    </HighPriorityForm>

    <!-- Incident Bridge with TipTap editor (HP only) -->
    <div v-if="emailType === 'high_priority'" class="preview-card">
      <div class="preview-header">Incident Bridge *（支持粘贴超链接）</div>
      <RichTextEditor
        ref="incidentBridgeEditorRef"
        v-model="incidentBridgeHtml"
      />
    </div>

    <!-- Email body editor (hidden for HP — body is auto-generated) -->
    <div v-if="emailType !== 'high_priority'" class="preview-card">
      <div class="preview-header">邮件正文（富文本编辑）</div>
      <RichTextEditor
        ref="rteRef"
        v-model="body"
        v-model:attachments="attachments"
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
    <n-modal v-model:show="previewVisible" preset="card" title="邮件预览" style="max-width:1060px">
      <div v-if="recipientTags.length || ccTags.length || subject" class="preview-meta">
        <div v-if="recipientTags.length" class="preview-meta-row">
          <span class="preview-meta-label">收件人</span>
          <span class="preview-meta-val">
            <span v-for="(addr, i) in recipientTags" :key="i" class="preview-pill">{{ addr }}</span>
          </span>
        </div>
        <div v-if="ccTags.length" class="preview-meta-row">
          <span class="preview-meta-label">抄送</span>
          <span class="preview-meta-val">
            <span v-for="(addr, i) in ccTags" :key="i" class="preview-pill">{{ addr }}</span>
          </span>
        </div>
        <div v-if="subject || previewEmailSubject" class="preview-meta-row">
          <span class="preview-meta-label">标题</span>
          <span class="preview-meta-val preview-meta-subject">{{ previewEmailSubject || subject }}</span>
        </div>
      </div>
      <div v-if="body" class="preview-body" v-html="previewHtml"></div>
      <div v-else class="preview-empty">暂无正文内容</div>
      <div v-if="attachments.length" class="preview-attachments">
        <div class="preview-attach-title">附件 ({{ attachments.length }})</div>
        <div v-for="(a, i) in attachments" :key="i" class="preview-attach-item">
          {{ a.name }} <span class="preview-attach-size">{{ formatSize(a.size) }}</span>
        </div>
      </div>
    </n-modal>

    <!-- Signature selector (hidden for HP — signature is outside the body template) -->
    <div v-if="emailType !== 'high_priority'" class="form-field">
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
    <n-tooltip :disabled="canSend" placement="top">
      <template #trigger>
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
      </template>
      <div v-for="h in sendHints" :key="h" class="send-hint-line">{{ h }}</div>
    </n-tooltip>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onActivated, onBeforeUnmount, inject } from "vue";
import { NInput, NSelect, NButton, NModal, NAutoComplete, NTooltip, useMessage, useDialog } from "naive-ui";
import { onBeforeRouteLeave } from "vue-router";
import SvgIcon from "@/components/SvgIcon.vue";
import RichTextEditor from "@/components/RichTextEditor.vue";
import AccountForm from "@/components/AccountForm.vue";
import SubscriptionForm from "@/components/SubscriptionForm.vue";
import HighPriorityForm from "@/components/HighPriorityForm.vue";
import { sendEmail, getTemplates, getSignatures, lookupIncident } from "@/api";

const message = useMessage();
const dialog = useDialog();
const accountEmail = inject("accountEmail", ref(""));
const accountExpired = inject("accountExpired", ref(false));
const emailType = ref("account");
const selectedTemplateId = ref(null);
const selectedSignatureId = ref(null);
const subject = ref("");
const recipientTags = ref([]);
const recipientInput = ref("");
const ccTags = ref([]);
const ccInput = ref("");
const editRecipientIdx = ref(-1);
const editCcIdx = ref(-1);
const body = ref("");
const userEditedBody = ref(false);
const previewVisible = ref(false);
const sending = ref(false);

const rteRef = ref(null);
const incidentBridgeEditorRef = ref(null);
const attachments = ref([]);
const incidentBridgeHtml = ref("");
const updateHtml = ref("");
const lookupTicketId = ref("");
const lookupLoading = ref(false);
const lookupResult = ref(null);  // null | { found: true, ticketId } | { found: false }
const formData = ref({});
const templates = ref([]);
const signatures = ref([]);
const bodySource = ref("");
const isDirty = ref(false);
const suppressDirty = ref(true); // suppressed until init completes
const subjectDropdownShow = ref(false);
const recipientDropdownShow = ref(false);
const ccDropdownShow = ref(false);

let hideDropdownTimer = null;
function hideDropdownWithDelay(showRef) {
  clearTimeout(hideDropdownTimer);
  hideDropdownTimer = setTimeout(() => { showRef.value = false; }, 200);
}
function cancelDropdownHide() {
  clearTimeout(hideDropdownTimer);
}

// Auto-show dropdown as user types (e.g. domain suggestions appearing mid-input)
watch(recipientInput, () => { if (filteredRecipientHistory.value.length) recipientDropdownShow.value = true; });
watch(ccInput, () => { if (filteredCcHistory.value.length) ccDropdownShow.value = true; });

function closeAllDropdowns() {
  subjectDropdownShow.value = false;
  recipientDropdownShow.value = false;
  ccDropdownShow.value = false;
}

function onDocumentClick(e) {
  if (e.target.closest(".field-wrapper")) return;
  closeAllDropdowns();
}

// ── Recipient autocomplete ────────

const DEFAULT_DOMAINS = ["@oe.21vianet.com", "@microsoft.com"];
const PRESET_KEY = "mailswift_preset_domains";
const subjectHistory = ref([]);
const recipientHistory = ref([]);
const ccHistory = ref([]);

function loadSubjectHistory() { subjectHistory.value = loadFieldHistory(FIELD_HISTORY_KEYS.subject); }
function loadRecipientHistory() { recipientHistory.value = loadFieldHistory(FIELD_HISTORY_KEYS.recipient); }
function loadCcHistory() { ccHistory.value = loadFieldHistory(FIELD_HISTORY_KEYS.cc); }

function loadAllFieldHistories() {
  loadSubjectHistory();
  loadRecipientHistory();
  loadCcHistory();
}

const filteredSubjectHistory = computed(() => {
  const val = (subject.value || "").trim().toLowerCase();
  if (!val) return subjectHistory.value;
  return subjectHistory.value.filter((s) => s.toLowerCase().includes(val));
});

function loadPresetDomains() {
  try {
    const raw = localStorage.getItem(PRESET_KEY);
    return raw ? JSON.parse(raw) : [...DEFAULT_DOMAINS];
  } catch { return [...DEFAULT_DOMAINS]; }
}

const filteredRecipientHistory = computed(() => {
  const val = (recipientInput.value || "").trim().toLowerCase();
  const atIdx = val.indexOf("@");
  if (atIdx >= 0) {
    const afterAt = val.slice(atIdx);
    const domains = loadPresetDomains();
    if (domains.some((d) => d === afterAt)) return [];
    const matching = domains.filter((d) => d.startsWith(afterAt));
    if (matching.length) return matching;
  }
  if (!val) return recipientHistory.value;
  return recipientHistory.value.filter((e) => e.toLowerCase().includes(val));
});

const filteredCcHistory = computed(() => {
  const val = (ccInput.value || "").trim().toLowerCase();
  const atIdx = val.indexOf("@");
  if (atIdx >= 0) {
    const afterAt = val.slice(atIdx);
    const domains = loadPresetDomains();
    if (domains.some((d) => d === afterAt)) return [];
    const matching = domains.filter((d) => d.startsWith(afterAt));
    if (matching.length) return matching;
  }
  if (!val) return ccHistory.value;
  return ccHistory.value.filter((e) => e.toLowerCase().includes(val));
});

function addRecipientTag() {
  const val = recipientInput.value.trim();
  if (!val) return;
  recipientInput.value = "";
  if (!recipientTags.value.includes(val)) recipientTags.value.push(val);
}

function addCcTag() {
  const val = ccInput.value.trim();
  if (!val) return;
  ccInput.value = "";
  if (!ccTags.value.includes(val)) ccTags.value.push(val);
}

// Domain-overwrite repair for both fields
function domainWatch(inputRef) {
  watch(inputRef, (val, oldVal) => {
    if (!val || !oldVal) return;
    const oldAt = oldVal.indexOf("@");
    if (oldAt > 0 && val.startsWith("@") && loadPresetDomains().includes(val)) {
      inputRef.value = oldVal.slice(0, oldAt) + val;
    }
  });
}
domainWatch(recipientInput);
domainWatch(ccInput);

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(str) {
  return EMAIL_RE.test(str.trim());
}

const recipientError = computed(() => {
  if (!recipientTags.value.length) return "";
  const bad = recipientTags.value.filter((a) => !isValidEmail(a));
  if (bad.length) return `格式不正确：${bad.join("、")}`;
  return "";
});

const ccError = computed(() => {
  if (!ccTags.value.length) return "";
  const bad = ccTags.value.filter((a) => !isValidEmail(a));
  if (bad.length) return `格式不正确：${bad.join("、")}`;
  return "";
});

const templateOptions = computed(() =>
  templates.value
    .filter((t) => t.type === emailType.value)
    .map((t) => ({ label: t.name, value: t.id }))
);

const signatureOptions = computed(() =>
  signatures.value.map((s) => ({
    label: s.is_default ? s.name + " （默认）" : s.name,
    value: s.id,
  }))
);

const previewEmailSubject = computed(() => {
  if (emailType.value !== "high_priority") return "";
  const d = formData.value || {};
  if (!d.severity && !d.ticket_id && !d.title) return "";
  return `${d.status_prefix || "INITIAL"} ${d.severity || "Sev?"}-Incident [${d.ticket_id || "xxxxxx"}] - ${d.category || "Network"} - ${d.title || ""}`;
});

// Derive HP status_prefix from selected template name
const hpStatusPrefix = computed(() => {
  if (emailType.value !== "high_priority") return "INITIAL";
  if (!selectedTemplateId.value) return "INITIAL";
  const t = templates.value.find((tp) => tp.id === selectedTemplateId.value);
  if (!t) return "INITIAL";
  const name = (t.name || "").toUpperCase();
  if (name.includes("UPDATED")) return "UPDATED";
  if (name.includes("MITIGATED")) return "MITIGATED";
  return "INITIAL";
});

async function handleLookupIncident() {
  const tid = lookupTicketId.value.trim();
  if (!tid) return;
  lookupLoading.value = true;
  lookupResult.value = null;
  try {
    const res = await lookupIncident(tid);
    if (res.data.ok) {
      const stored = res.data.data.form_data || {};
      formData.value = {
        ...formData.value,
        severity: stored.severity || formData.value.severity || "",
        ticket_id: stored.ticket_id || formData.value.ticket_id || tid,
        category: stored.category || formData.value.category || "Network",
        title: stored.title || formData.value.title || "",
        description: stored.description || formData.value.description || "",
        start_datetime: stored.start_datetime || formData.value.start_datetime || "",
        impact: stored.impact || formData.value.impact || "No impact",
        managers: stored.managers || formData.value.managers || [],
      };
      incidentBridgeHtml.value = stored.incidentBridgeHtml || "";
      updateHtml.value = stored.updateHtml || "";
      // Restore recipient/CC
      const restoredRecipient = stored.recipient || "";
      recipientTags.value = restoredRecipient ? restoredRecipient.split(",").filter(Boolean) : recipientTags.value;
      const restoredCc = stored.cc || "";
      ccTags.value = restoredCc ? restoredCc.split(",").filter(Boolean) : ccTags.value;
      lookupResult.value = { found: true, ticketId: tid };
    } else {
      lookupResult.value = { found: false };
    }
  } catch {
    lookupResult.value = { found: false };
  } finally {
    lookupLoading.value = false;
  }
}

const previewHtml = computed(() => {
  let html = body.value || "";
  if (selectedSignatureId.value) {
    const sig = signatures.value.find((s) => s.id === selectedSignatureId.value);
    if (sig && sig.content) {
      html += "<br>" + sig.content;
    }
  }
  return html;
});

// ── High Priority body rendering ────

function todayStr() {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${m}/${dd}/${d.getFullYear()}`;
}

function managersToHtml(managers) {
  return (managers || []).map((m) =>
    `${m.name} <a href="mailto:${m.email}">${m.email}</a>`
  ).join("; ");
}

function autoLink(text) {
  if (!text) return "";
  return text.replace(
    /(https?:\/\/[^\s<>]+)/gi,
    '<a href="$1" target="_blank" style="color:#0071e3;text-decoration:underline">$1</a>'
  );
}

function buildTitleLine(d) {
  const sev = d.severity || "Sev?";
  const tid = d.ticket_id || "xxxxxx";
  const cat = d.category || "Network";
  const ttl = d.title || "";
  return `${d.status_prefix || "INITIAL"} – ${sev} – ${cat} – ${ttl}`;
}

function renderHighPriorityBody(templateContent) {
  if (!templateContent) return "";
  const d = formData.value || {};
  let html = templateContent;
  html = html.replaceAll("{title_line}", buildTitleLine(d));
  html = html.replaceAll("{date}", d.date || "");
  html = html.replaceAll("{current_status}", d.current_status || "");
  html = html.replaceAll("{description}", (d.description || "").replace(/\n/g, "<br>"));
  html = html.replaceAll("{start_datetime}", d.start_datetime || "");
  html = html.replaceAll("{impact}", d.impact || "");
  html = html.replaceAll("{managers}", managersToHtml(d.managers));
  html = html.replaceAll("{next_update}", d.next_update || "");
  html = html.replaceAll("{update}", updateHtml.value || "");
  html = html.replaceAll("{resolution}", d.resolution || "");
  html = html.replaceAll("{end_datetime}", d.end_datetime || "");
  html = html.replaceAll("{incident_bridge}", incidentBridgeHtml.value);
  return html;
}

const sendHints = computed(() => {
  const hints = [];
  if (!accountEmail.value) hints.push("请先在设置中配置邮箱凭据");
  else if (accountExpired.value) hints.push("凭据已过期，请更新密码");
  if (emailType.value !== "high_priority" && !subject.value) hints.push("请填写邮件标题");
  if (!body.value.trim()) hints.push("请填写邮件正文");
  if (!recipientTags.value.length) hints.push("请添加至少一个收件人");
  else if (recipientError.value) hints.push(recipientError.value);
  if (ccError.value) hints.push(ccError.value);
  if (emailType.value === "high_priority") {
    const d = formData.value || {};
    if (!d.severity) hints.push("请选择 Severity");
    if (!d.ticket_id) hints.push("请填写 Ticket ID");
    if (!d.title) hints.push("请填写 Title");
    if (!d.description) hints.push("请填写 Description");
    const startDt = (d.start_datetime || "").replace(/Beijing Time\(GMT\+8\)\s*:\s*/i, "").trim();
    if (!startDt) hints.push("请完整填写 Start Date & Time（在 Beijing Time(GMT+8) : 后面填写日期时间）");
    else if (!/^(0[1-9]|1[0-2])\/(0[1-9]|[12]\d|3[01])\/\d{4}\s+([01]\d|2[0-3]):[0-5]\d$/.test(startDt)) hints.push("Start Date & Time 格式不正确，应为 MM/DD/YYYY HH:MM");
    if (!incidentBridgeHtml.value.trim()) hints.push("请填写 Incident Bridge");
    if (hpStatusPrefix.value !== "INITIAL" && !updateHtml.value.trim()) hints.push("请填写 Update");
    if (hpStatusPrefix.value === "MITIGATED" && !(d.resolution || "").trim()) hints.push("请填写 Resolution");
    const endDt = (d.end_datetime || "").replace(/Beijing Time\(GMT\+8\)\s*:\s*/i, "").trim();
    if (hpStatusPrefix.value === "MITIGATED" && !endDt) hints.push("请完整填写 End Date & Time（在 Beijing Time(GMT+8) : 后面填写日期时间）");
    else if (hpStatusPrefix.value === "MITIGATED" && endDt && !/^(0[1-9]|1[0-2])\/(0[1-9]|[12]\d|3[01])\/\d{4}\s+([01]\d|2[0-3]):[0-5]\d$/.test(endDt)) hints.push("End Date & Time 格式不正确，应为 MM/DD/YYYY HH:MM");
  } else if (emailType.value === "account") {
    const accts = formData.value.accounts;
    if (!accts || !accts.length) hints.push("请至少添加一条账号信息");
    else if (!accts.some((a) => a.account && a.password && a.account_type)) hints.push("请完整填写至少一条账号（账号、密码、类型）");
  } else {
    const subs = formData.value.subscriptions;
    if (!subs || !subs.length) hints.push("请至少添加一条订阅信息");
    else if (!subs.some((s) => s.subscription_id || s.subscription_name)) hints.push("请填写至少一条订阅（ID 或名称）");
  }
  return hints;
});

const canSend = computed(() => sendHints.value.length === 0);

// ── Lifecycle ───────────────────────

function autoSelectDefaultSignature() {
  if (selectedSignatureId.value) return; // already selected
  const def = signatures.value.find((s) => s.is_default);
  if (def) selectedSignatureId.value = def.id;
}

function onBeforeUnload(e) {
  if (isDirty.value) {
    e.preventDefault();
    e.returnValue = "";
  }
}

onMounted(async () => {
  try {
    const [tRes, sRes] = await Promise.all([getTemplates(), getSignatures()]);
    templates.value = tRes.data;
    signatures.value = sRes.data;
    autoSelectDefaultSignature();
  } catch { /* ignore */ }
  loadAllFieldHistories();
  loadDraft();
  window.addEventListener("beforeunload", onBeforeUnload);
  document.addEventListener("click", onDocumentClick);
  // Allow dirty tracking now that initial setup is done
  nextTick(() => { suppressDirty.value = false; });
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", onBeforeUnload);
  document.removeEventListener("click", onDocumentClick);
});

onActivated(async () => {
  try {
    const [tRes, sRes] = await Promise.all([getTemplates(), getSignatures()]);
    templates.value = tRes.data;
    signatures.value = sRes.data;
    autoSelectDefaultSignature();
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

function doSwitchType(type) {
  suppressDirty.value = true;
  emailType.value = type;
  selectedTemplateId.value = null;
  selectedSignatureId.value = null;
  subject.value = "";
  recipientTags.value = [];
  recipientInput.value = "";
  ccTags.value = [];
  ccInput.value = "";
  body.value = "";
  bodySource.value = "";
  userEditedBody.value = false;
  formData.value = {};
  attachments.value = [];
  incidentBridgeHtml.value = "";
  updateHtml.value = "";
  lookupTicketId.value = "";
  lookupResult.value = null;
  loadDraft();
  autoSelectDefaultSignature();
  suppressDirty.value = false;
}

function switchType(type) {
  if (emailType.value === type) return;
  if (!isDirty.value) {
    doSwitchType(type);
    return;
  }
  dialog.warning({
    title: "未保存的更改",
    content: "当前草稿尚未暂存，切换类型后修改将丢失。是否暂存后再切换？",
    positiveText: "暂存并切换",
    negativeText: "不保存",
    onPositiveClick: () => {
      saveDraft();
      doSwitchType(type);
    },
    onNegativeClick: () => {
      suppressDirty.value = true;
      clearDraft();
      isDirty.value = false;
      // Discard all fields and switch cleanly
      emailType.value = type;
      selectedTemplateId.value = null;
      selectedSignatureId.value = null;
      subject.value = "";
      recipientTags.value = [];
      recipientInput.value = "";
      ccTags.value = [];
      ccInput.value = "";
      body.value = "";
      bodySource.value = "";
      userEditedBody.value = false;
      formData.value = {};
      attachments.value = [];
      incidentBridgeHtml.value = "";
      updateHtml.value = "";
      lookupTicketId.value = "";
      lookupResult.value = null;
      autoSelectDefaultSignature();
      suppressDirty.value = false;
    },
    onClose: () => {
      // Cancel — stay on current type
    },
  });
}

function handleClear() {
  suppressDirty.value = true;
  selectedTemplateId.value = null;
  selectedSignatureId.value = null;
  subject.value = "";
  recipientTags.value = [];
  recipientInput.value = "";
  ccTags.value = [];
  ccInput.value = "";
  body.value = "";
  bodySource.value = "";
  userEditedBody.value = false;
  formData.value = {};
  attachments.value = [];
  incidentBridgeHtml.value = "";
  updateHtml.value = "";
  lookupTicketId.value = "";
  lookupResult.value = null;
  clearDraft();
  isDirty.value = false;
  suppressDirty.value = false;
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
    if (emailType.value === "high_priority") {
      // Determine status_prefix from template name
      const name = (t.name || "").toUpperCase();
      let prefix = "INITIAL";
      if (name.includes("UPDATED")) prefix = "UPDATED";
      else if (name.includes("MITIGATED")) prefix = "MITIGATED";
      // Reset HP-specific fields on template switch
      incidentBridgeHtml.value = "";
      updateHtml.value = "";
      lookupTicketId.value = "";
      lookupResult.value = null;
      // Sync status_prefix to formData so HighPriorityForm picks it up
      formData.value = {
        ...formData.value,
        status_prefix: prefix,
        current_status: prefix === "INITIAL" ? "Initial" :
                        prefix === "UPDATED" ? "Investigating" : "Mitigated",
        date: todayStr(),
      };
      body.value = renderHighPriorityBody(t.content);
    } else {
      body.value = renderTemplateContent(t.content);
    }
    selectedSignatureId.value = null;
    autoSelectDefaultSignature();
  }
}

function onBodyEdited() {
  userEditedBody.value = true;
}

// Re-render body when formData or incidentBridgeHtml changes
watch([formData, emailType, incidentBridgeHtml, updateHtml], () => {
  if (emailType.value === "high_priority") {
    if (selectedTemplateId.value) {
      const t = templates.value.find((tp) => tp.id === selectedTemplateId.value);
      if (t) { bodySource.value = t.content; body.value = renderHighPriorityBody(t.content); }
    }
    return;
  }
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

const DRAFT_KEY_PREFIX = "mailswift_saved_draft_";

// ── Field history ────────────────────

const FIELD_HISTORY_KEYS = {
  subject: "mailswift_history_subject",
  recipient: "mailswift_history_recipient",
  cc: "mailswift_history_cc",
  account_name: "mailswift_history_account_name",
  account_type: "mailswift_history_account_type",
  subscription_id: "mailswift_history_subscription_id",
  subscription_name: "mailswift_history_subscription_name",
};

function loadFieldHistory(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function addToFieldHistory(key, value) {
  if (!value || !value.trim()) return;
  const history = loadFieldHistory(key);
  const v = value.trim();
  const filtered = history.filter((h) => h !== v);
  filtered.unshift(v);
  if (filtered.length > 50) filtered.pop();
  try {
    localStorage.setItem(key, JSON.stringify(filtered));
  } catch { /* ignore */ }
}

function draftKey() {
  return DRAFT_KEY_PREFIX + emailType.value;
}

function saveDraft() {
  suppressDirty.value = true;
  const draft = {
    emailType: emailType.value,
    selectedTemplateId: selectedTemplateId.value,
    selectedSignatureId: selectedSignatureId.value,
    subject: subject.value,
    recipient: recipientTags.value.join(","),
    cc: ccTags.value.join(","),
    body: body.value,
    formData: formData.value,
    incidentBridgeHtml: incidentBridgeHtml.value,
    updateHtml: updateHtml.value,
  };
  try {
    localStorage.setItem(draftKey(), JSON.stringify(draft));
  } catch { /* quota exceeded, ignore */ }
  isDirty.value = false;
  suppressDirty.value = false;
}

function handleSaveDraft() {
  saveDraft();
  message.success("草稿已暂存");
}

function loadDraft() {
  try {
    const raw = localStorage.getItem(draftKey());
    if (!raw) return;
    const draft = JSON.parse(raw);
    suppressDirty.value = true;
    selectedTemplateId.value = draft.selectedTemplateId || null;
    selectedSignatureId.value = draft.selectedSignatureId || null;
    subject.value = draft.subject || "";
    const r = draft.recipient || "";
    recipientTags.value = typeof r === "string" ? r.split(",").filter(Boolean) : (Array.isArray(r) ? r : []);
    const c = draft.cc || "";
    ccTags.value = typeof c === "string" ? c.split(",").filter(Boolean) : (Array.isArray(c) ? c : []);
    body.value = draft.body || "";
    formData.value = draft.formData || {};
    incidentBridgeHtml.value = draft.incidentBridgeHtml || "";
    updateHtml.value = draft.updateHtml || "";
    isDirty.value = false;
    suppressDirty.value = false;
  } catch { /* ignore */ }
}

// Track unsaved changes (dirty flag only, no auto-save)
function hasFormContent() {
  if (subject.value.trim()) return true;
  if (recipientTags.value.length) return true;
  if (ccTags.value.length) return true;
  if (body.value.trim()) return true;
  const accounts = formData.value?.accounts || [];
  if (accounts.some((a) => a.account || a.password || a.account_type)) return true;
  const subs = formData.value?.subscriptions || [];
  if (subs.some((s) => s.subscription_id || s.subscription_name)) return true;
  if (incidentBridgeHtml.value.trim()) return true;
  if (updateHtml.value.trim()) return true;
  return false;
}

watch([emailType, selectedTemplateId, selectedSignatureId, subject, recipientTags, recipientInput, ccTags, ccInput, body, formData, incidentBridgeHtml, updateHtml], () => {
  if (suppressDirty.value) return;
  if (hasFormContent()) isDirty.value = true;
}, { deep: true, flush: "sync" });

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
    // For high_priority, auto-construct subject from form fields
    let finalSubject = subject.value;
    if (emailType.value === "high_priority") {
      const d = formData.value || {};
      finalSubject = `${d.status_prefix || "INITIAL"} ${d.severity || "Sev?"}-Incident [${d.ticket_id || "xxxxxx"}] - ${d.category || "Network"} - ${d.title || ""}`;
    }

    const payload = {
      email_type: emailType.value,
      recipient: recipientTags.value.join(","),
      cc: ccTags.value.join(","),
      subject: finalSubject,
      body: body.value,
      template_id: selectedTemplateId.value || null,
      signature_id: selectedSignatureId.value || null,
    };
    if (emailType.value === "high_priority") {
      payload.accounts = [];
      payload.subscriptions = [];
      // Include ticket_id and form_data for incident_store upsert
      const d = formData.value || {};
      payload.ticket_id = d.ticket_id || "";
      payload.form_data = {
        ...d,
        incidentBridgeHtml: incidentBridgeHtml.value,
        updateHtml: updateHtml.value,
        recipient: recipientTags.value.join(","),
        cc: ccTags.value.join(","),
      };
    } else if (emailType.value === "account") {
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

    // Record field histories
    addToFieldHistory(FIELD_HISTORY_KEYS.subject, subject.value);
    recipientTags.value.forEach((t) => addToFieldHistory(FIELD_HISTORY_KEYS.recipient, t));
    ccTags.value.forEach((t) => addToFieldHistory(FIELD_HISTORY_KEYS.cc, t));
    if (emailType.value === "account") {
      (formData.value.accounts || []).forEach((a) => {
        if (a.account) addToFieldHistory(FIELD_HISTORY_KEYS.account_name, a.account);
        if (a.account_type) addToFieldHistory(FIELD_HISTORY_KEYS.account_type, a.account_type);
      });
    } else {
      (formData.value.subscriptions || []).forEach((s) => {
        if (s.subscription_id) addToFieldHistory(FIELD_HISTORY_KEYS.subscription_id, s.subscription_id);
        if (s.subscription_name) addToFieldHistory(FIELD_HISTORY_KEYS.subscription_name, s.subscription_name);
      });
    }
    // Refresh in-memory histories so dropdown picks up new entries
    loadAllFieldHistories();

    handleClear();
  } catch (err) {
    message.error(err.response?.data?.detail || "发送失败");
  } finally {
    sending.value = false;
  }
}

function formatSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function clearDraft() {
  try {
    localStorage.removeItem(draftKey());
  } catch { /* ignore */ }
}

// ── Route leave guard ────────────────

onBeforeRouteLeave((to, from, next) => {
  if (!isDirty.value) {
    next();
    return;
  }
  dialog.warning({
    title: "未保存的更改",
    content: "当前草稿尚未暂存，离开后修改将丢失。是否暂存后再离开？",
    positiveText: "暂存并离开",
    negativeText: "不保存",
    onPositiveClick: () => {
      saveDraft();
      next();
    },
    onNegativeClick: () => {
      clearDraft();
      isDirty.value = false;
      next();
    },
    onClose: () => {
      // User cancelled the dialog — stay on current page
    },
  });
});
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

.title-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.4px;
  margin-bottom: 0;
}

.type-switcher {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
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

.field-wrapper {
  position: relative;
}

.history-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 1000;
  margin-top: 4px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.1);
  max-height: 200px;
  overflow-y: auto;
}

.history-dropdown-item {
  padding: 8px 14px;
  cursor: pointer;
  font-size: 14px;
  color: #1d1d1f;
  transition: background 0.1s;
}

.history-dropdown-item:hover {
  background: #f0f7ff;
}

.history-dropdown-item:first-child {
  border-radius: 10px 10px 0 0;
}

.history-dropdown-item:last-child {
  border-radius: 0 0 10px 10px;
}

.history-dropdown-empty {
  padding: 12px 14px;
  font-size: 13px;
  color: #999;
  text-align: center;
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

.pill-input-shell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  min-height: 40px;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  background: #fff;
  transition: border-color 0.2s;
}

.pill-input-shell:focus-within {
  border-color: #0071e3;
}

.pill-input-shell.pill-input-error {
  border-color: #e53935;
}

.pill-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 8px;
  background: #e6f4ea;
  color: #1e8e3e;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: nowrap;
}

.pill-tag.editing {
  background: #e8f0fe;
  color: #1a73e8;
}

.pill-tag-x {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 14px;
  padding: 0;
  line-height: 1;
  opacity: 0.5;
}

.pill-tag-x:hover {
  opacity: 1;
}

.pill-edit-input {
  width: 180px;
  padding: 0 4px;
  font-size: 13px;
  border: none;
  outline: none;
  background: transparent;
  color: #1a73e8;
}

.pill-auto {
  flex: 1;
  min-width: 120px;
}

.pill-auto :deep(.n-auto-complete) {
  border: none !important;
  box-shadow: none !important;
}

.pill-auto :deep(.n-input) {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
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

.preview-meta {
  background: #f8f9fa;
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 16px;
}

.preview-meta-row {
  display: flex;
  gap: 8px;
  font-size: 14px;
  line-height: 1.8;
}

.preview-meta-label {
  color: #86868b;
  flex-shrink: 0;
  min-width: 48px;
}

.preview-meta-val {
  color: #1d1d1f;
}

.preview-meta-subject {
  font-weight: 600;
}

.preview-pill {
  display: inline-block;
  padding: 1px 10px;
  margin: 2px 4px 2px 0;
  background: #e6f4ea;
  color: #1e8e3e;
  border-radius: 12px;
  font-size: 13px;
}

.send-hint-line {
  font-size: 13px;
  line-height: 1.8;
  color: #fff;
}

.preview-body {
  font-size: 16px;
  line-height: 1.7;
  color: #1d1d1f;
  word-break: break-word;
  overflow-x: auto;
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

.preview-attachments {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e0e0e0;
}

.preview-attach-title {
  font-size: 13px;
  font-weight: 600;
  color: #86868b;
  margin-bottom: 8px;
}

.preview-attach-item {
  font-size: 14px;
  color: #1d1d1f;
  padding: 4px 0;
}

.preview-attach-size {
  color: #86868b;
  font-size: 12px;
  margin-left: 8px;
}

.preview-btn-row {
  margin-bottom: 24px;
}

.lookup-section {
  margin-bottom: 24px;
}

.lookup-row {
  display: flex;
  gap: 8px;
}

.lookup-hint {
  margin-top: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
}

.lookup-hint-success {
  background: #f0f7ff;
  color: #1a73e8;
  border: 1px solid #c8ddf8;
}

.lookup-hint-warn {
  background: #fff8e6;
  color: #b06000;
  border: 1px solid #f5d78e;
}
</style>
