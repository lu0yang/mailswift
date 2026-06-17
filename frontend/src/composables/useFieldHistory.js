import { ref, computed } from 'vue'

export const FIELD_HISTORY_KEYS = {
  subject: 'mailswift_history_subject',
  recipient: 'mailswift_history_recipient',
  cc: 'mailswift_history_cc',
  account_name: 'mailswift_history_account_name',
  account_type: 'mailswift_history_account_type',
  subscription_id: 'mailswift_history_subscription_id',
  subscription_name: 'mailswift_history_subscription_name',
}

import { DEFAULT_DOMAINS } from '@/api'

const PRESET_KEY = 'mailswift_preset_domains'

export function useFieldHistory() {
  const subjectHistory = ref([])
  const recipientHistory = ref([])
  const ccHistory = ref([])

  function loadHistory(key) {
    try { return JSON.parse(localStorage.getItem(key) || '[]') } catch { return [] }
  }

  /** 往指定 key 的历史列表头部插入一条值（去重，上限 50） */
  function addToHistory(key, value) {
    if (!value || !value.trim()) return
    const history = loadHistory(key)
    const v = value.trim()
    const filtered = history.filter((h) => h !== v)
    filtered.unshift(v)
    if (filtered.length > 50) filtered.pop()
    try { localStorage.setItem(key, JSON.stringify(filtered)) } catch { /* */ }
  }

  function loadAll() {
    subjectHistory.value = loadHistory(FIELD_HISTORY_KEYS.subject)
    recipientHistory.value = loadHistory(FIELD_HISTORY_KEYS.recipient)
    ccHistory.value = loadHistory(FIELD_HISTORY_KEYS.cc)
  }

  // ── 预设域名 ──
  function loadPresetDomains() {
    try {
      const raw = localStorage.getItem(PRESET_KEY)
      return raw ? JSON.parse(raw) : [...DEFAULT_DOMAINS]
    } catch { return [...DEFAULT_DOMAINS] }
  }

  /**
   * 收件人/抄送的下拉选项：
   * - 无输入 → 显示全部历史
   * - 输入了 @ 且匹配域名 → 只显示域名补全建议
   * - 否则 → 按输入过滤历史
   */
  function filteredRecipientOptions(inputText) {
    return computed(() => {
      const val = (inputText.value || '').trim().toLowerCase()
      const atIdx = val.indexOf('@')
      if (atIdx >= 0) {
        const afterAt = val.slice(atIdx)
        const domains = loadPresetDomains()
        if (domains.some((d) => d === afterAt)) return []
        const matching = domains.filter((d) => d.startsWith(afterAt))
        if (matching.length) return matching
      }
      if (!val) return recipientHistory.value
      return recipientHistory.value.filter((e) => e.toLowerCase().includes(val))
    })
  }

  function filteredCcOptions(inputText) {
    return computed(() => {
      const val = (inputText.value || '').trim().toLowerCase()
      const atIdx = val.indexOf('@')
      if (atIdx >= 0) {
        const afterAt = val.slice(atIdx)
        const domains = loadPresetDomains()
        if (domains.some((d) => d === afterAt)) return []
        const matching = domains.filter((d) => d.startsWith(afterAt))
        if (matching.length) return matching
      }
      if (!val) return ccHistory.value
      return ccHistory.value.filter((e) => e.toLowerCase().includes(val))
    })
  }

  function filteredSubjectOptions(inputText) {
    return computed(() => {
      const val = (inputText.value || '').trim().toLowerCase()
      if (!val) return subjectHistory.value
      return subjectHistory.value.filter((s) => s.toLowerCase().includes(val))
    })
  }

  return {
    subjectHistory, recipientHistory, ccHistory,
    addToHistory, loadAll,
    loadPresetDomains,
    filteredRecipientOptions,
    filteredCcOptions,
    filteredSubjectOptions,
  }
}
