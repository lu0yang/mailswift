<template>
  <div class="settings">
    <n-button text size="small" @click="$router.push('/')" class="back-btn">
      <template #icon><n-icon><arrow-back-outline /></n-icon></template>
      <span style="font-size:14px">返回</span>
    </n-button>

    <div class="page-title">设置</div>

    <n-tabs type="line" animated>
      <!-- Account Tab -->
      <n-tab-pane name="account" tab="账户">
        <div class="settings-card">
          <!-- State B: already configured -->
          <template v-if="isConfigured">
            <div class="configured-banner">
              <span class="configured-dot"></span>
              已登录 {{ emailAddress }}
            </div>
            <div v-if="!showPasswordUpdate" class="update-link" @click="showPasswordUpdate = true">
              更新密码
            </div>
            <template v-if="showPasswordUpdate">
              <div class="form-field">
                <label class="field-label">新密码</label>
                <n-input v-model:value="password" type="password" show-password-on="click" placeholder="输入新密码" size="large" />
              </div>
              <div class="btn-row">
                <n-button size="large" :loading="testing" @click="handleTest">
                  测试新密码
                </n-button>
                <n-button type="primary" size="large" :loading="saving" :disabled="!connectionTested" @click="handleSave">
                  保存新密码
                </n-button>
              </div>
              <div v-if="!connectionTested && password" class="test-hint">
                请先通过连接测试，成功后方可保存
              </div>
            </template>
          </template>

          <!-- State A: not yet configured -->
          <template v-else>
            <div class="form-field">
              <label class="field-label">邮箱地址</label>
              <n-input v-model:value="emailAddress" placeholder="yourname@company.com" size="large" clearable />
            </div>
            <div class="form-field">
              <label class="field-label">密码</label>
              <n-input v-model:value="password" type="password" show-password-on="click" placeholder="输入密码" size="large" />
            </div>
            <div class="btn-row">
              <n-button size="large" :loading="testing" @click="handleTest">
                测试连接
              </n-button>
              <n-button type="primary" size="large" :loading="saving" :disabled="!connectionTested" @click="handleSave">
                保存并登录
              </n-button>
            </div>
            <div v-if="!connectionTested && (emailAddress || password)" class="test-hint">
              请先通过连接测试，成功后方可保存凭据
            </div>
          </template>
        </div>
      </n-tab-pane>

      <!-- Templates Tab -->
      <n-tab-pane name="templates" tab="邮件模板">
        <div class="settings-card">
          <div class="tab-header">
            <div class="filter-tabs">
              <div
                v-for="tab in templateFilterTabs"
                :key="tab.value"
                class="filter-tab"
                :class="{ active: templateFilter === tab.value }"
                @click="templateFilter = tab.value"
              >
                {{ tab.label }}
              </div>
            </div>
            <n-button type="primary" size="small" @click="openTemplateModal(null)">
              <template #icon><n-icon><add-outline /></n-icon></template>
              新建模板
            </n-button>
          </div>
          <div v-if="filteredTemplates.length === 0" class="empty">暂无模板</div>
          <div v-for="t in filteredTemplates" :key="t.id" class="list-card">
            <div class="list-card-main">
              <div class="list-card-left">
                <span class="type-badge" :class="t.type">{{ t.type === 'account' ? '账号' : '订阅' }}</span>
                <span class="list-card-name">{{ t.name }}</span>
              </div>
              <div class="list-card-right">
                <n-button text size="tiny" @click="openTemplateModal(t)">编辑</n-button>
                <n-button text size="tiny" type="error" @click="handleDeleteTemplate(t.id)">删除</n-button>
              </div>
            </div>
            <div class="list-card-preview">{{ previewText(t) }}</div>
          </div>
        </div>
      </n-tab-pane>

      <!-- Signatures Tab -->
      <n-tab-pane name="signatures" tab="签名管理">
        <div class="settings-card">
          <div class="tab-header">
            <span></span>
            <n-button type="primary" size="small" @click="openSignatureModal(null)">
              <template #icon><n-icon><add-outline /></n-icon></template>
              新建签名
            </n-button>
          </div>
          <div v-if="signatures.length === 0" class="empty">暂无签名</div>
          <div v-for="s in signatures" :key="s.id" class="list-card">
            <div class="list-card-main">
              <div class="list-card-left">
                <span class="list-card-name">{{ s.name }}</span>
                <span v-if="s.is_default" class="default-badge">默认</span>
              </div>
              <div class="list-card-right">
                <n-button text size="tiny" @click="openSignatureModal(s)">编辑</n-button>
                <n-button text size="tiny" type="error" @click="handleDeleteSignature(s.id)">删除</n-button>
              </div>
            </div>
            <div class="list-card-preview">{{ s.content.slice(0, 100) }}{{ s.content.length > 100 ? '…' : '' }}</div>
          </div>
        </div>
      </n-tab-pane>
    </n-tabs>

    <div class="reset-area">
      <n-button text type="error" size="small" :loading="resetting" @click="handleReset">
        初始化工具
      </n-button>
      <span class="reset-hint">恢复至默认设置，所有自定义模板、签名、登录凭据将被清除</span>
    </div>

    <!-- Template Edit Modal -->
    <n-modal v-model:show="templateModalVisible" preset="card" title="编辑模板" style="max-width:800px">
      <div class="form-row-2col">
        <div class="form-col">
          <label class="field-label">模板名称</label>
          <n-input v-model:value="templateForm.name" placeholder="例如：正式账号通知" size="large" />
        </div>
        <div class="form-col">
          <label class="field-label">类型</label>
          <n-select
            v-model:value="templateForm.type"
            :options="[{ label: '账号创建/重置', value: 'account' }, { label: '订阅创建', value: 'subscription' }]"
            size="large"
          />
        </div>
      </div>

      <div class="modal-section">
        <label class="section-label">
          <span class="section-num">1</span> 开头文字
          <span class="section-hint">— 所有账号前，出现一次</span>
        </label>
        <RichTextEditor v-model="templateForm.header" :variables="headerVariables" />
      </div>

      <div class="modal-section">
        <label class="section-label">
          <span class="section-num">2</span> 每条账号格式
          <span class="section-hint">— 有几条账号就重复几次</span>
        </label>
        <RichTextEditor v-model="templateForm.item" :variables="itemVariables" />
      </div>

      <div class="modal-section">
        <label class="section-label">
          <span class="section-num">3</span> 结尾文字
          <span class="section-hint">— 所有账号后，出现一次</span>
        </label>
        <RichTextEditor v-model="templateForm.footer" :variables="[]" />
      </div>

      <details class="preview-details">
        <summary class="preview-summary">预览效果</summary>
        <div class="preview-box" v-html="templatePreview"></div>
      </details>

      <template #footer>
        <div class="modal-footer">
          <n-button @click="templateModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="templateSaving" @click="handleSaveTemplate">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- Signature Edit Modal -->
    <n-modal v-model:show="sigModalVisible" preset="card" title="签名" style="max-width:720px">
      <div class="modal-field">
        <label class="field-label">签名名称</label>
        <n-input v-model:value="sigForm.name" placeholder="例如：工作签名" size="large" />
      </div>
      <div class="modal-field">
        <div class="sig-mode-bar">
          <span class="field-label" style="margin-bottom:0">签名内容</span>
          <div class="sig-mode-tabs">
            <button
              class="sig-mode-btn"
              :class="{ active: sigMode === 'richtext' }"
              @click="sigMode = 'richtext'"
            >富文本编辑</button>
            <button
              class="sig-mode-btn"
              :class="{ active: sigMode === 'html' }"
              @click="sigMode = 'html'"
            >从 Outlook 粘贴</button>
          </div>
        </div>
        <RichTextEditor v-if="sigMode === 'richtext'" v-model="sigForm.content" />
        <div v-else class="html-paste-wrap">
          <div
            class="paste-zone"
            :class="{ 'has-content': sigForm.content }"
            contenteditable
            @paste="onSigPaste"
            tabindex="0"
          >
            <div v-if="!sigForm.content && !sigImageConverting" class="paste-placeholder">
              从 Outlook 复制签名后，在此处 Ctrl+V 粘贴
            </div>
            <div v-else-if="sigImageConverting" class="paste-converting">正在处理图片…</div>
            <div v-else class="paste-done">已捕获签名</div>
          </div>
          <div class="paste-hint">点击上方区域后按 Ctrl+V 粘贴，工具自动提取 HTML 格式</div>
          <details class="preview-details" style="margin-top:12px">
            <summary class="preview-summary">预览效果</summary>
            <div class="preview-box" v-html="sigForm.content"></div>
          </details>
        </div>
      </div>
      <div class="modal-field">
        <n-checkbox v-model:checked="sigForm.is_default">设为默认签名</n-checkbox>
      </div>
      <template #footer>
        <div class="modal-footer">
          <n-button @click="sigModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="sigSaving" @click="handleSaveSignature">保存</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject } from "vue";
import {
  NInput, NSelect, NButton, NIcon, NTabs, NTabPane,
  NModal, NCheckbox, useMessage, useDialog,
} from "naive-ui";
import { ArrowBackOutline, AddOutline } from "@vicons/ionicons5";
import RichTextEditor from "@/components/RichTextEditor.vue";
import {
  getSettings, updateSettings, testConnection,
  getTemplates, createTemplate, updateTemplate, deleteTemplate,
  getSignatures, createSignature, updateSignature, deleteSignature,
  resetApp, encodeImage,
} from "@/api";

const message = useMessage();
const dialog = useDialog();

// ── Account ──────────────────────────

const refreshAccount = inject("refreshAccount", () => {});

const emailAddress = ref("");
const password = ref("");
const saving = ref(false);
const testing = ref(false);
const connectionTested = ref(false);
const isConfigured = ref(false);
const showPasswordUpdate = ref(false);

onMounted(async () => {
  try {
    const { data } = await getSettings();
    emailAddress.value = data.email_address || "";
    if (data.password_masked) {
      // Verify saved credentials actually work — same check as the header
      try {
        await testConnection();
        isConfigured.value = true;
        connectionTested.value = true;
      } catch {
        // Credentials expired — show login form
        isConfigured.value = false;
      }
    }
  } catch { /* not yet configured */ }
  await loadTemplates();
  await loadSignatures();
});

// Reset test state when password changes
watch(password, () => {
  connectionTested.value = false;
});

async function handleSave() {
  if (!connectionTested.value) {
    message.warning("请先通过连接测试再保存");
    return;
  }
  saving.value = true;
  try {
    await updateSettings({
      email_address: emailAddress.value,
      password: password.value,
    });
    message.success(isConfigured.value ? "密码已更新" : "已保存");
    isConfigured.value = true;
    showPasswordUpdate.value = false;
    password.value = "";
    connectionTested.value = false;
    refreshAccount();
  } catch (err) {
    message.error(err.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function handleTest() {
  if (!emailAddress.value || !password.value) {
    message.warning("请先填写邮箱地址和密码");
    return;
  }
  testing.value = true;
  try {
    await testConnection({
      email_address: emailAddress.value,
      password: password.value,
    });
    connectionTested.value = true;
    message.success("连接测试成功");
  } catch (err) {
    connectionTested.value = false;
    message.error("连接失败");
  } finally {
    testing.value = false;
  }
}

// ── Reset ────────────────────────────

const resetting = ref(false);

async function handleReset() {
  dialog.warning({
    title: "确认初始化",
    content: "将清除所有自定义模板、签名和登录凭据，恢复至默认状态。此操作不可撤销，确定继续？",
    positiveText: "确定",
    negativeText: "取消",
    onPositiveClick: async () => {
      resetting.value = true;
      try {
        await resetApp();
        // Clear local state
        emailAddress.value = "";
        password.value = "";
        isConfigured.value = false;
        connectionTested.value = false;
        showPasswordUpdate.value = false;
        templates.value = [];
        signatures.value = [];
        // Reload templates (defaults) and refresh header
        await loadTemplates();
        await loadSignatures();
        refreshAccount();
        message.success("已恢复至默认状态");
      } catch (err) {
        message.error(err.response?.data?.detail || "初始化失败");
      } finally {
        resetting.value = false;
      }
    },
  });
}

// ── Templates ─────────────────────────

const templates = ref([]);
const templateFilter = ref("");
const templateFilterTabs = [
  { label: "全部", value: "" },
  { label: "账号", value: "account" },
  { label: "订阅", value: "subscription" },
];

const filteredTemplates = computed(() => {
  if (!templateFilter.value) return templates.value;
  return templates.value.filter((t) => t.type === templateFilter.value);
});

const templateModalVisible = ref(false);
const templateSaving = ref(false);
const editingTemplateId = ref(null);
const templateForm = ref({ name: "", type: "account", header: "", item: "", footer: "" });

const accountVars = [
  { label: "account/accounts", marker: "{account_plural}" },
  { label: "用户名", marker: "{username}" },
  { label: "密码", marker: "{password}" },
  { label: "账户类型", marker: "{account_type}" },
];

const subscriptionVars = [
  { label: "subscription/subscriptions", marker: "{subscription_plural}" },
  { label: "Subscription Id", marker: "{subscription_id}" },
  { label: "Subscription Name", marker: "{subscription_name}" },
];

const headerVariables = computed(() => {
  const haveHas = { label: "have/has", marker: "{have_has}" };
  if (templateForm.value.type === "account") return [accountVars[0], haveHas];
  return [subscriptionVars[0], haveHas];
});

const itemVariables = computed(() => {
  if (templateForm.value.type === "account") return accountVars.slice(1);
  return subscriptionVars.slice(1);
});

const templatePreview = computed(() => {
  const t = templateForm.value;
  if (!t.header && !t.item && !t.footer) return "<p style='color:#86868b'>填写内容后预览</p>";

  const sampleData = t.type === "account"
    ? [
        { username: "zhangsan", password: "Abc12345", account_type: "正式账号" },
        { username: "lisi", password: "Xyz67890", account_type: "测试账号" },
      ]
    : [
        { subscription_id: "SUB-001", subscription_name: "基础版" },
        { subscription_id: "SUB-002", subscription_name: "高级版" },
      ];

  const pluralMap = {
    account_plural: sampleData.length === 1 ? "account" : "accounts",
    subscription_plural: sampleData.length === 1 ? "subscription" : "subscriptions",
  };

  let header = t.header;
  for (const [k, v] of Object.entries(pluralMap)) {
    header = header.replaceAll(`{${k}}`, v);
  }

  const items = sampleData.map((d) => {
    let part = t.item;
    for (const [k, v] of Object.entries(d)) {
      part = part.replaceAll(`{${k}}`, v);
    }
    return part;
  });

  return header + items.join("\n") + t.footer;
});

function parseTemplateContent(content) {
  if (!content) return { header: "", item: "", footer: "" };
  try {
    const parsed = JSON.parse(content);
    if (parsed && typeof parsed === "object" && "item" in parsed) {
      return {
        header: parsed.header || "",
        item: parsed.item || "",
        footer: parsed.footer || "",
      };
    }
  } catch { /* legacy format */ }
  return { header: "", item: content, footer: "" };
}

function serialiseTemplateContent(header, item, footer) {
  return JSON.stringify({ header: header || "", item: item || "", footer: footer || "" });
}

function previewText(tpl) {
  const parsed = parseTemplateContent(tpl.content);
  const text = [parsed.header, parsed.item, parsed.footer].filter(Boolean).join(" ");
  const stripped = text.replace(/<[^>]+>/g, "").trim();
  return stripped.slice(0, 80) + (stripped.length > 80 ? "…" : "");
}

async function loadTemplates() {
  try {
    const { data } = await getTemplates();
    templates.value = data;
  } catch { /* ignore */ }
}

function openTemplateModal(template) {
  if (template) {
    editingTemplateId.value = template.id;
    const parsed = parseTemplateContent(template.content);
    templateForm.value = {
      name: template.name,
      type: template.type,
      header: parsed.header,
      item: parsed.item,
      footer: parsed.footer,
    };
  } else {
    editingTemplateId.value = null;
    templateForm.value = { name: "", type: "account", header: "", item: "", footer: "" };
  }
  templateModalVisible.value = true;
}

async function handleSaveTemplate() {
  if (!templateForm.value.name) {
    message.warning("请输入模板名称");
    return;
  }
  if (!templateForm.value.item) {
    message.warning("请填写至少每条账号格式");
    return;
  }
  templateSaving.value = true;
  try {
    const payload = {
      name: templateForm.value.name,
      type: templateForm.value.type,
      content: serialiseTemplateContent(
        templateForm.value.header,
        templateForm.value.item,
        templateForm.value.footer
      ),
    };
    if (editingTemplateId.value) {
      await updateTemplate(editingTemplateId.value, payload);
    } else {
      await createTemplate(payload);
    }
    message.success("模板已保存");
    templateModalVisible.value = false;
    await loadTemplates();
  } catch (err) {
    message.error(err.response?.data?.detail || "保存失败");
  } finally {
    templateSaving.value = false;
  }
}

async function handleDeleteTemplate(id) {
  dialog.warning({
    title: "确认删除",
    content: "确定要删除这个模板吗？此操作不可撤销。",
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await deleteTemplate(id);
        message.success("模板已删除");
        await loadTemplates();
      } catch {
        message.error("删除失败");
      }
    },
  });
}

// ── Signatures ────────────────────────

const signatures = ref([]);
const sigModalVisible = ref(false);
const sigSaving = ref(false);
const editingSigId = ref(null);
const sigMode = ref("richtext");
const sigImageConverting = ref(false);
const sigForm = ref({ name: "", content: "", is_default: false });

async function loadSignatures() {
  try {
    const { data } = await getSignatures();
    signatures.value = data;
  } catch { /* ignore */ }
}

async function onSigPaste(e) {
  e.preventDefault();
  const html = e.clipboardData?.getData("text/html");
  if (!html) return;

  e.target.innerHTML = "";

  // Parse HTML and find images that need base64 conversion
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const imgs = doc.querySelectorAll("img");
  const fileImgs = [];

  imgs.forEach((img) => {
    const src = img.getAttribute("src");
    if (src && (src.startsWith("file://") || /^[A-Z]:[/\\]/i.test(src))) {
      fileImgs.push({ img, src });
    }
  });

  if (fileImgs.length > 0) {
    sigImageConverting.value = true;

    for (const { img, src } of fileImgs) {
      try {
        const { data } = await encodeImage(src);
        img.setAttribute("src", data.data_uri);
      } catch {
        // Keep original src if conversion fails
      }
    }

    sigImageConverting.value = false;
  }

  sigForm.value.content = doc.body.innerHTML;
}

function openSignatureModal(sig) {
  if (sig) {
    editingSigId.value = sig.id;
    sigForm.value = { name: sig.name, content: sig.content, is_default: sig.is_default };
    sigMode.value = /<table|<img|<td|<tr|style="/i.test(sig.content) ? "html" : "richtext";
  } else {
    editingSigId.value = null;
    sigForm.value = { name: "", content: "", is_default: false };
    sigMode.value = "richtext";
  }
  sigModalVisible.value = true;
}

async function handleSaveSignature() {
  if (!sigForm.value.name) {
    message.warning("请输入签名名称");
    return;
  }
  sigSaving.value = true;
  try {
    if (editingSigId.value) {
      await updateSignature(editingSigId.value, sigForm.value);
    } else {
      await createSignature(sigForm.value);
    }
    message.success("签名已保存");
    sigModalVisible.value = false;
    await loadSignatures();
  } catch (err) {
    message.error(err.response?.data?.detail || "保存失败");
  } finally {
    sigSaving.value = false;
  }
}

async function handleDeleteSignature(id) {
  dialog.warning({
    title: "确认删除",
    content: "确定要删除这个签名吗？此操作不可撤销。",
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await deleteSignature(id);
        message.success("签名已删除");
        await loadSignatures();
      } catch {
        message.error("删除失败");
      }
    },
  });
}
</script>

<style scoped>
.settings {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.back-btn { margin-bottom: 12px; }

.page-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.4px;
  margin-bottom: 20px;
}

.settings-card {
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.form-field { margin-bottom: 18px; }

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin-bottom: 6px;
}

.field-hint {
  font-size: 12px;
  color: #86868b;
  font-weight: 400;
}

.field-hint code {
  background: #f0f7ff;
  color: #0071e3;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 11px;
}

.btn-row {
  display: flex;
  gap: 10px;
}

.configured-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #e8f8ed;
  border-radius: 10px;
  font-size: 14px;
  color: #1d1d1f;
  margin-bottom: 20px;
}

.configured-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #34c759;
  flex-shrink: 0;
}

.update-link {
  font-size: 14px;
  color: #0071e3;
  cursor: pointer;
  font-weight: 500;
}

.update-link:hover {
  color: #0077ed;
  text-decoration: underline;
}

.reset-area {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 28px;
  padding: 12px 0;
}

.reset-hint {
  font-size: 12px;
  color: #86868b;
}

.test-hint {
  margin-top: 12px;
  font-size: 13px;
  color: #f59e0b;
  text-align: center;
}

/* ── Template / Signature lists ─── */

.tab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.filter-tabs {
  display: flex;
  gap: 8px;
}

.filter-tab {
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  background: #f5f5f7;
  color: #6e6e73;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-tab:hover { color: #1d1d1f; }

.filter-tab.active {
  background: #1d1d1f;
  color: #fff;
}

.list-card {
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 8px;
  transition: box-shadow 0.2s;
}

.list-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.list-card-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.list-card-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.list-card-name {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.type-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 5px;
}

.type-badge.account { background: #f0f7ff; color: #0071e3; }
.type-badge.subscription { background: #f3e8ff; color: #7c3aed; }

.default-badge {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 5px;
  background: #e8f8ed;
  color: #34c759;
}

.list-card-right {
  display: flex;
  gap: 4px;
}

.list-card-preview {
  font-size: 12px;
  color: #86868b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty {
  text-align: center;
  padding: 40px 0;
  color: #86868b;
  font-size: 14px;
}

/* ── Signature mode tabs ───────────── */

.sig-mode-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.sig-mode-tabs {
  display: flex;
  gap: 1px;
  background: #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.sig-mode-btn {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  border: none;
  background: #fff;
  color: #6e6e73;
  cursor: pointer;
  transition: all 0.15s;
}

.sig-mode-btn:hover {
  color: #1d1d1f;
}

.sig-mode-btn.active {
  background: #0071e3;
  color: #fff;
}

.html-paste-wrap {
  margin-top: 6px;
}

.paste-zone {
  border: 2px dashed #d0d0d0;
  border-radius: 10px;
  min-height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: text;
  transition: border-color 0.2s, background 0.2s;
  outline: none;
  padding: 16px;
}

.paste-zone:focus {
  border-color: #0071e3;
  background: #f0f7ff;
}

.paste-zone.has-content {
  border-style: solid;
  border-color: #34c759;
  background: #e8f8ed;
}

.paste-placeholder {
  color: #86868b;
  font-size: 14px;
  text-align: center;
  pointer-events: none;
}

.paste-converting {
  color: #f59e0b;
  font-size: 14px;
  font-weight: 500;
}

.paste-done {
  color: #34c759;
  font-size: 14px;
  font-weight: 500;
}

.paste-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #86868b;
}

/* ── Modal ────────────────────────── */

.form-row-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.modal-section {
  margin-bottom: 18px;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin-bottom: 6px;
}

.section-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #0071e3;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.section-hint {
  font-size: 12px;
  color: #86868b;
  font-weight: 400;
}

.preview-details {
  margin-top: 16px;
}

.preview-summary {
  font-size: 13px;
  color: #0071e3;
  cursor: pointer;
  font-weight: 500;
  margin-bottom: 8px;
}

.preview-box {
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  padding: 16px;
  font-size: 16px;
  line-height: 1.7;
  color: #1d1d1f;
  background: #fafafa;
  max-height: 300px;
  overflow-y: auto;
}

.preview-box :deep(p) {
  margin: 0 0 6px;
}

.preview-box :deep(a) {
  color: #0071e3;
}

.modal-field {
  margin-bottom: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
