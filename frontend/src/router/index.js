import { createRouter, createWebHashHistory } from "vue-router";
import AccountView from "@/views/AccountView.vue";
import SubscriptionView from "@/views/SubscriptionView.vue";
import HighPriorityView from "@/views/HighPriorityView.vue";
import SettingsView from "@/views/SettingsView.vue";
import HistoryView from "@/views/HistoryView.vue";
import LoginView from "@/views/LoginView.vue";

const routes = [
  { path: "/", redirect: "/account" },
  { path: "/login", name: "login", component: LoginView },
  { path: "/account", name: "account", component: AccountView },
  { path: "/subscription", name: "subscription", component: SubscriptionView },
  { path: "/high-priority", name: "high-priority", component: HighPriorityView },
  { path: "/settings", name: "settings", component: SettingsView },
  { path: "/history", name: "history", component: HistoryView },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

router.beforeEach((to) => {
  const token = localStorage.getItem("mailswift_token");
  if (!token && to.name !== "login") {
    return { name: "login" };
  }
  if (token && to.name === "login") {
    return { name: "account" };
  }
});

export default router;
