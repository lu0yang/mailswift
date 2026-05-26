<template>
  <div class="settings">
    <n-button text size="small" @click="$router.push('/')" class="back-btn">
      <template #icon><n-icon><arrow-back-outline /></n-icon></template>
      <span style="font-size:14px">返回</span>
    </n-button>

    <div class="page-title">邮箱凭据配置</div>

    <n-tabs type="line" animated>
      <!-- SMTP Tab -->
      <n-tab-pane name="smtp" tab="SMTP 配置">
        <div class="settings-card">
          <div class="form-row">
            <div class="form-col smtp-host">
              <label class="field-label">SMTP 服务器</label>
              <n-input v-model:value="smtpHost" size="large" clearable />
            </div>
            <div class="form-col smtp-port">
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
          <n-button type="primary" size="large" :loading="saving" block @click="handleSave">
            保存凭据
          </n-button>
          <div v-if="statusText" class="status-bar">
            <span class="status-dot" :class="statusType"></span>
            {{ statusText }}
          </div>
        </div>
      </n-tab-pane>

      <!-- Account template tab -->
      <n-tab-pane name="account" tab="账号邮件模板">
        <div class="template-card">
          <div class="template-hints">
            可用变量：<code>{account}</code> <code>{password}</code> <code>{account_type}</code> <code>{remark}</code>
          </div>
          <n-input
            v-model:value="accountTemplate"
            type="textarea"
            :autosize="{ minRows: 8, maxRows: 20 }"
            placeholder="账号邮件模板..."
            size="large"
          />
        </div>
      </n-tab-pane>

      <!-- Subscription template tab -->
      <n-tab-pane name="subscription" tab="订阅邮件模板">
        <div class="template-card">
          <div class="template-hints">
            可用变量：<code>{subscription_list}</code> <code>{remark}</code>
          </div>
          <n-input
            v-model:value="subscriptionTemplate"
            type="textarea"
            :autosize="{ minRows: 8, maxRows: 20 }"
            placeholder="订阅邮件模板..."
            size="large"
          />
        </div>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { NInput, NInputNumber, NButton, NIcon, NTabs, NTabPane, useMessage } from "naive-ui";
import { ArrowBackOutline } from "@vicons/ionicons5";
import { getSettings, updateSettings } from "@/api";

const message = useMessage();
const smtpHost = ref("mail.21vianet.com");
const smtpPort = ref(587);
const emailAddress = ref("");
const password = ref("");
const accountTemplate = ref("");
const subscriptionTemplate = ref("");
const saving = ref(false);
const statusText = ref("");
const statusType = ref("");

onMounted(async () => {
  try {
    const { data } = await getSettings();
    smtpHost.value = data.smtp_host || "mail.21vianet.com";
    smtpPort.value = data.smtp_port || 587;
    emailAddress.value = data.email_address;
    accountTemplate.value = data.account_template;
    subscriptionTemplate.value = data.subscription_template;
    if (data.password_masked) {
      statusText.value = `已配置  |  上次更新：${data.updated_at?.slice(0, 10) || "-"}`;
      statusType.value = "success";
    }
  } catch {
    // not yet configured
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
      smtp_host: smtpHost.value,
      smtp_port: smtpPort.value,
      email_address: emailAddress.value,
      password: password.value,
      account_template: accountTemplate.value,
      subscription_template: subscriptionTemplate.value,
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
  margin-bottom: 20px;
}

.settings-card {
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.form-row {
  display: flex;
  gap: 12px;
  margin-bottom: 18px;
}

.form-col.smtp-host {
  flex: 3;
}

.form-col.smtp-port {
  flex: 1;
}

.form-field {
  margin-bottom: 18px;
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

.template-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.template-hints {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 12px;
}

.template-hints code {
  background: #f0f7ff;
  color: #0071e3;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
</style>
