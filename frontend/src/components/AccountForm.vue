<template>
  <div class="form-section">
    <div class="section-label">账号信息</div>
    <div class="form-row">
      <div class="form-col">
        <label class="field-label">账号 *</label>
        <n-input v-model:value="local.account" placeholder="请输入账号" size="large" />
      </div>
      <div class="form-col">
        <label class="field-label">密码 *</label>
        <n-input
          v-model:value="local.password"
          type="password"
          show-password-on="click"
          placeholder="请输入密码"
          size="large"
        />
      </div>
    </div>
    <div class="form-field">
      <label class="field-label">账户类型 *</label>
      <n-select
        v-model:value="local.account_type"
        :options="accountTypeOptions"
        placeholder="请选择账户类型"
        size="large"
      />
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from "vue";
import { NInput, NSelect } from "naive-ui";

const props = defineProps({ modelValue: Object });
const emit = defineEmits(["update:modelValue"]);

const accountTypeOptions = [
  { label: "Devops", value: "Devops" },
  { label: "Nodevops", value: "Nodevops" },
];

const local = reactive({
  account: props.modelValue?.account || "",
  password: props.modelValue?.password || "",
  account_type: props.modelValue?.account_type || "",
});

watch(local, (v) => emit("update:modelValue", { ...v }), { deep: true });
</script>

<style scoped>
.form-section {
  margin-bottom: 24px;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.form-field {
  margin-bottom: 0;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin-bottom: 6px;
}
</style>
