<template>
  <div class="home">
    <div class="page-title">发送邮件</div>

    <!-- Email type switcher -->
    <div class="type-switcher">
      <div
        class="type-card"
        :class="{ active: emailType === 'account' }"
        @click="emailType = 'account'"
      >
        <div class="type-icon">
          <n-icon size="24"><person-outline /></n-icon>
        </div>
        <div class="type-label">账号创建</div>
        <div class="type-desc">发送账号和密码信息</div>
      </div>
      <div
        class="type-card"
        :class="{ active: emailType === 'subscription' }"
        @click="emailType = 'subscription'"
      >
        <div class="type-icon">
          <n-icon size="24"><cube-outline /></n-icon>
        </div>
        <div class="type-label">订阅创建</div>
        <div class="type-desc">发送订阅信息</div>
      </div>
    </div>

    <!-- Subject & Recipient -->
    <div class="form-field">
      <label class="field-label">邮件标题 *</label>
      <n-input v-model:value="subject" placeholder="邮件标题" size="large" clearable />
    </div>

    <div class="form-row">
      <div class="form-col">
        <label class="field-label">收件人 *</label>
        <n-input v-model:value="recipient" placeholder="user@example.com" size="large" clearable />
      </div>
      <div class="form-col">
        <label class="field-label">抄送 CC</label>
        <n-input v-model:value="cc" placeholder="cc@example.com（多人用逗号分隔）" size="large" clearable />
      </div>
    </div>

    <!-- Dynamic form -->
    <AccountForm v-if="emailType === 'account'" v-model="formData" />
    <SubscriptionForm v-else v-model="formData" />

    <!-- Remark -->
    <div class="form-field">
      <label class="field-label">备注（选填）</label>
      <n-input
        v-model:value="remark"
        type="textarea"
        placeholder="附加说明..."
        :autosize="{ minRows: 2, maxRows: 4 }"
        size="large"
      />
    </div>

    <!-- Editable body preview -->
    <div class="preview-card">
      <div class="preview-header">邮件正文（可编辑）</div>
      <n-input
        v-model:value="editableBody"
        type="textarea"
        :autosize="{ minRows: 6, maxRows: 20 }"
        size="large"
      />
    </div>

    <!-- Send -->
    <n-button
      type="primary"
      size="large"
      :loading="sending"
      :disabled="!canSend"
      block
      @click="handleSend"
    >
      <template #icon><n-icon><send-outline /></n-icon></template>
      发送邮件
    </n-button>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { NInput, NButton, NIcon, useMessage } from "naive-ui";
import { PersonOutline, CubeOutline, SendOutline } from "@vicons/ionicons5";
import AccountForm from "@/components/AccountForm.vue";
import SubscriptionForm from "@/components/SubscriptionForm.vue";
import { sendEmail } from "@/api";

const message = useMessage();
const emailType = ref("account");
const subject = ref("");
const recipient = ref("");
const cc = ref("");
const remark = ref("");
const sending = ref(false);
const editableBody = ref("");

const formData = ref({});

watch(emailType, () => {
  formData.value = {};
  remark.value = "";
});

const canSend = computed(() => {
  if (!subject.value || !recipient.value) return false;
  if (emailType.value === "account") {
    return formData.value.account && formData.value.password && formData.value.account_type;
  }
  return formData.value.subscriptions && formData.value.subscriptions.length > 0;
});

// Auto-generate body preview from form data
watch([formData, remark, emailType], () => {
  const lines = [];
  lines.push("您好，");
  lines.push("");
  if (emailType.value === "account") {
    const d = formData.value;
    if (d.account || d.password || d.account_type) {
      lines.push("您的账号已创建完成，信息如下：");
      if (d.account) lines.push(`  账号：${d.account}`);
      if (d.password) lines.push(`  密码：${d.password}`);
      if (d.account_type) lines.push(`  类型：${d.account_type}`);
    }
  } else {
    const subs = formData.value.subscriptions;
    if (subs && subs.length > 0) {
      lines.push("您的订阅已创建完成，信息如下：");
      subs.forEach((s, i) => {
        if (s.subscription_id || s.subscription_name) {
          lines.push(`  ${i + 1}. ${s.subscription_id || "-"} - ${s.subscription_name || "-"}`);
        }
      });
    }
  }
  if (remark.value) lines.push(`\n${remark.value}`);
  editableBody.value = lines.join("\n");
}, { deep: true, immediate: true });

async function handleSend() {
  sending.value = true;
  try {
    const payload = {
      email_type: emailType.value,
      recipient: recipient.value,
      cc: cc.value,
      subject: subject.value,
      remark: remark.value,
    };
    if (emailType.value === "account") {
      Object.assign(payload, {
        account: formData.value.account,
        password: formData.value.password,
        account_type: formData.value.account_type,
      });
    } else {
      payload.subscriptions = (formData.value.subscriptions || []).map((s) => ({
        subscription_id: s.subscription_id,
        subscription_name: s.subscription_name,
      }));
    }
    // Use the user-edited body
    payload.body = editableBody.value;
    await sendEmail(payload);
    message.success("邮件发送成功");
  } catch (err) {
    message.error(err.response?.data?.detail || "发送失败");
  } finally {
    sending.value = false;
  }
}
</script>

<style scoped>
.home {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.4px;
  margin-bottom: 28px;
}

.type-switcher {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 28px;
}

.type-card {
  padding: 20px;
  border-radius: 14px;
  border: 2px solid transparent;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.type-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.type-card.active {
  border-color: #0071e3;
  background: #f0f7ff;
}

.type-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #f5f5f7;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  color: #6e6e73;
}

.type-card.active .type-icon {
  background: #0071e3;
  color: #fff;
}

.type-label {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.type-desc {
  font-size: 13px;
  color: #86868b;
}

.form-field {
  margin-bottom: 20px;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin-bottom: 6px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.preview-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.preview-header {
  font-size: 12px;
  font-weight: 600;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}
</style>
