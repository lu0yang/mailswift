import { ref, computed } from 'vue'
import { getSignatures } from '@/api'

/**
 * 签名选择共享逻辑 — 所有发送页面复用。
 *
 * 用法:
 *   const { signatures, selectedSignatureId, signatureOptions,
 *           signatureHtml, load, init, autoSelectDefault, resetToDefault } = useSignature()
 *
 *   // onMounted 中
 *   await init()
 *
 *   // previewHtml computed 中
 *   html += signatureHtml.value
 *
 *   // 发送 payload 中
 *   signature_id: selectedSignatureId.value || null
 *
 *   // 切换模板/类型时
 *   resetToDefault()
 */
export function useSignature() {
  const signatures = ref([])
  const selectedSignatureId = ref(null)

  /** 供 n-select 使用的选项列表 */
  const signatureOptions = computed(() =>
    signatures.value.map((s) => ({
      label: s.is_default ? s.name + ' （默认）' : s.name,
      value: s.id,
    }))
  )

  /**
   * 根据选中的签名生成 HTML 片段，供 previewHtml 拼接。
   * 所有新签名已在前端保存时统一包裹 max-width:600px；
   * 保留检测是为了兼容数据库中旧签名。
   */
  const signatureHtml = computed(() => {
    if (!selectedSignatureId.value) return ''
    const sig = signatures.value.find((s) => s.id === selectedSignatureId.value)
    if (!sig?.content) return ''
    if (sig.content.includes('max-width:600px')) {
      return '<br>' + sig.content
    }
    return '<br><div style="max-width:600px;">' + sig.content + '</div>'
  })

  /** 加载签名列表 */
  async function load() {
    const { data } = await getSignatures()
    signatures.value = data
  }

  /** 自动选中默认签名（已有选中则跳过） */
  function autoSelectDefault() {
    if (selectedSignatureId.value) return
    const def = signatures.value.find((s) => s.is_default)
    if (def) selectedSignatureId.value = def.id
  }

  /** 加载列表 + 自动选默认，用于 onMounted 初始化 */
  async function init() {
    await load()
    autoSelectDefault()
  }

  /** 清空选中并重新自动选择默认（切换模板/邮件类型时调用） */
  function resetToDefault() {
    selectedSignatureId.value = null
    autoSelectDefault()
  }

  return {
    signatures,
    selectedSignatureId,
    signatureOptions,
    signatureHtml,
    load,
    init,
    autoSelectDefault,
    resetToDefault,
  }
}
