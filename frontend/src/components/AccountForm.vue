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
      <n-input v-model:value="local.account_type" placeholder="如：管理员、普通用户、访客" size="large" />
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from "vue";
import { NInput } from "naive-ui";

const props = defineProps({ modelValue: Object });
const emit = defineEmits(["update:modelValue"]);

const local = reactive({
  account: props.modelValue?.account || "",
  password: props.modelValue?.password || "",
  account_type: props.modelValue?.account_type || "",
});

watch(local, (v) => emit("update:modelValue", { ...v }), { deep: true });
</script>
