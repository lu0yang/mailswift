import { createRouter, createWebHashHistory } from "vue-router";
import AccountView from "@/views/AccountView.vue";
import SubscriptionView from "@/views/SubscriptionView.vue";
import HighPriorityView from "@/views/HighPriorityView.vue";
import SettingsView from "@/views/SettingsView.vue";
import HistoryView from "@/views/HistoryView.vue";

const routes = [
  { path: "/", redirect: "/account" },
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

export default router;
