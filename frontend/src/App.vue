<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-dialog-provider>
    <n-message-provider>
      <div class="app-shell">
        <header class="app-header">
          <div class="header-left">
            <span class="logo" @click="$router.push('/account')">MailSwift</span>
            <nav class="header-nav">
              <router-link to="/account" class="nav-link" active-class="nav-link--active">账号</router-link>
              <router-link to="/subscription" class="nav-link" active-class="nav-link--active">订阅</router-link>
              <router-link to="/high-priority" class="nav-link" active-class="nav-link--active">HP</router-link>
            </nav>
          </div>
          <div class="header-right">
            <div class="account-status">
              <span class="status-dot" :class="accountClass"></span>
              <span class="status-text">{{ accountLabel }}</span>
            </div>
            <n-button text @click="$router.push('/settings')">
              设置
            </n-button>
            <n-button text @click="$router.push('/history')">
              历史
            </n-button>
            <n-button text @click="handleLogout" style="color:#ff3b30">
              退出登录
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
import { ref, computed, provide, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { isLoggedIn, getMe, removeToken, getDomains, DEFAULT_DOMAINS } from "@/api";
import { NConfigProvider, NDialogProvider, NMessageProvider, NButton } from "naive-ui";
import { zhCN, dateZhCN } from "naive-ui";

const router = useRouter();

const userEmail = ref("");
const userDisplayName = ref("");

const accountLabel = computed(() => {
  return userDisplayName.value || userEmail.value || "未登录";
});

const accountClass = computed(() => {
  return userEmail.value ? "ok" : "none";
});

async function fetchUser() {
  try {
    const { data } = await getMe();
    userEmail.value = data.email;
    userDisplayName.value = data.display_name;
  } catch {
    userEmail.value = "";
    userDisplayName.value = "";
  }
}

function handleLogout() {
  removeToken();
  userEmail.value = "";
  userDisplayName.value = "";
  router.replace("/login");
}

provide("userEmail", userEmail);
provide("accountEmail", userEmail);

async function syncDomains() {
  try {
    const { data } = await getDomains();
    const custom = data.domains || [];
    const merged = [...new Set([...DEFAULT_DOMAINS, ...custom])];
    localStorage.setItem("mailswift_preset_domains", JSON.stringify(merged));
  } catch { /* */ }
}

onMounted(() => {
  if (isLoggedIn()) {
    fetchUser();
    syncDomains();
  }
});

// 监听路由变化：登录成功后跳转时重新获取用户信息
watch(() => router.currentRoute.value, (to) => {
  if (to.name !== "login" && isLoggedIn()) {
    fetchUser();
  }
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

.header-left {
  display: flex;
  align-items: center;
  gap: 24px;
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

.header-nav {
  display: flex;
  gap: 4px;
  -webkit-app-region: no-drag;
}

.nav-link {
  font-size: 14px;
  font-weight: 500;
  color: #6e6e73;
  text-decoration: none;
  padding: 4px 12px;
  border-radius: 6px;
  transition: all 0.15s;
}

.nav-link:hover {
  color: #1d1d1f;
  background: #f5f5f7;
}

.nav-link--active {
  color: #0071e3;
  background: #e8f0fe;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
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
</style>
