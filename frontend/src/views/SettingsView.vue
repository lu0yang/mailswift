<template>
  <div class="settings">
    <n-button text size="small" @click="$router.push('/')" class="back-btn">
      <template #icon><SvgIcon name="arrow-back" /></template>
      <span style="font-size:14px">返回</span>
    </n-button>

    <div class="page-title">设置</div>

    <n-tabs type="line" animated>

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
            <n-button v-if="templateFilter !== 'high_priority'" type="primary" size="small" @click="openTemplateModal(null)">
              <template #icon><SvgIcon name="add" /></template>
              新建模板
            </n-button>
          </div>
          <div v-if="filteredTemplates.length === 0" class="empty">暂无模板</div>
          <div v-for="t in filteredTemplates" :key="t.id" class="list-card">
            <div class="list-card-main">
              <div class="list-card-left">
                <span class="type-badge" :class="t.type">{{ t.type === 'account' ? '账号' : t.type === 'subscription' ? '订阅' : 'HP' }}</span>
                <span class="list-card-name">{{ t.name }}</span>
                <span v-if="t.is_public" class="public-badge">公共</span>
              </div>
              <div v-if="!t.is_public" class="list-card-right">
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
              <template #icon><SvgIcon name="add" /></template>
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

      <!-- Preset Domains Tab -->
      <n-tab-pane name="domains" tab="预设域名">
        <div class="settings-card">
          <div class="tab-header">
            <span class="tab-header-hint">收件人输入 @ 后显示的域名建议列表</span>
            <n-button type="primary" size="small" @click="openDomainModal(-1)">
              <template #icon><SvgIcon name="add" /></template>
              添加域名
            </n-button>
          </div>
          <div v-if="domains.length === 0" class="empty">暂无预设域名</div>
          <div v-for="(d, i) in domains" :key="i" class="list-card">
            <div class="list-card-main">
              <div class="list-card-left">
                <span class="list-card-name">{{ d }}</span>
                <span class="list-card-badge" :class="DEFAULT_DOMAINS.includes(d) ? 'badge-default' : 'badge-personal'">
                  {{ DEFAULT_DOMAINS.includes(d) ? '默认' : '个人' }}
                </span>
              </div>
              <div v-if="!DEFAULT_DOMAINS.includes(d)" class="list-card-right">
                <n-button text size="tiny" @click="openDomainModal(i)">编辑</n-button>
                <n-button text size="tiny" type="error" @click="removeDomain(i)">删除</n-button>
              </div>
            </div>
          </div>
        </div>

        <!-- Domain edit modal -->
        <n-modal v-model:show="domainModalVisible" preset="card" :title="domainEditIndex >= 0 ? '编辑域名' : '添加域名'" style="max-width:400px">
          <div class="modal-field">
            <label class="field-label">域名（以 @ 开头）</label>
            <n-input v-model:value="domainFormValue" placeholder="@example.com" size="large" />
          </div>
          <template #footer>
            <div class="modal-footer">
              <n-button @click="domainModalVisible = false">取消</n-button>
              <n-button type="primary" :disabled="!domainFormValue.startsWith('@')" @click="saveDomain">保存</n-button>
            </div>
          </template>
        </n-modal>
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
          <span class="section-hint">— 所有{{ templateForm.type === 'account' ? '账号' : '订阅' }}前，出现一次</span>
        </label>
        <RichTextEditor v-model="templateForm.header" :variables="headerVariables" />
      </div>

      <div class="modal-section">
        <label class="section-label">
          <span class="section-num">2</span> 每条{{ templateForm.type === 'account' ? '账号' : '订阅' }}格式
          <span class="section-hint">— 有几条{{ templateForm.type === 'account' ? '账号' : '订阅' }}就重复几次</span>
        </label>
        <RichTextEditor v-model="templateForm.item" :variables="itemVariables" />
      </div>

      <div class="modal-section">
        <label class="section-label">
          <span class="section-num">3</span> 结尾文字
          <span class="section-hint">— 所有{{ templateForm.type === 'account' ? '账号' : '订阅' }}后，出现一次</span>
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
            <div :style="sigPreviewScale < 1 ? { transform: `scale(${sigPreviewScale})`, transformOrigin: 'top left', width: `${100 / sigPreviewScale}%` } : {}">
              <div class="preview-box" v-html="sigForm.content"></div>
            </div>
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
import { ref, computed, watch, onMounted, nextTick } from "vue";
import {
  NInput, NSelect, NButton, NTabs, NTabPane, NAutoComplete,
  NModal, NCheckbox, useMessage, useDialog,
} from "naive-ui";
import SvgIcon from "@/components/SvgIcon.vue";
import RichTextEditor from "@/components/RichTextEditor.vue";
import {
  getTemplates, createTemplate, updateTemplate, deleteTemplate,
  getSignatures, createSignature, updateSignature, deleteSignature,
  resetApp, getDomains, updateDomains, DEFAULT_DOMAINS,
} from "@/api";

const message = useMessage();
const dialog = useDialog();

// ── Init ──────────────────────────────

onMounted(() => {
  loadTemplates();
  loadSignatures();
  loadDomains();
});

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
  { label: "HP", value: "high_priority" },
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
    message.warning(templateForm.value.type === "account" ? "请填写至少每条账号格式" : "请填写至少每条订阅格式");
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
const sigPreviewScale = ref(1.0);

async function loadSignatures() {
  try {
    const { data } = await getSignatures();
    signatures.value = data;
  } catch { /* ignore */ }
}

// ── Preset domains ──────────────────

const domains = ref([]);           // 全量（默认+自定义），仅用于展示
let customDomains = [];            // 用户自己添加的，存数据库

const domainModalVisible = ref(false);
const domainEditIndex = ref(-1);
const domainFormValue = ref("");

async function loadDomains() {
  try {
    const { data } = await getDomains();
    customDomains = data.domains || [];
  } catch {
    customDomains = [];
  }
  // 始终合并默认域名 + 用户自定义，去重
  domains.value = [...new Set([...DEFAULT_DOMAINS, ...customDomains])];
  localStorage.setItem("mailswift_preset_domains", JSON.stringify(domains.value));
}

async function saveDomains() {
  // 只把用户自己加的（非默认）存入数据库
  customDomains = domains.value.filter(d => !DEFAULT_DOMAINS.includes(d));
  localStorage.setItem("mailswift_preset_domains", JSON.stringify(domains.value));
  try { await updateDomains(customDomains); } catch { /* */ }
}

function openDomainModal(index) {
  domainEditIndex.value = index;
  domainFormValue.value = index >= 0 ? domains.value[index] : "";
  domainModalVisible.value = true;
}

function saveDomain() {
  const val = domainFormValue.value.trim();
  if (!val || !val.startsWith("@")) return;
  if (domains.value.includes(val) && domains.value[domainEditIndex.value] !== val) {
    message.warning("该域名已存在");
    return;
  }
  if (domainEditIndex.value >= 0) {
    domains.value[domainEditIndex.value] = val;
  } else {
    domains.value.push(val);
  }
  saveDomains();
  domainModalVisible.value = false;
  message.success(domainEditIndex.value >= 0 ? "已更新" : "已添加");
}

function removeDomain(index) {
  const domain = domains.value[index];
  if (DEFAULT_DOMAINS.includes(domain)) {
    message.warning("默认域名不可删除");
    return;
  }
  dialog.warning({
    title: "确认删除",
    content: `确定要删除 ${domain} 吗？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: () => {
      domains.value.splice(index, 1);
      saveDomains();
      message.success("已删除");
    },
  });
}

function measurePreviewScale() {
  nextTick(() => {
    const wrap = document.querySelector(".preview-box .sig-paste-wrap");
    if (!wrap) return;
    const h = wrap.scrollHeight;
    sigPreviewScale.value = h > 200 ? Math.max(0.3, 200 / h) : 1.0;
  });
}

/**
 * 从 RTF 数据中提取嵌入的图片，返回 data URI 数组。
 * 统一走 createImageBitmap + canvas → PNG，让浏览器系统解码器识别所有格式。
 */
async function extractRtfImages(rtf) {
  const result = [];
  if (!rtf) return result;

  // 匹配所有图片格式: *blip (pngblip/jpegblip) + wmetafile + emfblip
  const blipRegex = /\\(pngblip|jpegblip|wmetafile|emfblip|\w*blip)(?:\\\w+)*(?:{.*?})*/gi;
  let blipMatch;
  while ((blipMatch = blipRegex.exec(rtf)) !== null) {
    let hexStart = blipMatch.index + blipMatch[0].length;
    let hexStr = "";
    while (hexStart < rtf.length) {
      const ch = rtf[hexStart];
      if (ch === "}") break;
      if (/[0-9a-fA-F]/.test(ch)) {
        hexStr += ch;
      } else if (ch === "\\") {
        while (hexStart < rtf.length && rtf[hexStart] !== " " && rtf[hexStart] !== "}") {
          hexStart++;
        }
        if (rtf[hexStart] === "}") break;
      } else if (ch === "\r" || ch === "\n" || ch === " ") {
        // skip
      } else {
        break;
      }
      hexStart++;
    }

    if (hexStr.length < 200) continue;

    const len = Math.floor(hexStr.length / 2);
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = parseInt(hexStr.substring(i * 2, i * 2 + 2), 16);
    }

    // 统一使用浏览器的系统解码器处理所有格式（PNG/JPEG/WMF/EMF 等）
    try {
      const blob = new Blob([bytes]);
      const bmp = await createImageBitmap(blob);
      const canvas = document.createElement('canvas');
      canvas.width = bmp.width;
      canvas.height = bmp.height;
      canvas.getContext('2d').drawImage(bmp, 0, 0);
      bmp.close();
      result.push(canvas.toDataURL('image/png'));
    } catch {
      // 解码失败 → 回退为原始 base64
      let binary = "";
      for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
      result.push(`data:image/png;base64,${btoa(binary)}`);
    }
  }
  return result;
}

async function onSigPaste(e) {
  e.preventDefault();
  const rawHtml = e.clipboardData?.getData("text/html");
  if (!rawHtml) return;

  e.target.innerHTML = "";

  // 从原始 HTML 提取 file:// 路径
  const fileSrcs = [];
  const fileRegex = /src\s*=\s*\"(file:\/\/\/[^\"]+|[A-Za-z]:[\\\/][^\"]+)\"/gi;
  let match;
  while ((match = fileRegex.exec(rawHtml)) !== null) {
    fileSrcs.push(match[1]);
  }

  let processedHtml = rawHtml;
  if (fileSrcs.length > 0) {
    sigImageConverting.value = true;
    const rtfData = e.clipboardData?.getData("text/rtf") || "";
    console.log("[sig] fileSrcs:", fileSrcs.length, "rtfLen:", rtfData.length,
      "blips:", ["pngblip","jpegblip","wmetafile","emfblip"].map(k =>
        k+":"+(rtfData.match(new RegExp("\\\\"+k,"gi"))||[]).length).join(", "));
    const rtfImages = await extractRtfImages(rtfData);
    console.log("[sig] images:", rtfImages.length, "sizes:", rtfImages.map(i => i ? i.length : 0));
    // 文件路径去重
	    const uniqueSrcs = [...new Set(fileSrcs)];
	    const count = Math.min(uniqueSrcs.length, rtfImages.length);
    for (let i = 0; i < count; i++) {
      if (rtfImages[i]) {
        processedHtml = processedHtml.replaceAll(uniqueSrcs[i], rtfImages[i]);
      }
    }
    sigImageConverting.value = false;
  }

  // 用处理后的 HTML 重新解析
  const parser = new DOMParser();
  const doc = parser.parseFromString(processedHtml, "text/html");

  // Vertically center all table cells (Outlook defaults to top)
  doc.querySelectorAll("td").forEach((td) => {
    td.style.verticalAlign = "middle";
  });

  // Remove empty <p> and <o:p> noise that Outlook injects, then tighten paragraph spacing
  doc.querySelectorAll("p").forEach((p) => {
    // Don't touch paragraphs that contain images
    if (p.querySelector("img")) {
      p.style.margin = "0 0 4px 0";
      p.style.lineHeight = "1.4";
      return;
    }
    if (!p.textContent.trim() || p.textContent === " ") {
      p.remove();
    } else {
      p.style.margin = "0 0 4px 0";
      p.style.lineHeight = "1.4";
      p.querySelectorAll("o\\:p").forEach((op) => op.remove());
    }
  });

  // Force all images to their natural resolution. Outlook wraps them in
  // tables with hardcoded cell sizes; rather than chasing every attribute,
  // we use !important to reclaim control.
  doc.querySelectorAll("img").forEach((img) => {
    img.removeAttribute("naturalheight");
    img.removeAttribute("naturalwidth");
    img.style.setProperty("width", "auto", "important");
    img.style.setProperty("height", "auto", "important");
    img.style.setProperty("max-width", "100%", "important");
  });

  sigForm.value.content = '<div class="sig-paste-wrap" style="max-width:600px;">' + doc.body.innerHTML + '</div>';
  measurePreviewScale();
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
  if (sigForm.value.content) measurePreviewScale();
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

.account-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
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

.saved-accounts {
  border-top: 1px solid #f0f0f0;
  margin-top: 24px;
  padding-top: 20px;
}

.saved-title {
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin-bottom: 10px;
}

.saved-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f8f8f8;
}

.saved-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.saved-email {
  font-size: 14px;
  color: #1d1d1f;
}

.saved-active {
  font-size: 11px;
  padding: 1px 6px;
  background: #e6f4ea;
  color: #1e8e3e;
  border-radius: 4px;
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

.tab-header-hint {
  font-size: 13px;
  color: #86868b;
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

.list-card-badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 4px;
  margin-left: 6px;
  vertical-align: middle;
}

.badge-default { background: #e8f0fe; color: #0071e3; }
.badge-personal { background: #fff3e0; color: #e67e00; }

.type-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 5px;
}

.type-badge.account { background: #f0f7ff; color: #0071e3; }
.type-badge.subscription { background: #f3e8ff; color: #7c3aed; }
.type-badge.high_priority { background: #ffe8e8; color: #c00000; }

.default-badge {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 5px;
  background: #e8f8ed;
  color: #34c759;
}

.public-badge {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 5px;
  background: #fff3e0;
  color: #e67e00;
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

.preview-box :deep(img) {
  max-width: 100%;
  height: auto;
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
