<template>
  <div class="form-section">
    <div class="section-header">
      <span class="section-label">订阅信息 *</span>
      <n-button size="tiny" type="primary" text @click="addSubscription">
        <template #icon><SvgIcon name="add" /></template>
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
          <div class="field-wrapper">
            <n-input
              v-model:value="sub.subscription_id"
              placeholder="订阅 ID"
              size="large"
              :input-props="{ autocomplete: 'off' }"
              @focus="openDropdown(index, 'sub_id')"
              @blur="closeDropdownDelayed()"
            />
            <div v-if="dropdownRow === index && dropdownField === 'sub_id' && filteredSubIdHistory.length" class="history-dropdown">
              <div v-for="item in filteredSubIdHistory" :key="item" class="history-dropdown-item" @mousedown.prevent="selectSubId(item)">
                {{ item }}
              </div>
            </div>
          </div>
          <div class="field-wrapper">
            <n-input
              v-model:value="sub.subscription_name"
              placeholder="订阅名称"
              size="large"
              :input-props="{ autocomplete: 'off' }"
              @focus="openDropdown(index, 'sub_name')"
              @blur="closeDropdownDelayed()"
            />
            <div v-if="dropdownRow === index && dropdownField === 'sub_name' && filteredSubNameHistory.length" class="history-dropdown">
              <div v-for="item in filteredSubNameHistory" :key="item" class="history-dropdown-item" @mousedown.prevent="selectSubName(item)">
                {{ item }}
              </div>
            </div>
          </div>
        </div>
        <n-button text type="error" size="small" @click="removeSubscription(index)">
          <template #icon><SvgIcon name="close" /></template>
        </n-button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { reactive, computed, watch, nextTick, ref, onMounted, onBeforeUnmount } from "vue";
import { NInput, NButton } from "naive-ui";
import SvgIcon from "@/components/SvgIcon.vue";

const props = defineProps({ modelValue: Object });
const emit = defineEmits(["update:modelValue"]);

let keyCounter = 0;

let suppressEmit = false;

const local = reactive({
  subscriptions: (props.modelValue?.subscriptions || []).map((s) => ({
    subscription_id: s.subscription_id || "",
    subscription_name: s.subscription_name || "",
    _key: ++keyCounter,
  })),
});

// Auto-add one empty row on mount if none exist
if (local.subscriptions.length === 0) {
  local.subscriptions.push({ subscription_id: "", subscription_name: "", _key: ++keyCounter });
}

watch(local, (v) => {
  if (suppressEmit) return;
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
    _key: ++keyCounter,
  });
}

function removeSubscription(index) {
  local.subscriptions.splice(index, 1);
}

// Sync with parent formData (draft restore / clear)
watch(() => props.modelValue?.subscriptions, (subs) => {
  if (!subs || subs.length === 0) {
    if (local.subscriptions.length > 0) {
      suppressEmit = true;
      local.subscriptions.splice(0, local.subscriptions.length, {
        subscription_id: "", subscription_name: "", _key: ++keyCounter,
      });
      nextTick(() => { suppressEmit = false; });
    }
  } else {
    suppressEmit = true;
    local.subscriptions.splice(0, local.subscriptions.length, ...subs.map(s => ({
      subscription_id: s.subscription_id || "",
      subscription_name: s.subscription_name || "",
      _key: ++keyCounter,
    })));
    nextTick(() => { suppressEmit = false; });
  }
}, { deep: true });

// ── Subscription field history dropdown ────

const SUB_ID_HISTORY_KEY = "mailswift_history_subscription_id";
const SUB_NAME_HISTORY_KEY = "mailswift_history_subscription_name";
const subIdHistory = ref([]);
const subNameHistory = ref([]);
const dropdownRow = ref(-1);
const dropdownField = ref("");

function loadHistories() {
  try {
    subIdHistory.value = JSON.parse(localStorage.getItem(SUB_ID_HISTORY_KEY) || "[]");
    subNameHistory.value = JSON.parse(localStorage.getItem(SUB_NAME_HISTORY_KEY) || "[]");
  } catch { subIdHistory.value = []; subNameHistory.value = []; }
}

const filteredSubIdHistory = computed(() => {
  const acct = dropdownRow.value >= 0 ? local.subscriptions[dropdownRow.value] : null;
  if (!acct) return [];
  const val = (acct.subscription_id || "").trim().toLowerCase();
  if (!val) return subIdHistory.value;
  return subIdHistory.value.filter((s) => s.toLowerCase().includes(val));
});

const filteredSubNameHistory = computed(() => {
  const acct = dropdownRow.value >= 0 ? local.subscriptions[dropdownRow.value] : null;
  if (!acct) return [];
  const val = (acct.subscription_name || "").trim().toLowerCase();
  if (!val) return subNameHistory.value;
  return subNameHistory.value.filter((s) => s.toLowerCase().includes(val));
});

let hideTimer = null;
function openDropdown(index, field) {
  clearTimeout(hideTimer);
  loadHistories();
  dropdownRow.value = index;
  dropdownField.value = field;
}
function closeDropdownDelayed() {
  clearTimeout(hideTimer);
  hideTimer = setTimeout(() => { dropdownRow.value = -1; }, 200);
}
function selectSubId(item) {
  if (dropdownRow.value >= 0) local.subscriptions[dropdownRow.value].subscription_id = item;
  dropdownRow.value = -1;
}
function selectSubName(item) {
  if (dropdownRow.value >= 0) local.subscriptions[dropdownRow.value].subscription_name = item;
  dropdownRow.value = -1;
}

function onDocClick(e) {
  if (e.target.closest(".field-wrapper")) return;
  dropdownRow.value = -1;
}

onMounted(() => {
  loadHistories();
  document.addEventListener("click", onDocClick);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", onDocClick);
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

.field-wrapper {
  position: relative;
}

.history-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 1000;
  margin-top: 4px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.1);
  max-height: 200px;
  overflow-y: auto;
}

.history-dropdown-item {
  padding: 8px 14px;
  cursor: pointer;
  font-size: 14px;
  color: #1d1d1f;
  transition: background 0.1s;
}

.history-dropdown-item:hover {
  background: #f0f7ff;
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
