import { ref, computed, watch } from 'vue'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function useRecipients() {
  const tags = ref([])
  const input = ref('')
  const ccTags = ref([])
  const ccInput = ref('')
  const editIdx = ref(-1)
  const editCcIdx = ref(-1)

  function isValidEmail(str) {
    return EMAIL_RE.test(str.trim())
  }

  const error = computed(() => {
    if (!tags.value.length) return ''
    const bad = tags.value.filter((a) => !isValidEmail(a))
    if (bad.length) return `格式不正确：${bad.join('、')}`
    return ''
  })

  const ccError = computed(() => {
    if (!ccTags.value.length) return ''
    const bad = ccTags.value.filter((a) => !isValidEmail(a))
    if (bad.length) return `格式不正确：${bad.join('、')}`
    return ''
  })

  function addTag() {
    const val = input.value.trim()
    if (!val) return
    input.value = ''
    if (!tags.value.includes(val)) tags.value.push(val)
  }

  function addCcTag() {
    const val = ccInput.value.trim()
    if (!val) return
    ccInput.value = ''
    if (!ccTags.value.includes(val)) ccTags.value.push(val)
  }

  function joinTags() {
    return tags.value.join(',')
  }

  function joinCcTags() {
    return ccTags.value.join(',')
  }

  function setTags(str) {
    tags.value = str ? str.split(',').filter(Boolean) : []
  }

  function setCcTags(str) {
    ccTags.value = str ? str.split(',').filter(Boolean) : []
  }

  function clearAll() {
    tags.value = []
    input.value = ''
    ccTags.value = []
    ccInput.value = ''
  }

  /**
   * 域名覆盖修复：当用户输入 @ 后选择域名建议时，
   * 自动拼接回完整的邮箱地址。
   */
  function installDomainWatch(inputRef, domainsFn) {
    watch(inputRef, (val, oldVal) => {
      if (!val || !oldVal) return
      const oldAt = oldVal.indexOf('@')
      if (oldAt > 0 && val.startsWith('@') && domainsFn().includes(val)) {
        inputRef.value = oldVal.slice(0, oldAt) + val
      }
    })
  }

  return {
    tags, input, ccTags, ccInput,
    editIdx, editCcIdx,
    error, ccError,
    addTag, addCcTag,
    joinTags, joinCcTags,
    setTags, setCcTags,
    clearAll,
    installDomainWatch,
  }
}
