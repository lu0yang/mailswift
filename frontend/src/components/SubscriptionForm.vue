<template>
  <div class="form-section">
    <div class="section-header">
      <span class="section-label">订阅信息 *</span>
      <n-button size="tiny" type="primary" text @click="addSubscription">
        <template #icon><n-icon><add-outline /></n-icon></template>
        添加订阅
      </n-button>
    </div>

    <div v-if="local.subscriptions.length === 0" class="empty-hint">
      暂无订阅，请点击"添加订阅"
    </div>

    <TransitionGroup name="list">
      <div
        v-for="(sub, index) in local.subscriptions"
        :key="sub._key"
        class="subscription-row"
      >
        <div class="sub-index">{{ index + 1 }}</div>
        <div class="sub-fields">
          <n-input
            v-model:value="sub.subscription_id"
            placeholder="订阅 ID"
            size="large"
          />
          <n-input
            v-model:value="sub.subscription_name"
            placeholder="订阅名称"
            size="large"
          />
        </div>
        <n-button text type="error" size="small" @click="removeSubscription(index)">
          <template #icon><n-icon><close-outline /></n-icon></template>
        </n-button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { reactive, watch, ref } from "vue";
import { NInput, NButton, NIcon } from "naive-ui";
import { AddOutline, CloseOutline } from "@vicons/ionicons5";

const props = defineProps({ modelValue: Object });
const emit = defineEmits(["update:modelValue"]);

let keyCounter = ref(0);

const local = reactive({
  subscriptions: (props.modelValue?.subscriptions || []).map((s) => ({
    subscription_id: s.subscription_id || "",
    subscription_name: s.subscription_name || "",
    _key: ++keyCounter.value,
  })),
});

watch(local, (v) => {
  const clean = v.subscriptions.map(({ subscription_id, subscription_name }) => ({
    subscription_id,
    subscription_name,
  }));
  emit("update:modelValue", { subscriptions: clean });
}, { deep: true });

function addSubscription() {
  local.subscriptions.push({
    subscription_id: "",
    subscription_name: "",
    _key: ++keyCounter.value,
  });
}

function removeSubscription(index) {
  local.subscriptions.splice(index, 1);
}
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

.subscription-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.sub-index {
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

.sub-fields {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
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
