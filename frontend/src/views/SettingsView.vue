<template>
  <div class="settings">
    <n-button text size="small" @click="$router.push('/')" class="back-btn">
      <template #icon><n-icon><arrow-back-outline /></n-icon></template>
      <span style="font-size:14px">返回</span>
    </n-button>

    <div class="page-title">设置</div>

    <n-tabs type="line" animated>
      <!-- SMTP Tab -->
      <n-tab-pane name="smtp" tab="SMTP 配置">
        <div class="settings-card">
          <div class="form-row">
            <div class="form-col host-col">
              <label class="field-label">SMTP 服务器</label>
              <n-input v-model:value="smtpHost" size="large" clearable />
            </div>
            <div class="form-col port-col">
              <label class="field-label">端口</label>
              <n-input-number v-model:value="smtpPort" :min="1" :max="65535" size="large" />
            </div>
          </div>
          <div class="form-field">
            <label class="field-label">邮箱地址</label>
            <n-input v-model:value="emailAddress" placeholder="yourname@company.com" size="large" clearable />
          </div>
          <div class="form-field">
            <label class="field-label">密码 / 应用专用密码</label>
            <n-input v-model:value="password" type="password" show-password-on="click" placeholder="输入密码" size="large" />
          </div>
          <div class="btn-row">
            <n-button size="large" :loading="testing" @click="handleTest">
              测试连接
            </n-button>
            <n-button type="primary" size="large" :loading="saving" :disabled="!smtpTested" @click="handleSave">
              保存凭据
            </n-button>
          </div>
          <div v-if="!smtpTested && (emailAddress || password)" class="test-hint">
            请先通过连接测试，成功后方可保存凭据
          </div>
          <div v-if="statusText" class="status-bar">
            <span class="status-dot" :class="statusType"></span>
            {{ statusText }}
          </div>
        </div>
      </n-tab-pane>

      <!-- IMAP Tab -->
      <n-tab-pane name="imap" tab="IMAP 配置">
        <div class="settings-card">
          <p class="tab-desc">用于在发送邮件后将副本存入"已发送邮件"文件夹。</p>
          <div class="form-row">
            <div class="form-col host-col">
              <label class="field-label">IMAP 服务器</label>
              <n-input v-model:value="imapHost" size="large" clearable />
            </div>
            <div class="form-col port-col">
              <label class="field-label">端口</label>
              <n-input-number v-model:value="imapPort" :min="1" :max="65535" size="large" />
            </div>
          </div>
          <n-button type="primary" size="large" :loading="saving" @click="handleSave">
            保存 IMAP 配置
          </n-button>
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
            <div class="list-card-preview">{{ t.content.slice(0, 100) }}{{ t.content.length > 100 ? '…' : '' }}</div>
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

    <!-- Template Edit Modal -->
    <n-modal v-model:show="templateModalVisible" preset="card" title="模板" style="max-width:720px">
      <div class="modal-field">
        <label class="field-label">模板名称</label>
        <n-input v-model:value="templateForm.name" placeholder="例如：正式账号通知" size="large" />
      </div>
      <div class="modal-field">
        <label class="field-label">类型</label>
        <n-select
          v-model:value="templateForm.type"
          :options="[{ label: '账号创建', value: 'account' }, { label: '订阅创建', value: 'subscription' }]"
          size="large"
        />
      </div>
      <div class="modal-field">
        <label class="field-label">
          正文内容
          <span class="field-hint">
            — 变量：
            <code v-if="templateForm.type === 'account'">{account_list}</code>
            <code v-else>{subscription_list}</code>
          </span>
        </label>
        <RichTextEditor v-model="templateForm.content" />
      </div>
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
        <label class="field-label">签名内容</label>
        <RichTextEditor v-model="sigForm.content" />
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
import { ref, computed, watch, onMounted } from "vue";
import {
  NInput, NInputNumber, NSelect, NButton, NIcon, NTabs, NTabPane,
  NModal, NCheckbox, useMessage,
} from "naive-ui";
import { ArrowBackOutline, AddOutline } from "@vicons/ionicons5";
import RichTextEditor from "@/components/RichTextEditor.vue";
import {
  getSettings, updateSettings, testSmtp,
  getTemplates, createTemplate, updateTemplate, deleteTemplate,
  getSignatures, createSignature, updateSignature, deleteSignature,
} from "@/api";

const message = useMessage();

// ── SMTP / IMAP ──────────────────────

const smtpHost = ref("mail.21vianet.com");
const smtpPort = ref(587);
const emailAddress = ref("");
const password = ref("");
const imapHost = ref("partner.outlook.cn");
const imapPort = ref(993);
const saving = ref(false);
const testing = ref(false);
const smtpTested = ref(false);
const statusText = ref("");
const statusType = ref("");

onMounted(async () => {
  try {
    const { data } = await getSettings();
    smtpHost.value = data.smtp_host || "mail.21vianet.com";
    smtpPort.value = data.smtp_port || 587;
    emailAddress.value = data.email_address;
    imapHost.value = data.imap_host || "partner.outlook.cn";
    imapPort.value = data.imap_port || 993;
    if (data.password_masked) {
      statusText.value = `已配置  |  上次更新：${data.updated_at?.slice(0, 10) || "-"}`;
      statusType.value = "success";
      smtpTested.value = true;
    }
  } catch { /* not yet configured */ }
  await loadTemplates();
  await loadSignatures();
});

// Reset test state when SMTP fields change
watch([smtpHost, smtpPort, emailAddress, password], () => {
  smtpTested.value = false;
});

async function handleSave() {
  if (!smtpTested.value) {
    message.warning("请先通过连接测试再保存");
    return;
  }
  saving.value = true;
  try {
    await updateSettings({
      smtp_host: smtpHost.value,
      smtp_port: smtpPort.value,
      email_address: emailAddress.value,
      password: password.value,
      imap_host: imapHost.value,
      imap_port: imapPort.value,
    });
    message.success("已保存");
    statusText.value = "已配置";
    statusType.value = "success";
    password.value = "";
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
    await testSmtp({
      smtp_host: smtpHost.value,
      smtp_port: smtpPort.value,
      email_address: emailAddress.value,
      password: password.value,
    });
    smtpTested.value = true;
    message.success("连接测试成功");
  } catch (err) {
    smtpTested.value = false;
    message.error(err.response?.data?.detail || "连接测试失败");
  } finally {
    testing.value = false;
  }
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
const templateForm = ref({ name: "", type: "account", content: "" });

async function loadTemplates() {
  try {
    const { data } = await getTemplates();
    templates.value = data;
  } catch { /* ignore */ }
}

function openTemplateModal(template) {
  if (template) {
    editingTemplateId.value = template.id;
    templateForm.value = {
      name: template.name,
      type: template.type,
      content: template.content,
    };
  } else {
    editingTemplateId.value = null;
    templateForm.value = { name: "", type: "account", content: "" };
  }
  templateModalVisible.value = true;
}

async function handleSaveTemplate() {
  if (!templateForm.value.name) {
    message.warning("请输入模板名称");
    return;
  }
  templateSaving.value = true;
  try {
    if (editingTemplateId.value) {
      await updateTemplate(editingTemplateId.value, templateForm.value);
    } else {
      await createTemplate(templateForm.value);
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
  try {
    await deleteTemplate(id);
    message.success("模板已删除");
    await loadTemplates();
  } catch {
    message.error("删除失败");
  }
}

// ── Signatures ────────────────────────

const signatures = ref([]);
const sigModalVisible = ref(false);
const sigSaving = ref(false);
const editingSigId = ref(null);
const sigForm = ref({ name: "", content: "", is_default: false });

async function loadSignatures() {
  try {
    const { data } = await getSignatures();
    signatures.value = data;
  } catch { /* ignore */ }
}

function openSignatureModal(sig) {
  if (sig) {
    editingSigId.value = sig.id;
    sigForm.value = { name: sig.name, content: sig.content, is_default: sig.is_default };
  } else {
    editingSigId.value = null;
    sigForm.value = { name: "", content: "", is_default: false };
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
  try {
    await deleteSignature(id);
    message.success("签名已删除");
    await loadSignatures();
  } catch {
    message.error("删除失败");
  }
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

.tab-desc {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  gap: 12px;
  margin-bottom: 18px;
}

.form-col.host-col { flex: 3; }
.form-col.port-col { flex: 1; }

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

.status-bar {
  margin-top: 16px;
  font-size: 13px;
  color: #86868b;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e0e0e0;
}

.status-dot.success { background: #34c759; }

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

/* ── Modal ────────────────────────── */

.modal-field {
  margin-bottom: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
