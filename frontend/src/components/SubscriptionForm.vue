<template>
  <div class="form-section">
    <div class="section-label">订阅信息</div>
    <div class="form-row">
      <div class="form-col">
        <label class="field-label">订阅 ID *</label>
        <n-input v-model:value="local.subscription_id" placeholder="如：SUB-2024-001" size="large" />
      </div>
      <div class="form-col">
        <label class="field-label">订阅名称 *</label>
        <n-input v-model:value="local.subscription_name" placeholder="请输入订阅名称" size="large" />
      </div>
    </div>
    <div class="form-field">
      <label class="field-label">订阅类型 *</label>
      <n-input v-model:value="local.subscription_type" placeholder="如：高级版、企业版、试用版" size="large" />
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from "vue";
import { NInput } from "naive-ui";

const props = defineProps({ modelValue: Object });
const emit = defineEmits(["update:modelValue"]);

const local = reactive({
  subscription_id: props.modelValue?.subscription_id || "",
  subscription_name: props.modelValue?.subscription_name || "",
  subscription_type: props.modelValue?.subscription_type || "",
});

watch(local, (v) => emit("update:modelValue", { ...v }), { deep: true });
</script>
