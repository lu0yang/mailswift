<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-dialog-provider>
    <n-message-provider>
      <div class="app-shell">
        <header class="app-header">
          <div class="header-left">
            <span class="logo" @click="$router.push('/')">MailSwift</span>
          </div>
          <div class="header-right">
            <n-popover trigger="click" placement="bottom-end" :width="260">
              <template #trigger>
                <div class="account-status">
                  <span class="status-dot" :class="accountClass"></span>
                  <span class="status-text">{{ accountLabel }}</span>
                </div>
              </template>
              <div class="account-switcher">
                <div class="switcher-title">切换账户</div>
                <div
                  v-for="acct in accounts"
                  :key="acct.id"
                  class="switcher-item"
                  :class="{ active: acct.id === accountId }"
                  @click="handleSwitchAccount(acct)"
                >
                  <span class="switcher-dot" :class="acct.is_active ? 'active-dot' : ''"></span>
                  <span class="switcher-email">{{ acct.email_address }}</span>
                  <span v-if="acct.id === accountId" class="switcher-check">✓</span>
                </div>
                <div v-if="!accounts.length" class="switcher-empty">暂无已保存的账户</div>
                <div class="switcher-footer">
                  <n-button text size="tiny" @click="$router.push('/settings')">管理账户</n-button>
                </div>
              </div>
            </n-popover>
            <n-button text @click="$router.push('/settings')">
              <template #icon><SvgIcon name="settings" /></template>
            </n-button>
            <n-button text @click="$router.push('/history')">
              <template #icon><SvgIcon name="list" /></template>
            </n-button>
          </div>
        </header>
        <main class="app-main">
          <router-view />
        </main>
      </div>
    </n-message-provider>
    </n-dialog-provider>
  </n-config-provider>
</template>

<script setup>
import { ref, computed, provide, onMounted } from "vue";
import { NConfigProvider, NDialogProvider, NMessageProvider, NButton, NPopover } from "naive-ui";
import { zhCN, dateZhCN } from "naive-ui";
import SvgIcon from "@/components/SvgIcon.vue";
import { getSettings, testConnection, getAccounts, switchAccount } from "@/api";

const accountEmail = ref("");
const accountExpired = ref(false);
const accountId = ref(0);
const accounts = ref([]);
const switching = ref(false);

const accountClass = computed(() => {
  if (!accountEmail.value) return "none";
  if (accountExpired.value) return "expired";
  return "ok";
});

const accountLabel = computed(() => {
  if (!accountEmail.value) return "未登录";
  if (accountExpired.value) return "凭据已过期";
  return accountEmail.value;
});

async function refreshAccount() {
  try {
    const { data } = await getSettings();
    if (data.email_address && data.password_masked) {
      accountEmail.value = data.email_address;
      accountId.value = data.id || 0;
      try {
        await testConnection();
        accountExpired.value = false;
      } catch {
        accountExpired.value = true;
      }
    } else {
      accountEmail.value = "";
      accountId.value = 0;
      accountExpired.value = false;
    }
  } catch {
    accountEmail.value = "";
    accountId.value = 0;
    accountExpired.value = false;
  }
  // Also load all accounts for the switcher
  try {
    const { data } = await getAccounts();
    accounts.value = data || [];
  } catch { accounts.value = []; }
}

async function handleSwitchAccount(acct) {
  if (acct.id === accountId.value || switching.value) return;
  switching.value = true;
  try {
    await switchAccount(acct.id);
    await refreshAccount();
    window.dispatchEvent(new Event("account-changed"));
  } catch { /* ignore */ }
  switching.value = false;
}

provide("refreshAccount", refreshAccount);
provide("accountEmail", accountEmail);
provide("accountExpired", accountExpired);

onMounted(() => {
  refreshAccount();
});

const themeOverrides = {
  common: {
    primaryColor: "#0071e3",
    primaryColorHover: "#0077ed",
    borderRadius: "10px",
    fontSize: "15px",
  },
  Button: {
    colorPrimary: "#0071e3",
    colorHoverPrimary: "#0077ed",
    borderRadiusMedium: "10px",
  },
  Input: {
    borderRadius: "8px",
  },
};
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  background: #f5f5f7;
  color: #1d1d1f;
  -webkit-font-smoothing: antialiased;
}

.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
  -webkit-app-region: drag;
}

.header-left .logo {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.3px;
  color: #1d1d1f;
  cursor: pointer;
  user-select: none;
  -webkit-app-region: no-drag;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  -webkit-app-region: no-drag;
}

.account-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 16px;
  background: #f5f5f7;
  cursor: pointer;
  transition: background 0.2s;
  margin-right: 4px;
}

.account-status:hover {
  background: #e8e8ed;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.none { background: #a1a1a6; }
.status-dot.ok { background: #34c759; }
.status-dot.expired { background: #ff3b30; }

.status-text {
  font-size: 13px;
  font-weight: 500;
  color: #1d1d1f;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-main {
  flex: 1;
  padding: 32px;
  max-width: 720px;
  margin: 0 auto;
  width: 100%;
}

.account-switcher {
  padding: 4px 0;
}

.switcher-title {
  font-size: 13px;
  color: #86868b;
  padding: 4px 12px 8px;
}

.switcher-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
}

.switcher-item:hover {
  background: #f5f5f7;
}

.switcher-item.active {
  background: #e8f0fe;
}

.switcher-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #d0d0d0;
  flex-shrink: 0;
}

.switcher-dot.active-dot {
  background: #34c759;
}

.switcher-email {
  font-size: 14px;
  color: #1d1d1f;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.switcher-check {
  color: #0071e3;
  font-size: 14px;
}

.switcher-empty {
  font-size: 13px;
  color: #86868b;
  padding: 12px;
  text-align: center;
}

.switcher-footer {
  border-top: 1px solid #f0f0f0;
  margin-top: 4px;
  padding: 8px 12px 0;
}
</style>
