<template>
  <div class="form-section">
    <div class="section-header">
      <span class="section-label">账号信息 *</span>
      <n-button size="tiny" type="primary" text @click="addAccount">
        <template #icon><SvgIcon name="add" /></template>
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
          <div class="field-wrapper">
            <n-input
              v-model:value="acct.account"
              placeholder="账号"
              size="large"
              :input-props="{ autocomplete: 'off' }"
              @focus="openDropdown(index)"
              @blur="closeDropdownDelayed()"
            />
            <div v-if="dropdownRow === index && filteredAccountHistory.length" class="history-dropdown">
              <div
                v-for="item in filteredAccountHistory"
                :key="item"
                class="history-dropdown-item"
                @mousedown.prevent="selectAccount(item)"
              >
                {{ item }}
              </div>
            </div>
          </div>
          <n-input
            v-model:value="acct.password"
            type="password"
            show-password-on="click"
            placeholder="密码"
            size="large"
            :input-props="{ autocomplete: 'new-password' }"
          />
          <n-select
            v-model:value="acct.account_type"
            :options="accountTypeOptions"
            placeholder="账户类型"
            size="large"
          />
        </div>
        <n-button text type="error" size="small" @click="removeAccount(index)">
          <template #icon><SvgIcon name="close" /></template>
        </n-button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { reactive, computed, watch, nextTick, ref, onMounted, onBeforeUnmount } from "vue";
import { NInput, NSelect, NButton } from "naive-ui";
import SvgIcon from "@/components/SvgIcon.vue";

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

// Sync with parent formData (draft restore / clear)
watch(() => props.modelValue?.accounts, (accts) => {
  if (!accts || accts.length === 0) {
    // Parent cleared: reset to one empty row
    if (local.accounts.length > 0) {
      suppressEmit = true;
      local.accounts.splice(0, local.accounts.length, {
        account: "", password: "", account_type: "", _key: ++keyCounter,
      });
      nextTick(() => { suppressEmit = false; });
    }
  } else {
    // Parent set data (draft restore): sync into local
    suppressEmit = true;
    local.accounts.splice(0, local.accounts.length, ...accts.map(a => ({
      account: a.account || "",
      password: a.password || "",
      account_type: a.account_type || "",
      _key: ++keyCounter,
    })));
    nextTick(() => { suppressEmit = false; });
  }
}, { deep: true });

// ── Account name history dropdown ────

const ACCOUNT_HISTORY_KEY = "mailswift_history_account_name";
const accountHistory = ref([]);
const dropdownRow = ref(-1);

function loadAccountHistory() {
  try {
    const raw = localStorage.getItem(ACCOUNT_HISTORY_KEY);
    accountHistory.value = raw ? JSON.parse(raw) : [];
  } catch { accountHistory.value = []; }
}

const filteredAccountHistory = computed(() => {
  if (dropdownRow.value < 0) return [];
  const acct = local.accounts[dropdownRow.value];
  if (!acct) return [];
  const val = (acct.account || "").trim().toLowerCase();
  if (!val) return accountHistory.value;
  return accountHistory.value.filter((s) => s.toLowerCase().includes(val));
});

let hideTimer = null;
function openDropdown(index) {
  clearTimeout(hideTimer);
  loadAccountHistory();
  dropdownRow.value = index;
}
function closeDropdownDelayed() {
  clearTimeout(hideTimer);
  hideTimer = setTimeout(() => { dropdownRow.value = -1; }, 200);
}
function selectAccount(item) {
  if (dropdownRow.value >= 0) {
    local.accounts[dropdownRow.value].account = item;
  }
  dropdownRow.value = -1;
}

function onDocClick(e) {
  if (e.target.closest(".field-wrapper")) return;
  dropdownRow.value = -1;
}

onMounted(() => {
  loadAccountHistory();
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
