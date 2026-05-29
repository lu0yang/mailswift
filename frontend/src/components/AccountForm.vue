<template>
  <div class="form-section">
    <div class="section-header">
      <span class="section-label">账号信息 *</span>
      <n-button size="tiny" type="primary" text @click="addAccount">
        <template #icon><n-icon><add-outline /></n-icon></template>
        添加账号
      </n-button>
    </div>

    <div v-if="local.accounts.length === 0" class="empty-hint">
      暂无账号，请点击"添加账号"
    </div>

    <TransitionGroup name="list">
      <div
        v-for="(acct, index) in local.accounts"
        :key="acct._key"
        class="account-row"
      >
        <div class="account-index">{{ index + 1 }}</div>
        <div class="account-fields">
          <n-input
            v-model:value="acct.account"
            placeholder="账号"
            size="large"
          />
          <n-input
            v-model:value="acct.password"
            type="password"
            show-password-on="click"
            placeholder="密码"
            size="large"
          />
          <n-select
            v-model:value="acct.account_type"
            :options="accountTypeOptions"
            placeholder="账户类型"
            size="large"
          />
        </div>
        <n-button text type="error" size="small" @click="removeAccount(index)">
          <template #icon><n-icon><close-outline /></n-icon></template>
        </n-button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { reactive, watch, nextTick } from "vue";
import { NInput, NSelect, NButton, NIcon } from "naive-ui";
import { AddOutline, CloseOutline } from "@vicons/ionicons5";

const props = defineProps({ modelValue: Object });
const emit = defineEmits(["update:modelValue"]);

let keyCounter = 0;

const accountTypeOptions = [
  { label: "DevOps", value: "DevOps" },
  { label: "DevOps NonRestricted", value: "DevOps NonRestricted" },
];

let suppressEmit = false;

const local = reactive({
  accounts: (props.modelValue?.accounts || []).map((a) => ({
    account: a.account || "",
    password: a.password || "",
    account_type: a.account_type || "",
    _key: ++keyCounter,
  })),
});

if (local.accounts.length === 0) {
  local.accounts.push({
    account: "",
    password: "",
    account_type: "",
    _key: ++keyCounter,
  });
}

watch(local, () => {
  if (suppressEmit) return;
  const clean = local.accounts.map(({ account, password, account_type }) => ({
    account,
    password,
    account_type,
  }));
  emit("update:modelValue", { accounts: clean });
}, { deep: true });

function addAccount() {
  local.accounts.push({
    account: "",
    password: "",
    account_type: "",
    _key: ++keyCounter,
  });
}

function removeAccount(index) {
  local.accounts.splice(index, 1);
}

// Sync when parent clears form data (keep-alive scenario)
watch(() => props.modelValue?.accounts?.length, (len) => {
  if (len === 0 && local.accounts.length > 0) {
    suppressEmit = true;
    local.accounts.splice(0, local.accounts.length, {
      account: "", password: "", account_type: "", _key: ++keyCounter,
    });
    nextTick(() => { suppressEmit = false; });
  }
});
</script>

<style scoped>
.form-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.empty-hint {
  padding: 20px;
  text-align: center;
  color: #86868b;
  font-size: 14px;
  background: #fafafa;
  border-radius: 10px;
}

.account-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.account-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #86868b;
  flex-shrink: 0;
}

.account-fields {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.list-enter-active,
.list-leave-active {
  transition: all 0.2s ease;
}

.list-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
