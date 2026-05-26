import { createRouter, createWebHashHistory } from "vue-router";
import HomeView from "@/views/HomeView.vue";
import SettingsView from "@/views/SettingsView.vue";
import HistoryView from "@/views/HistoryView.vue";

const routes = [
  { path: "/", name: "home", component: HomeView },
  { path: "/settings", name: "settings", component: SettingsView },
  { path: "/history", name: "history", component: HistoryView },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
