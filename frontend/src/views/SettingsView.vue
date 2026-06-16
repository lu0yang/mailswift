<template>
  <div class="settings">
    <n-button text size="small" @click="$router.push('/')" class="back-btn">
      <template #icon><SvgIcon name="arrow-back" /></template>
      <span style="font-size:14px">返回</span>
    </n-button>

    <div class="page-title">设置</div>

    <div class="info-card">
      <div class="info-row">
        <span class="info-label">登录邮箱</span>
        <span class="info-value">{{ userEmail }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">显示名称</span>
        <span class="info-value">{{ userDisplayName }}</span>
      </div>
      <div class="info-hint">
        密码仅在本次浏览器会话中保存，关闭标签页后需重新登录。
      </div>
    </div>

    <div class="danger-zone">
      <h3 class="danger-title">重置数据</h3>
      <p class="danger-desc">删除我的所有模板、签名和发送记录（公共模板不受影响）</p>
      <n-button type="error" @click="handleReset" :loading="resetting">
        重置我的数据
      </n-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { NButton, useMessage, useDialog } from "naive-ui";
import SvgIcon from "@/components/SvgIcon.vue";
import { getMe, resetApp } from "@/api";

const message = useMessage();
const dialog = useDialog();
const userEmail = ref("");
const userDisplayName = ref("");
const resetting = ref(false);

onMounted(async () => {
  try {
    const { data } = await getMe();
    userEmail.value = data.email;
    userDisplayName.value = data.display_name;
  } catch { /* ignore */ }
});

async function handleReset() {
  dialog.warning({
    title: "确认重置",
    content: "将删除您的所有模板、签名和发送记录，此操作不可撤销。",
    positiveText: "确认重置",
    negativeText: "取消",
    onPositiveClick: async () => {
      resetting.value = true;
      try {
        await resetApp();
        message.success("数据已重置");
      } catch {
        message.error("重置失败");
      }
      resetting.value = false;
    },
  });
}
</script>

<style scoped>
.settings { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.back-btn { margin-bottom: 12px; }

.page-title {
  font-size: 28px; font-weight: 700; letter-spacing: -0.4px; margin-bottom: 24px;
}

.info-card {
  background: #fff; border-radius: 12px; padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04); margin-bottom: 24px;
}

.info-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 0; border-bottom: 1px solid #f5f5f7;
}

.info-label { font-size: 14px; color: #86868b; }
.info-value { font-size: 14px; color: #1d1d1f; font-weight: 500; }

.info-hint {
  font-size: 13px; color: #a1a1a6; margin-top: 12px; text-align: center;
}

.danger-zone {
  background: #fff; border-radius: 12px; padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.danger-title { font-size: 16px; color: #ff3b30; margin-bottom: 8px; }
.danger-desc { font-size: 13px; color: #86868b; margin-bottom: 16px; }
</style>
