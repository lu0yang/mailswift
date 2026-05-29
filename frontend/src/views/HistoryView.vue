<template>
  <div class="history">
    <n-button text size="small" @click="$router.push('/')" class="back-btn">
      <template #icon><n-icon><arrow-back-outline /></n-icon></template>
      <span style="font-size:14px">返回</span>
    </n-button>

    <div class="page-title">发送记录</div>

    <!-- Filter tabs -->
    <div class="filter-tabs">
      <div
        v-for="tab in tabs"
        :key="tab.value"
        class="filter-tab"
        :class="{ active: filter === tab.value }"
        @click="filter = tab.value; fetchHistory()"
      >
        {{ tab.label }}
      </div>
    </div>

    <!-- Records -->
    <div class="records">
      <div
        v-for="item in items"
        :key="item.id"
        class="record-card"
        @click="toggleExpand(item.id)"
      >
        <div class="record-main">
          <div class="record-left">
            <div class="record-type-badge" :class="item.email_type">
              {{ item.email_type === 'account' ? '账号' : '订阅' }}
            </div>
            <span class="record-recipient">{{ item.subject || '（无标题）' }}</span>
          </div>
          <div class="record-right">
            <span class="record-status" :class="item.status">
              {{ item.status === 'success' ? '已发送' : '发送失败' }}
            </span>
            <span class="record-time">{{ formatTime(item.sent_at) }}</span>
          </div>
        </div>
        <div v-if="expandedId === item.id" class="record-detail">
          <div class="detail-row">
            <span class="detail-label">收件人</span>
            <span>{{ item.recipient }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">主题</span>
            <span>{{ item.subject || '（无标题）' }}</span>
          </div>
          <div v-if="item.error_message" class="detail-row error">
            <span class="detail-label">失败原因</span>
            <span>{{ item.error_message }}</span>
          </div>
          <n-button
            size="tiny"
            type="error"
            text
            @click.stop="handleDelete(item.id)"
          >
            删除此记录
          </n-button>
        </div>
      </div>

      <div v-if="loading" class="loading-hint">加载中…</div>
      <div v-else-if="items.length === 0" class="empty">
        暂无记录
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > pageSize" class="pagination">
      <n-button
        text
        :disabled="page <= 1"
        @click="page--; fetchHistory()"
      >
        上一页
      </n-button>
      <span class="page-info">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
      <n-button
        text
        :disabled="page >= Math.ceil(total / pageSize)"
        @click="page++; fetchHistory()"
      >
        下一页
      </n-button>
    </div>

    <div class="total-hint">共 {{ total }} 条记录</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated } from "vue";
import { NButton, NIcon, useMessage, useDialog } from "naive-ui";
import { ArrowBackOutline } from "@vicons/ionicons5";
import { getHistory, deleteHistory } from "@/api";

const message = useMessage();
const dialog = useDialog();
const filter = ref("");
const items = ref([]);
const page = ref(1);
const pageSize = 20;
const total = ref(0);
const loading = ref(false);
const expandedId = ref(null);

const tabs = [
  { label: "全部", value: "" },
  { label: "账号", value: "account" },
  { label: "订阅", value: "subscription" },
];

onMounted(() => fetchHistory());
onActivated(() => fetchHistory());

async function fetchHistory() {
  loading.value = true;
  try {
    const params = { page: page.value, page_size: pageSize };
    if (filter.value) params.email_type = filter.value;
    const { data } = await getHistory(params);
    items.value = data.items;
    total.value = data.total;
  } catch (err) {
    message.error("加载记录失败");
  } finally {
    loading.value = false;
  }
}

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id;
}

async function handleDelete(id) {
  dialog.warning({
    title: "确认删除",
    content: "确定要删除这条发送记录吗？此操作不可撤销。",
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await deleteHistory(id);
        message.success("已删除");
        fetchHistory();
      } catch {
        message.error("删除失败");
      }
    },
  });
}

function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
</script>

<style scoped>
.history {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.back-btn {
  margin-bottom: 12px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.4px;
  margin-bottom: 20px;
}

.filter-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.filter-tab {
  padding: 8px 18px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  background: #fff;
  color: #6e6e73;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.filter-tab:hover {
  color: #1d1d1f;
}

.filter-tab.active {
  background: #1d1d1f;
  color: #fff;
}

.records {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.record-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px 18px;
  cursor: pointer;
  transition: box-shadow 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.record-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.record-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.record-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.record-type-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
}

.record-type-badge.account {
  background: #f0f7ff;
  color: #0071e3;
}

.record-type-badge.subscription {
  background: #f3e8ff;
  color: #7c3aed;
}

.record-recipient {
  font-size: 14px;
  color: #1d1d1f;
}

.record-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.record-status {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 6px;
}

.record-status.success {
  background: #e8f8ed;
  color: #34c759;
}

.record-status.failed {
  background: #ffe5e5;
  color: #ff3b30;
}

.record-time {
  font-size: 13px;
  color: #86868b;
}

.record-detail {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.detail-row {
  display: flex;
  gap: 10px;
  font-size: 13px;
  margin-bottom: 6px;
  color: #424245;
}

.detail-row.error {
  color: #ff3b30;
}

.detail-label {
  font-weight: 500;
  color: #86868b;
  min-width: 56px;
}

.loading-hint {
  text-align: center;
  padding: 60px 0;
  color: #86868b;
  font-size: 14px;
}

.empty {
  text-align: center;
  padding: 60px 0;
  color: #86868b;
  font-size: 15px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
}

.page-info {
  font-size: 13px;
  color: #86868b;
}

.total-hint {
  text-align: center;
  font-size: 13px;
  color: #86868b;
  margin-top: 8px;
}
</style>
