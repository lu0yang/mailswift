<template>
  <div class="settings">
    <n-button text size="small" @click="$router.push('/')" class="back-btn">
      <template #icon><SvgIcon name="arrow-back" /></template>
      <span style="font-size:14px">返回</span>
    </n-button>

    <div class="page-title">设置</div>

    <n-tabs type="line" animated>
      <!-- Tab 1: 模板 -->
      <n-tab-pane name="templates" tab="模板">
        <div class="tab-header">
          <span class="tab-count">{{ templates.length }} 个模板</span>
          <n-button size="small" type="primary" @click="openTemplateEditor()">新建模板</n-button>
        </div>
        <div v-if="templates.length === 0" class="empty">暂无自定义模板</div>
        <div v-for="t in templates" :key="t.id" class="card-row">
          <div class="card-info">
            <span class="card-name">{{ t.name }}</span>
            <span class="card-type">{{ typeLabel(t.type) }}</span>
          </div>
          <div class="card-actions">
            <n-button text size="tiny" @click="openTemplateEditor(t)">编辑</n-button>
            <n-button text size="tiny" type="error" @click="deleteTemplateItem(t.id)">删除</n-button>
          </div>
        </div>
      </n-tab-pane>

      <!-- Tab 2: 签名 -->
      <n-tab-pane name="signatures" tab="签名">
        <div class="tab-header">
          <span class="tab-count">{{ signatures.length }} 个签名</span>
          <n-button size="small" type="primary" @click="openSignatureEditor()">新建签名</n-button>
        </div>
        <div v-if="signatures.length === 0" class="empty">暂无签名</div>
        <div v-for="s in signatures" :key="s.id" class="card-row">
          <div class="card-info">
            <span class="card-name">{{ s.name }}</span>
            <span v-if="s.is_default" class="card-badge">默认</span>
          </div>
          <div class="card-actions">
            <n-button text size="tiny" @click="openSignatureEditor(s)">编辑</n-button>
            <n-button text size="tiny" type="error" @click="deleteSignatureItem(s.id)">删除</n-button>
          </div>
        </div>
      </n-tab-pane>

      <!-- Tab 3: 域名预设 -->
      <n-tab-pane name="domains" tab="域名预设">
        <div class="tab-header">
          <span class="tab-count">{{ domains.length }} 个域名</span>
          <n-button size="small" type="primary" @click="addDomain">添加域名</n-button>
        </div>
        <p class="hint">输入收件人时打出 @ 符号会自动提示这些域名。</p>
        <div v-if="domains.length === 0" class="empty">暂无预设域名</div>
        <div v-for="(d, i) in domains" :key="i" class="card-row">
          <div class="card-info">
            <span class="card-name">@{{ d }}</span>
          </div>
          <div class="card-actions">
            <n-button text size="tiny" type="error" @click="domains.splice(i, 1); saveDomains()">删除</n-button>
          </div>
        </div>
      </n-tab-pane>
    </n-tabs>

    <!-- 模板编辑弹窗 -->
    <n-modal v-model:show="tplShow" preset="card" :title="tplEditId ? '编辑模板' : '新建模板'" style="max-width:600px">
      <n-input v-model:value="tplForm.name" placeholder="模板名称" size="large" style="margin-bottom:12px" />
      <n-select v-model:value="tplForm.type" :options="typeOptions" placeholder="模板类型" size="large" style="margin-bottom:12px" />
      <n-input v-model:value="tplForm.content" type="textarea" :autosize="{ minRows: 4, maxRows: 12 }" placeholder="HTML 内容" />
      <template #footer>
        <n-button @click="tplShow = false">取消</n-button>
        <n-button type="primary" @click="saveTemplate">保存</n-button>
      </template>
    </n-modal>

    <!-- 签名编辑弹窗 -->
    <n-modal v-model:show="sigShow" preset="card" :title="sigEditId ? '编辑签名' : '新建签名'" style="max-width:600px">
      <n-input v-model:value="sigForm.name" placeholder="签名名称" size="large" style="margin-bottom:12px" />
      <n-input v-model:value="sigForm.content" type="textarea" :autosize="{ minRows: 3, maxRows: 8 }" placeholder="HTML 内容" size="large" style="margin-bottom:12px" />
      <n-checkbox v-model:checked="sigForm.is_default">设为默认签名</n-checkbox>
      <template #footer>
        <n-button @click="sigShow = false">取消</n-button>
        <n-button type="primary" @click="saveSignature">保存</n-button>
      </template>
    </n-modal>

    <!-- 域名添加弹窗 -->
    <n-modal v-model:show="domainShow" preset="card" title="添加域名" style="max-width:360px">
      <n-input v-model:value="newDomain" placeholder="如 oe.21vianet.com" size="large" @keyup.enter="confirmAddDomain" />
      <template #footer>
        <n-button @click="domainShow = false">取消</n-button>
        <n-button type="primary" @click="confirmAddDomain">添加</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { NButton, NTabs, NTabPane, NInput, NSelect, NCheckbox, NModal, useMessage } from "naive-ui";
import SvgIcon from "@/components/SvgIcon.vue";
import {
  getTemplates, createTemplate, updateTemplate, deleteTemplate,
  getSignatures, createSignature, updateSignature, deleteSignature,
} from "@/api";

const message = useMessage();

const typeOptions = [
  { label: "账号 Account", value: "account" },
  { label: "订阅 Subscription", value: "subscription" },
];

function typeLabel(t) {
  return t === "account" ? "账号" : t === "subscription" ? "订阅" : "HP";
}

// ── 模板 ──

const templates = ref([]);
const tplShow = ref(false);
const tplEditId = ref(null);
const tplForm = reactive({ name: "", type: "account", content: "" });

async function loadTemplates() {
  try { const { data } = await getTemplates(); templates.value = data.filter(t => t.id > 6); } catch { /* */ }
}

function openTemplateEditor(tpl) {
  if (tpl) { tplEditId.value = tpl.id; tplForm.name = tpl.name; tplForm.type = tpl.type; tplForm.content = tpl.content; }
  else { tplEditId.value = null; tplForm.name = ""; tplForm.type = "account"; tplForm.content = ""; }
  tplShow.value = true;
}

async function saveTemplate() {
  try {
    if (tplEditId.value) { await updateTemplate(tplEditId.value, { name: tplForm.name, content: tplForm.content }); }
    else { await createTemplate({ name: tplForm.name, type: tplForm.type, content: tplForm.content }); }
    tplShow.value = false;
    loadTemplates();
    message.success("已保存");
  } catch { message.error("保存失败"); }
}

async function deleteTemplateItem(id) {
  try { await deleteTemplate(id); loadTemplates(); message.success("已删除"); } catch { message.error("删除失败"); }
}

// ── 签名 ──

const signatures = ref([]);
const sigShow = ref(false);
const sigEditId = ref(null);
const sigForm = reactive({ name: "", content: "", is_default: false });

async function loadSignatures() {
  try { const { data } = await getSignatures(); signatures.value = data; } catch { /* */ }
}

function openSignatureEditor(sig) {
  if (sig) { sigEditId.value = sig.id; sigForm.name = sig.name; sigForm.content = sig.content; sigForm.is_default = sig.is_default; }
  else { sigEditId.value = null; sigForm.name = ""; sigForm.content = ""; sigForm.is_default = false; }
  sigShow.value = true;
}

async function saveSignature() {
  try {
    if (sigEditId.value) { await updateSignature(sigEditId.value, { name: sigForm.name, content: sigForm.content, is_default: sigForm.is_default }); }
    else { await createSignature({ name: sigForm.name, content: sigForm.content, is_default: sigForm.is_default }); }
    sigShow.value = false;
    loadSignatures();
    message.success("已保存");
  } catch { message.error("保存失败"); }
}

async function deleteSignatureItem(id) {
  try { await deleteSignature(id); loadSignatures(); message.success("已删除"); } catch { message.error("删除失败"); }
}

// ── 域名预设 ──

const PRESET_KEY = "mailswift_preset_domains";
const domains = ref([]);
const domainShow = ref(false);
const newDomain = ref("");

function loadDomains() {
  try { domains.value = JSON.parse(localStorage.getItem(PRESET_KEY) || "[]"); } catch { domains.value = []; }
}

function saveDomains() {
  try { localStorage.setItem(PRESET_KEY, JSON.stringify(domains.value)); } catch { /* */ }
}

function addDomain() { newDomain.value = ""; domainShow.value = true; }

function confirmAddDomain() {
  const val = newDomain.value.trim();
  if (!val) return;
  if (domains.value.includes(val)) { message.warning("域名已存在"); return; }
  domains.value.push(val);
  saveDomains();
  domainShow.value = false;
}

// ── Init ──

onMounted(() => {
  loadTemplates();
  loadSignatures();
  loadDomains();
});
</script>

<style scoped>
.settings { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.back-btn { margin-bottom: 12px; }
.page-title { font-size: 28px; font-weight: 700; letter-spacing: -0.4px; margin-bottom: 20px; }

.tab-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.tab-count { font-size: 13px; color: #86868b; }

.card-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #fff; border-radius: 10px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-info { display: flex; align-items: center; gap: 8px; }
.card-name { font-size: 14px; font-weight: 500; }
.card-type { font-size: 12px; color: #86868b; background: #f5f5f7; padding: 2px 8px; border-radius: 4px; }
.card-badge { font-size: 11px; color: #0071e3; background: #e8f0fe; padding: 2px 8px; border-radius: 4px; }
.card-actions { display: flex; gap: 4px; }

.hint { font-size: 13px; color: #86868b; margin-bottom: 16px; }
.empty { text-align: center; padding: 40px 0; color: #86868b; font-size: 14px; }
</style>
