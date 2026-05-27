<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-message-provider>
      <div class="app-shell">
        <header class="app-header">
          <div class="header-left">
            <span class="logo" @click="$router.push('/')">MailSwift</span>
          </div>
          <div class="header-right">
            <n-button text @click="$router.push('/settings')">
              <template #icon><n-icon><settings-outline /></n-icon></template>
            </n-button>
            <n-button text @click="$router.push('/history')">
              <template #icon><n-icon><list-outline /></n-icon></template>
            </n-button>
          </div>
        </header>
        <main class="app-main">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </main>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { NConfigProvider, NMessageProvider, NButton, NIcon } from "naive-ui";
import { SettingsOutline, ListOutline } from "@vicons/ionicons5";
import { zhCN, dateZhCN } from "naive-ui";

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
  gap: 4px;
  -webkit-app-region: no-drag;
}

.app-main {
  flex: 1;
  padding: 32px;
  max-width: 720px;
  margin: 0 auto;
  width: 100%;
}
</style>
