import { ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useDialog } from 'naive-ui'

const PREFIX = 'mailswift_saved_draft_'

/**
 * 草稿暂存/加载/清除 + dirty 追踪 + 路由离开守卫
 * @param {string} emailType — 'account' | 'subscription' | 'high_priority'
 */
export function useDraft(emailType) {
  const dialog = useDialog()
  const isDirty = ref(false)
  const suppress = ref(true) // init 阶段抑制 dirty 标记

  function key() {
    return PREFIX + emailType
  }

  /** 将任意对象写入 localStorage 并清除 dirty 标记 */
  function save(state) {
    suppress.value = true
    try { localStorage.setItem(key(), JSON.stringify(state)) } catch { /* quota */ }
    isDirty.value = false
    suppress.value = false
  }

  /** 从 localStorage 加载草稿，无数据时返回 null */
  function load() {
    try {
      const raw = localStorage.getItem(key())
      return raw ? JSON.parse(raw) : null
    } catch { return null }
  }

  /** 删除当前类型的草稿 */
  function clear() {
    try { localStorage.removeItem(key()) } catch { /* */ }
  }

  /** 允许 dirty 追踪（init 完成后调用） */
  function markReady() {
    Promise.resolve().then(() => { suppress.value = false })
  }

  /**
   * 安装路由离开守卫。
   * @param {() => object} getFormState — 返回当前表单状态的工厂函数
   */
  function installRouteGuard(getFormState) {
    onBeforeRouteLeave((_to, _from, next) => {
      if (!isDirty.value) {
        next()
        return
      }
      dialog.warning({
        title: '未保存的更改',
        content: '当前草稿尚未暂存，离开后修改将丢失。是否暂存后再离开？',
        positiveText: '暂存并离开',
        negativeText: '不保存',
        onPositiveClick: () => {
          save(getFormState())
          next()
        },
        onNegativeClick: () => {
          clear()
          isDirty.value = false
          next()
        },
        onClose: () => {
          // 用户取消 — 停留在当前页
        },
      })
    })
  }

  return { isDirty, suppress, save, load, clear, markReady, installRouteGuard, key }
}
