<template>
  <div class="business-page">
    <div class="title-row">
      <div class="page-title">账号创建 / 重置</div>
      <div class="title-actions">
        <n-button text size="small" @click="handleSaveDraft" :disabled="!draft.isDirty.value">
          <template #icon><SvgIcon name="save" /></template>
          暂存草稿
        </n-button>
        <n-button text type="error" size="small" @click="handleClear">
          <template #icon><SvgIcon name="trash" /></template>
          一键清理
        </n-button>
      </div>
    </div>

    <!-- 模板选择 -->
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

    <!-- 标题 -->
    <div class="form-field">
      <label class="field-label">邮件标题 *</label>
      <div class="field-wrapper">
        <n-input
          v-model:value="subject"
          placeholder="邮件标题"
          size="large"
          clearable
          :input-props="{ autocomplete: 'off' }"
          @focus="cancelDropdownHide(); subjectDropdownShow = filtSubjHistory.length > 0"
          @blur="hideDropdownWithDelay('subject')"
        />
        <div v-if="subjectDropdownShow" class="history-dropdown">
          <div v-for="item in filtSubjHistory" :key="item" class="history-dropdown-item"
            @mousedown.prevent="subject = item; subjectDropdownShow = false">
            {{ item }}
          </div>
          <div v-if="filtSubjHistory.length === 0" class="history-dropdown-empty">无匹配记录</div>
        </div>
      </div>
    </div>

    <!-- 收件人 / 抄送 -->
    <div class="form-row">
      <div class="form-col">
        <label class="field-label">收件人 *</label>
        <div class="field-wrapper">
          <div class="pill-input-shell" :class="{ 'pill-input-error': recip.error.value }">
            <span v-for="(addr, i) in recip.tags.value" :key="i" class="pill-tag"
              :class="{ editing: recip.editIdx.value === i }" @dblclick="recip.editIdx.value = i">
              <template v-if="recip.editIdx.value === i">
                <input v-model="recip.tags.value[i]" class="pill-edit-input"
                  @keyup.enter="recip.editIdx.value = -1" @blur="recip.editIdx.value = -1" @click.stop />
              </template>
              <template v-else>
                {{ addr }}<button class="pill-tag-x" @click="recip.tags.value.splice(i, 1)">&times;</button>
              </template>
            </span>
            <div class="pill-auto">
              <n-input v-model:value="recip.input.value" placeholder="输入邮箱，回车添加" size="small"
                :input-props="{ autocomplete: 'off' }"
                @keyup.enter.prevent="recip.addTag()"
                @focus="cancelDropdownHide(); recipientDropdownShow = filtRecipHistory.length > 0"
                @blur="recip.addTag(); hideDropdownWithDelay('recipient')" />
            </div>
          </div>
          <div v-if="recipientDropdownShow" class="history-dropdown">
            <div v-for="item in filtRecipHistory" :key="item" class="history-dropdown-item"
              @mousedown.prevent="recip.input.value = item; recipientDropdownShow = false">
              {{ item }}
            </div>
            <div v-if="filtRecipHistory.length === 0" class="history-dropdown-empty">无匹配记录</div>
          </div>
        </div>
        <span v-if="recip.error.value" class="field-error">{{ recip.error.value }}</span>
      </div>
      <div class="form-col">
        <label class="field-label">抄送 CC</label>
        <div class="field-wrapper">
          <div class="pill-input-shell">
            <span v-for="(addr, i) in recip.ccTags.value" :key="i" class="pill-tag"
              :class="{ editing: recip.editCcIdx.value === i }" @dblclick="recip.editCcIdx.value = i">
              <template v-if="recip.editCcIdx.value === i">
                <input v-model="recip.ccTags.value[i]" class="pill-edit-input"
                  @keyup.enter="recip.editCcIdx.value = -1" @blur="recip.editCcIdx.value = -1" @click.stop />
              </template>
              <template v-else>
                {{ addr }}<button class="pill-tag-x" @click="recip.ccTags.value.splice(i, 1)">&times;</button>
              </template>
            </span>
            <div class="pill-auto">
              <n-input v-model:value="recip.ccInput.value" placeholder="输入邮箱，回车添加" size="small"
                :input-props="{ autocomplete: 'off' }"
                @keyup.enter.prevent="recip.addCcTag()"
                @focus="cancelDropdownHide(); ccDropdownShow = filtCcHistory.length > 0"
                @blur="recip.addCcTag(); hideDropdownWithDelay('cc')" />
            </div>
          </div>
          <div v-if="ccDropdownShow" class="history-dropdown">
            <div v-for="item in filtCcHistory" :key="item" class="history-dropdown-item"
              @mousedown.prevent="recip.ccInput.value = item; ccDropdownShow = false">
              {{ item }}
            </div>
            <div v-if="filtCcHistory.length === 0" class="history-dropdown-empty">无匹配记录</div>
          </div>
        </div>
        <span v-if="recip.ccError.value" class="field-error">{{ recip.ccError.value }}</span>
      </div>
    </div>

    <!-- 账号表单 -->
    <AccountForm v-model="formData" :key="formKey" />

    <!-- 正文编辑器 -->
    <div class="preview-card">
      <div class="preview-header">邮件正文（富文本编辑）</div>
      <RichTextEditor ref="rteRef" v-model="body" v-model:attachments="attachments" @update:model-value="onBodyEdited" />
    </div>

    <!-- 预览按钮 -->
    <div class="preview-btn-row">
      <n-button size="large" @click="previewVisible = true">
        <template #icon><SvgIcon name="eye" /></template>
        预览邮件
      </n-button>
    </div>

    <!-- 预览弹窗 -->
    <n-modal v-model:show="previewVisible" preset="card" title="邮件预览" style="max-width:1060px">
      <div v-if="recip.tags.value.length || recip.ccTags.value.length || subject" class="preview-meta">
        <div v-if="recip.tags.value.length" class="preview-meta-row">
          <span class="preview-meta-label">收件人</span>
          <span class="preview-meta-val">
            <span v-for="(addr, i) in recip.tags.value" :key="i" class="preview-pill">{{ addr }}</span>
          </span>
        </div>
        <div v-if="recip.ccTags.value.length" class="preview-meta-row">
          <span class="preview-meta-label">抄送</span>
          <span class="preview-meta-val">
            <span v-for="(addr, i) in recip.ccTags.value" :key="i" class="preview-pill">{{ addr }}</span>
          </span>
        </div>
        <div v-if="subject" class="preview-meta-row">
          <span class="preview-meta-label">标题</span>
          <span class="preview-meta-val preview-meta-subject">{{ subject }}</span>
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

    <!-- 签名 -->
    <div class="form-field">
      <label class="field-label">邮件签名</label>
      <n-select v-model:value="selectedSignatureId" :options="signatureOptions" placeholder="选择签名（可选）" size="large" clearable />
    </div>

    <!-- 发送 -->
    <n-tooltip :disabled="canSend" placement="top">
      <template #trigger>
        <n-button type="primary" size="large" :loading="sending" :disabled="!canSend" block @click="handleSend">
          <template #icon><SvgIcon name="send" /></template>
          发送邮件
        </n-button>
      </template>
      <div v-for="h in sendHints" :key="h" class="send-hint-line">{{ h }}</div>
    </n-tooltip>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, inject, nextTick } from 'vue'
import { NInput, NSelect, NButton, NModal, NTooltip, useMessage } from 'naive-ui'
import SvgIcon from '@/components/SvgIcon.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import AccountForm from '@/components/AccountForm.vue'
import { sendEmail, getTemplates, getSignatures } from '@/api'
import { useDraft } from '@/composables/useDraft'
import { useFieldHistory, FIELD_HISTORY_KEYS } from '@/composables/useFieldHistory'
import { useRecipients } from '@/composables/useRecipients'

const message = useMessage()
const accountEmail = inject('accountEmail', ref(''))


// ── Composables ──
const draft = useDraft('account')
const history = useFieldHistory()
const recip = useRecipients()

// ── State ──
const subject = ref('')
const body = ref('')
const bodySource = ref('')
const userEditedBody = ref(false)
const selectedTemplateId = ref(null)
const selectedSignatureId = ref(null)
const formData = ref({})
const formKey = ref(0)
const attachments = ref([])
const templates = ref([])
const signatures = ref([])
const previewVisible = ref(false)
const sending = ref(false)
const rteRef = ref(null)

// ── Dropdown state ──
const subjectDropdownShow = ref(false)
const recipientDropdownShow = ref(false)
const ccDropdownShow = ref(false)
let hideDropdownTimer = null

function hideDropdownWithDelay(which) {
  clearTimeout(hideDropdownTimer)
  hideDropdownTimer = setTimeout(() => {
    if (which === 'subject') subjectDropdownShow.value = false
    else if (which === 'recipient') recipientDropdownShow.value = false
    else ccDropdownShow.value = false
  }, 200)
}
function cancelDropdownHide() { clearTimeout(hideDropdownTimer) }
function closeAllDropdowns() {
  subjectDropdownShow.value = false
  recipientDropdownShow.value = false
  ccDropdownShow.value = false
}
function onDocumentClick(e) {
  if (e.target.closest('.field-wrapper')) return
  closeAllDropdowns()
}

// ── Filtered histories ──
const filtSubjHistory = history.filteredSubjectOptions(subject)
const filtRecipHistory = history.filteredRecipientOptions(recip.input)
const filtCcHistory = history.filteredCcOptions(recip.ccInput)

// ── Watch auto-show dropdowns ──
watch(recip.input, () => { if (filtRecipHistory.value.length) recipientDropdownShow.value = true })
watch(recip.ccInput, () => { if (filtCcHistory.value.length) ccDropdownShow.value = true })

// ── Domain watch ──
recip.installDomainWatch(recip.input, history.loadPresetDomains)
recip.installDomainWatch(recip.ccInput, history.loadPresetDomains)

// ── Template options ──
const templateOptions = computed(() =>
  templates.value.filter(t => t.type === 'account').map(t => ({ label: t.name, value: t.id }))
)

const signatureOptions = computed(() =>
  signatures.value.map(s => ({
    label: s.is_default ? s.name + ' （默认）' : s.name,
    value: s.id,
  }))
)

const previewHtml = computed(() => {
  let html = body.value || ''
  if (selectedSignatureId.value) {
    const sig = signatures.value.find(s => s.id === selectedSignatureId.value)
    if (sig && sig.content) {
      html += '<br>' + sig.content
    }
  }
  return html
})

// ── Template rendering ──

function renderTemplateContent(templateContent) {
  if (!templateContent) return ''
  try {
    const tpl = JSON.parse(templateContent)
    if (tpl && typeof tpl === 'object' && 'item' in tpl) return renderNewFormat(tpl)
  } catch { /* legacy – render as-is with variable substitution */ }
  let html = templateContent
  const accounts = (formData.value.accounts || []).filter(a => a.account || a.password || a.account_type)
  const lines = accounts.map((a, i) => `${i + 1}. ${a.account} / ${a.password} / ${a.account_type}`)
  html = html.replaceAll('{account_list}', lines.join('<br>') || '（无）')
  return html
}

function renderNewFormat(tpl) {
  let header = tpl.header || ''
  const itemTpl = tpl.item || ''
  const footer = tpl.footer || ''
  const accounts = (formData.value.accounts || []).filter(a => a.account || a.password || a.account_type)
  const count = accounts.length
  header = header.replaceAll('{account_plural}', count === 1 ? 'account' : 'accounts')
  header = header.replaceAll('{have_has}', count === 1 ? 'has' : 'have')
  const items = accounts.map(a => {
    let part = itemTpl
    part = part.replaceAll('{username}', a.account || '')
    part = part.replaceAll('{password}', a.password || '')
    part = part.replaceAll('{account_type}', a.account_type || '')
    return part
  })
  const parts = [header, ...items, footer].filter(p => p.trim())
  return parts.join('')
}

function substitutePlainMarkers(text) {
  const accounts = (formData.value.accounts || []).filter(a => a.account || a.password || a.account_type)
  text = text.replaceAll('{account_plural}', accounts.length === 1 ? 'account' : 'accounts')
  text = text.replaceAll('{have_has}', accounts.length === 1 ? 'has' : 'have')
  text = text.replaceAll('{account_list}', accounts.map((a, i) => `${i + 1}. ${a.account} / ${a.password} / ${a.account_type}`).join('<br>') || '（无）')
  if (accounts.length >= 1) {
    text = text.replaceAll('{username}', accounts[0].account || '')
    text = text.replaceAll('{password}', accounts[0].password || '')
    text = text.replaceAll('{account_type}', accounts[0].account_type || '')
  }
  return text
}

// ── Body auto-render watcher ──
const MARKERS = ['{account_list}', '{account_plural}', '{username}', '{password}', '{account_type}', '{have_has}']

watch([formData, selectedTemplateId], () => {
  if (selectedTemplateId.value) {
    if (userEditedBody.value) return
    const t = templates.value.find(tp => tp.id === selectedTemplateId.value)
    if (t) {
      bodySource.value = t.content
      body.value = renderTemplateContent(t.content)
    }
    return
  }
  if (body.value && MARKERS.some(m => body.value.includes(m))) {
    bodySource.value = body.value
    body.value = substitutePlainMarkers(bodySource.value)
  }
}, { deep: true })

// ── Event handlers ──

function onBodyEdited() { userEditedBody.value = true }

function onTemplateChange(id) {
  if (!id) { bodySource.value = ''; body.value = ''; return }
  const t = templates.value.find(tp => tp.id === id)
  if (t) {
    bodySource.value = t.content
    userEditedBody.value = false
    body.value = renderTemplateContent(t.content)
    selectedSignatureId.value = null
    autoSelectDefaultSignature()
  }
}

function autoSelectDefaultSignature() {
  if (selectedSignatureId.value) return
  const def = signatures.value.find(s => s.is_default)
  if (def) selectedSignatureId.value = def.id
}

// ── Send hints ──
const sendHints = computed(() => {
  const hints = []
  if (!accountEmail.value) hints.push('请先在设置中配置邮箱凭据')

  if (!subject.value) hints.push('请填写邮件标题')
  if (!body.value.trim()) hints.push('请填写邮件正文')
  if (!recip.tags.value.length) hints.push('请添加至少一个收件人')
  else if (recip.error.value) hints.push(recip.error.value)
  if (recip.ccError.value) hints.push(recip.ccError.value)
  const accts = formData.value.accounts || []
  if (!accts || !accts.length) hints.push('请至少添加一条账号信息')
  else if (!accts.some(a => a.account && a.password && a.account_type)) hints.push('请完整填写至少一条账号（账号、密码、类型）')
  return hints
})

const canSend = computed(() => sendHints.value.length === 0)

// ── Draft ──

function getFormState() {
  return {
    selectedTemplateId: selectedTemplateId.value,
    selectedSignatureId: selectedSignatureId.value,
    subject: subject.value,
    recipient: recip.joinTags(),
    cc: recip.joinCcTags(),
    body: body.value,
    formData: formData.value,
  }
}

function handleSaveDraft() {
  draft.save(getFormState())
  message.success('草稿已暂存')
}

function loadDraftIntoForm() {
  const d = draft.load()
  if (!d) return
  draft.suppress.value = true
  selectedTemplateId.value = d.selectedTemplateId || null
  selectedSignatureId.value = d.selectedSignatureId || null
  subject.value = d.subject || ''
  recip.setTags(d.recipient || '')
  recip.setCcTags(d.cc || '')
  body.value = d.body || ''
  formData.value = d.formData || {}
  formKey.value++  // 强制重建子组件，确保数据同步
  if (d.body) userEditedBody.value = true  // 防止模板watch覆盖恢复的body
  draft.isDirty.value = false
  draft.suppress.value = false
}

function handleClear() {
  draft.suppress.value = true
  selectedTemplateId.value = null
  selectedSignatureId.value = null
  subject.value = ''
  body.value = ''
  bodySource.value = ''
  userEditedBody.value = false
  formData.value = {}
  attachments.value = []
  recip.clearAll()
  draft.clear()
  draft.isDirty.value = false
  draft.suppress.value = false
}

// ── Dirty tracking ──
watch(
  [selectedTemplateId, selectedSignatureId, subject, recip.tags, recip.input, recip.ccTags, recip.ccInput, body, formData],
  () => {
    if (draft.suppress.value) return
    if (subject.value.trim() || recip.tags.value.length || recip.ccTags.value.length || body.value.trim() ||
        (formData.value.accounts || []).some(a => a.account || a.password || a.account_type)) {
      draft.isDirty.value = true
    }
  },
  { deep: true, flush: 'sync' }
)

// ── Route guard ──
draft.installRouteGuard(getFormState)

// ── Send ──

async function handleSend() {
  if (sending.value) return
  if (recip.error.value) { message.warning('收件人邮箱格式不正确'); return }
  if (recip.ccError.value) { message.warning(recip.ccError.value); return }
  sending.value = true
  try {
    const payload = {
      email_type: 'account',
      recipient: recip.joinTags(),
      cc: recip.joinCcTags(),
      subject: subject.value,
      body: body.value,
      template_id: selectedTemplateId.value || null,
      signature_id: selectedSignatureId.value || null,
      accounts: (formData.value.accounts || []).map(a => ({
        account: a.account, password: a.password, account_type: a.account_type,
      })),
      subscriptions: [],
    }
    // Attachments
    const files = rteRef.value?.getAttachments() || []
    if (files.length) {
      payload.attachments = await Promise.all(files.map(f =>
        new Promise(resolve => {
          const reader = new FileReader()
          reader.onload = e => resolve({ filename: f.name, content_base64: e.target.result.split(',')[1] })
          reader.readAsDataURL(f)
        })
      ))
    }
    await sendEmail(payload)
    message.success('邮件发送成功')

    // Record field histories
    history.addToHistory(FIELD_HISTORY_KEYS.subject, subject.value)
    recip.tags.value.forEach(t => history.addToHistory(FIELD_HISTORY_KEYS.recipient, t))
    recip.ccTags.value.forEach(t => history.addToHistory(FIELD_HISTORY_KEYS.cc, t))
    ;(formData.value.accounts || []).forEach(a => {
      if (a.account) history.addToHistory(FIELD_HISTORY_KEYS.account_name, a.account)
      if (a.account_type) history.addToHistory(FIELD_HISTORY_KEYS.account_type, a.account_type)
    })
    history.loadAll()

    handleClear()
  } catch (err) {
    message.error(err.response?.data?.detail || '发送失败')
  } finally {
    sending.value = false
  }
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// ── Lifecycle ──

onMounted(async () => {
  try {
    const [tRes, sRes] = await Promise.all([getTemplates(), getSignatures()])
    templates.value = tRes.data
    signatures.value = sRes.data
    autoSelectDefaultSignature()
  } catch { /* */ }
  history.loadAll()
  loadDraftIntoForm()
  draft.markReady()
  window.addEventListener('beforeunload', onBeforeUnload)
  document.addEventListener('click', onDocumentClick)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  document.removeEventListener('click', onDocumentClick)
})

function onBeforeUnload(e) {
  if (draft.isDirty.value) { e.preventDefault(); e.returnValue = '' }
}
</script>

<style scoped>
.business-page { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.title-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }
.title-actions { display: flex; align-items: center; gap: 8px; }
.page-title { font-size: 28px; font-weight: 700; letter-spacing: -0.4px; }

.form-field { margin-bottom: 20px; }
.field-label { display: block; font-size: 14px; font-weight: 500; color: #1d1d1f; margin-bottom: 6px; }
.field-wrapper { position: relative; }
.field-error { display: block; font-size: 12px; color: #d03050; margin-top: 4px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }

.pill-input-shell {
  display: flex; flex-wrap: wrap; align-items: center; gap: 4px;
  padding: 4px 8px; min-height: 40px; border: 1px solid #d0d0d0;
  border-radius: 8px; background: #fff; transition: border-color 0.2s;
}
.pill-input-shell:focus-within { border-color: #0071e3; }
.pill-input-shell.pill-input-error { border-color: #e53935; }
.pill-tag {
  display: inline-flex; align-items: center; gap: 3px; padding: 1px 8px;
  background: #e6f4ea; color: #1e8e3e; border-radius: 12px; font-size: 13px;
  line-height: 1.6; white-space: nowrap;
}
.pill-tag.editing { background: #e8f0fe; color: #1a73e8; }
.pill-tag-x { background: none; border: none; color: inherit; cursor: pointer; font-size: 14px; padding: 0; line-height: 1; opacity: 0.5; }
.pill-tag-x:hover { opacity: 1; }
.pill-edit-input { width: 180px; padding: 0 4px; font-size: 13px; border: none; outline: none; background: transparent; color: #1a73e8; }
.pill-auto { flex: 1; min-width: 120px; }
.pill-auto :deep(.n-input) { border: none !important; box-shadow: none !important; background: transparent !important; }

.history-dropdown {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 1000;
  margin-top: 4px; background: #fff; border: 1px solid #e0e0e0;
  border-radius: 10px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); max-height: 200px; overflow-y: auto;
}
.history-dropdown-item { padding: 8px 14px; cursor: pointer; font-size: 14px; color: #1d1d1f; transition: background 0.1s; }
.history-dropdown-item:hover { background: #f0f7ff; }
.history-dropdown-item:first-child { border-radius: 10px 10px 0 0; }
.history-dropdown-item:last-child { border-radius: 0 0 10px 10px; }
.history-dropdown-empty { padding: 12px 14px; font-size: 13px; color: #999; text-align: center; }

.preview-card { background: #fff; border-radius: 14px; padding: 20px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.preview-header { font-size: 12px; font-weight: 600; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
.preview-btn-row { margin-bottom: 24px; }

.preview-meta { background: #f8f9fa; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px; }
.preview-meta-row { display: flex; gap: 8px; font-size: 14px; line-height: 1.8; }
.preview-meta-label { color: #86868b; flex-shrink: 0; min-width: 48px; }
.preview-meta-val { color: #1d1d1f; }
.preview-meta-subject { font-weight: 600; }
.preview-pill { display: inline-block; padding: 1px 10px; margin: 2px 4px 2px 0; background: #e6f4ea; color: #1e8e3e; border-radius: 12px; font-size: 13px; }
.preview-body { font-size: 16px; line-height: 1.7; color: #1d1d1f; word-break: break-word; overflow-x: auto; }
.preview-body :deep(a) { color: #0071e3; }
.preview-body :deep(img) { max-width: 100%; }
.preview-body :deep(p) { margin: 0 0 8px; }
.preview-body :deep(ul), .preview-body :deep(ol) { padding-left: 20px; margin: 8px 0; }
.preview-empty { font-size: 14px; color: #86868b; text-align: center; padding: 20px 0; }
.preview-attachments { margin-top: 16px; padding-top: 16px; border-top: 1px solid #e0e0e0; }
.preview-attach-title { font-size: 13px; font-weight: 600; color: #86868b; margin-bottom: 8px; }
.preview-attach-item { font-size: 14px; color: #1d1d1f; padding: 4px 0; }
.preview-attach-size { color: #86868b; font-size: 12px; margin-left: 8px; }
.send-hint-line { font-size: 13px; line-height: 1.8; color: #fff; }
</style>
