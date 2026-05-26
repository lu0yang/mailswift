<template>
  <div class="settings">
    <n-button text size="small" @click="$router.push('/')" class="back-btn">
      <template #icon><n-icon><arrow-back-outline /></n-icon></template>
      <span style="font-size:14px">返回</span>
    </n-button>

    <div class="page-title">邮箱凭据配置</div>

    <div class="settings-card">
      <div class="card-icon">
        <n-icon size="28" color="#0071e3"><lock-closed-outline /></n-icon>
      </div>

      <div class="form-field">
        <label class="field-label">Outlook 邮箱</label>
        <n-input
          v-model:value="emailAddress"
          placeholder="yourname@contoso.com"
          size="large"
          clearable
        />
      </div>

      <div class="form-field">
        <label class="field-label">邮箱密码 / 应用专用密码</label>
        <n-input
          v-model:value="password"
          type="password"
          show-password-on="click"
          placeholder="输入密码"
          size="large"
        />
      </div>

      <n-button
        type="primary"
        size="large"
        :loading="saving"
        block
        @click="handleSave"
      >
        保存凭据
      </n-button>

      <div v-if="statusText" class="status-bar">
        <span class="status-dot" :class="statusType"></span>
        {{ statusText }}
      </div>
    </div>

    <div class="tip-card">
      <n-icon size="18" color="#0071e3"><bulb-outline /></n-icon>
      <span>建议使用 Outlook 应用专用密码，而非主密码，更安全且可单独吊销。</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { NInput, NButton, NIcon, useMessage } from "naive-ui";
import { ArrowBackOutline, LockClosedOutline, BulbOutline } from "@vicons/ionicons5";
import { getSettings, updateSettings } from "@/api";

const message = useMessage();
const emailAddress = ref("");
const password = ref("");
const saving = ref(false);
const statusText = ref("");
const statusType = ref("");

onMounted(async () => {
  try {
    const { data } = await getSettings();
    emailAddress.value = data.email_address;
    if (data.password_masked) {
      statusText.value = `已配置  |  上次更新：${data.updated_at?.slice(0, 10) || "-"}`;
      statusType.value = "success";
    }
  } catch {
    // settings not yet created
  }
});

async function handleSave() {
  if (!emailAddress.value) {
    message.warning("请输入邮箱地址");
    return;
  }
  saving.value = true;
  try {
    await updateSettings({
      email_address: emailAddress.value,
      password: password.value,
    });
    message.success("凭据已保存");
    statusText.value = "已配置";
    statusType.value = "success";
    password.value = "";
  } catch (err) {
    message.error(err.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
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

.back-btn {
  margin-bottom: 12px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.4px;
  margin-bottom: 28px;
}

.settings-card {
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  text-align: center;
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: #f0f7ff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
}

.form-field {
  margin-bottom: 18px;
  text-align: left;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin-bottom: 6px;
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

.status-dot.success {
  background: #34c759;
}

.tip-card {
  margin-top: 16px;
  padding: 14px 18px;
  background: #f0f7ff;
  border-radius: 10px;
  font-size: 13px;
  color: #424245;
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
