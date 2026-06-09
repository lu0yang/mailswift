<template>
  <div class="hp-form">
    <!-- Title preview -->
    <div class="hp-preview">
      <span class="hp-preview-label">邮件标题预览：</span>
      <span class="hp-preview-text">{{ titlePreview }}</span>
    </div>

    <!-- Row: Severity + Ticket ID -->
    <div class="hp-row">
      <div class="hp-field">
        <label class="hp-label">Severity *</label>
        <n-select v-model:value="local.severity" :options="severityOptions" placeholder="选择级别" size="large" />
      </div>
      <div class="hp-field">
        <label class="hp-label">Ticket ID *</label>
        <n-input v-model:value="local.ticket_id" placeholder="如 784021363" size="large" :input-props="{ autocomplete: 'off' }" />
      </div>
    </div>

    <!-- Row: Category + Title -->
    <div class="hp-row">
      <div class="hp-field">
        <label class="hp-label">Category *</label>
        <n-select v-model:value="local.category" :options="categoryOptions" placeholder="Network" size="large" tag filterable />
      </div>
      <div class="hp-field">
        <label class="hp-label">Title *</label>
        <n-input v-model:value="local.title" placeholder="事件描述" size="large" :input-props="{ autocomplete: 'off' }" />
      </div>
    </div>

    <!-- Date -->
    <div class="hp-field">
      <label class="hp-label">Date</label>
      <n-input v-model:value="local.date" placeholder="MM/DD/YYYY" size="large" :input-props="{ autocomplete: 'off' }" />
    </div>

    <!-- Current Status -->
    <div class="hp-field">
      <label class="hp-label">Current Status</label>
      <n-input v-model:value="local.current_status" placeholder="Initial" size="large" :input-props="{ autocomplete: 'off' }" />
    </div>

    <!-- Description -->
    <div class="hp-field">
      <label class="hp-label">Description *</label>
      <n-input v-model:value="local.description" type="textarea" :autosize="{ minRows: 3, maxRows: 8 }" placeholder="必填，描述事件详情" size="large" :input-props="{ autocomplete: 'off' }" />
    </div>

    <!-- Start Date & Time -->
    <div class="hp-field">
      <label class="hp-label">Start Date & Time *</label>
      <n-input v-model:value="local.start_datetime" placeholder="MM/DD/YYYY HH:MM" size="large" :input-props="{ autocomplete: 'off' }" />
      <span class="hp-hint">格式：Beijing Time(GMT+8) : MM/DD/YYYY HH:MM</span>
    </div>

    <!-- Impact -->
    <div class="hp-field">
      <label class="hp-label">Impact *</label>
      <n-input v-model:value="local.impact" placeholder="No impact" size="large" :input-props="{ autocomplete: 'off' }" />
    </div>

    <!-- Slot for Update field (HP UPDATED) -->
    <slot name="after-impact" />

    <!-- Operations Manager -->
    <div class="hp-field">
      <label class="hp-label">Operations Manager *</label>
      <div class="hp-mgr-bar">
        <span class="hp-mgr-team-label">团队：</span>
        <n-select v-model:value="activeTeamId" :options="teamOptions" size="small" style="width:180px" @update:value="onTeamSwitch" />
        <n-button text size="tiny" @click="renameTeam">✎ 重命名</n-button>
        <n-button text size="tiny" @click="teamPanelShow = true">管理团队</n-button>
      </div>
      <div class="hp-mgr-pills">
        <span v-for="(m, i) in local.managers" :key="i" class="hp-mgr-pill">
          {{ m.name }} &lt;{{ m.email }}&gt;
          <button class="hp-mgr-x" @click="removeManager(i)">×</button>
        </span>
        <n-button text size="tiny" type="primary" @click="addManagerRow" style="font-size:13px">+ 添加成员</n-button>
      </div>
    </div>

    <!-- Slot for Update field (HP MITIGATED, after Operations Manager) -->
    <slot name="after-operations" />

    <!-- Next Update (INITIAL only) -->
    <div v-if="local.status_prefix === 'INITIAL'" class="hp-field">
      <label class="hp-label">Next Update</label>
      <n-input v-model:value="local.next_update" placeholder="30 minutes" size="large" :input-props="{ autocomplete: 'off' }" />
    </div>

    <!-- Resolution (MITIGATED only) -->
    <div v-if="local.status_prefix === 'MITIGATED'" class="hp-field">
      <label class="hp-label">Resolution *</label>
      <n-input v-model:value="local.resolution" placeholder="如 Mitigated by itself." size="large" :input-props="{ autocomplete: 'off' }" />
    </div>

    <!-- End Date & Time (MITIGATED only) -->
    <div v-if="local.status_prefix === 'MITIGATED'" class="hp-field">
      <label class="hp-label">End Date &amp; Time *</label>
      <n-input v-model:value="local.end_datetime" placeholder="MM/DD/YYYY HH:MM" size="large" :input-props="{ autocomplete: 'off' }" />
      <span class="hp-hint">格式：Beijing Time(GMT+8) : MM/DD/YYYY HH:MM</span>
    </div>

    <!-- ── Modals ── -->

    <!-- Team management panel -->
    <n-modal v-model:show="teamPanelShow" title="管理团队" style="max-width:640px" preset="card">
      <div class="tm-panel">
        <div class="tm-list">
          <div v-for="team in teams" :key="team.id" class="tm-row" :class="{ active: team.id === activeTeamId }" @click="selectTeamInPanel(team.id)">
            <span class="tm-name">{{ team.name }}</span>
            <span class="tm-count">{{ team.managers.length }} 人</span>
            <n-button text size="tiny" @click.stop="renameTeamInPanel(team.id)">重命名</n-button>
            <n-button v-if="teams.length > 1" text size="tiny" type="error" @click.stop="deleteTeam(team.id)">删除</n-button>
          </div>
          <n-button text size="small" type="primary" @click="createTeam" style="margin-top:8px">+ 新建团队</n-button>
        </div>
        <n-divider />
        <div class="tm-members-title">
          {{ activeTeamName }} — 成员列表
          <n-button text size="tiny" type="primary" @click="addMemberToPanel">+ 添加</n-button>
        </div>
        <div v-for="(m, i) in editingManagers" :key="i" class="tm-member-row">
          <n-input v-model:value="m.name" placeholder="姓名" size="small" style="flex:1" />
          <n-input v-model:value="m.email" placeholder="邮箱" size="small" style="flex:2" />
          <n-button text size="tiny" type="error" @click="removeMemberFromPanel(i)">×</n-button>
        </div>
        <div v-if="editingManagers.length === 0" class="tm-empty">暂无成员，点击"添加"新增</div>
      </div>
      <template #footer>
        <n-button type="primary" @click="teamPanelShow = false">完成</n-button>
      </template>
    </n-modal>

    <!-- Rename dialog -->
    <n-modal v-model:show="renameShow" title="重命名团队" style="max-width:360px" preset="card">
      <n-input v-model:value="renameValue" placeholder="输入团队名称" size="large" />
      <template #footer>
        <n-button @click="renameShow = false">取消</n-button>
        <n-button type="primary" @click="confirmRename">确认</n-button>
      </template>
    </n-modal>

    <!-- Add manager dialog -->
    <n-modal v-model:show="addManagerShow" title="添加成员" style="max-width:420px" preset="card">
      <div class="hp-row">
        <n-input v-model:value="newName" placeholder="姓名" size="large" />
        <n-input v-model:value="newEmail" placeholder="邮箱" size="large" />
      </div>
      <template #footer>
        <n-button @click="addManagerShow = false">取消</n-button>
        <n-button type="primary" @click="confirmAddManager">添加</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { reactive, computed, watch, ref, nextTick, onMounted, onBeforeUnmount } from "vue";
import { NInput, NSelect, NButton, NModal, NDivider } from "naive-ui";

const props = defineProps({ modelValue: Object });
const emit = defineEmits(["update:modelValue"]);

// ── Constants ──────────────────────

const TEAMS_KEY = "mailswift_hp_teams";
const ACTIVE_TEAM_KEY = "mailswift_hp_active_team";

const DEFAULT_MANAGERS = [
  { name: "Dong Lei", email: "dong.lei@oe.21vianet.com" },
  { name: "Dong Jiaying", email: "dong.jiaying@oe.21vianet.com" },
  { name: "Zhang Weidong", email: "zhang.weidong@oe.21vianet.com" },
  { name: "Sun Yonghui", email: "sun.yonghui@oe.21vianet.com" },
  { name: "Qiu Chao", email: "qiu.chao@oe.21vianet.com" },
  { name: "Luo Yang", email: "luo.yang@oe.21vianet.com" },
];

const severityOptions = [
  { label: "Sev0", value: "Sev0" },
  { label: "Sev1", value: "Sev1" },
  { label: "Sev2", value: "Sev2" },
];

const categoryOptions = [
  { label: "Network", value: "Network" },
  { label: "Compute", value: "Compute" },
  { label: "Storage", value: "Storage" },
  { label: "Database", value: "Database" },
];

function todayStr() {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${m}/${dd}/${d.getFullYear()}`;
}

// ── Team management ────────────────

function loadTeams() { try { return JSON.parse(localStorage.getItem(TEAMS_KEY)); } catch { return null; } }
function saveTeams(v) { try { localStorage.setItem(TEAMS_KEY, JSON.stringify(v)); } catch { /* */ } }
function newId() { return "t_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6); }

function initTeams() {
  let list = loadTeams();
  if (!list || list.length === 0) {
    const id = newId();
    list = [{ id, name: "我的团队", managers: DEFAULT_MANAGERS.map((m) => ({ ...m })) }];
    saveTeams(list);
    localStorage.setItem(ACTIVE_TEAM_KEY, id);
  }
  return list;
}

const teams = ref(initTeams());
const activeTeamId = ref(localStorage.getItem(ACTIVE_TEAM_KEY) || teams.value[0]?.id || "");
const activeTeam = computed(() => teams.value.find((t) => t.id === activeTeamId.value) || teams.value[0]);
const activeTeamName = computed(() => activeTeam.value?.name || "");
const teamOptions = computed(() => teams.value.map((t) => ({ label: t.name, value: t.id })));

function onTeamSwitch(id) {
  activeTeamId.value = id;
  localStorage.setItem(ACTIVE_TEAM_KEY, id);
  local.managers = activeTeam.value.managers.map((m) => ({ ...m }));
}

// ── Team panel ─────────────────────

const teamPanelShow = ref(false);
const editingManagers = ref([]);
const renameShow = ref(false);
const renameValue = ref("");
const renameTargetId = ref("");
const addManagerShow = ref(false);
const newName = ref("");
const newEmail = ref("");

function selectTeamInPanel(id) {
  activeTeamId.value = id;
  localStorage.setItem(ACTIVE_TEAM_KEY, id);
  editingManagers.value = activeTeam.value.managers.map((m) => ({ ...m }));
}

watch(teamPanelShow, (show) => { if (show) selectTeamInPanel(activeTeamId.value); });

function createTeam() {
  const id = newId();
  teams.value.push({ id, name: "新团队", managers: [] });
  saveTeams(teams.value);
  selectTeamInPanel(id);
}

function deleteTeam(id) {
  if (teams.value.length <= 1) return;
  teams.value = teams.value.filter((t) => t.id !== id);
  saveTeams(teams.value);
  if (activeTeamId.value === id) {
    activeTeamId.value = teams.value[0].id;
    localStorage.setItem(ACTIVE_TEAM_KEY, activeTeamId.value);
    local.managers = teams.value[0].managers.map((m) => ({ ...m }));
  }
  selectTeamInPanel(activeTeamId.value);
}

function renameTeam() { renameTargetId.value = activeTeamId.value; renameValue.value = activeTeam.value?.name || ""; renameShow.value = true; }
function renameTeamInPanel(id) { renameTargetId.value = id; const t = teams.value.find((t) => t.id === id); renameValue.value = t?.name || ""; renameShow.value = true; }
function confirmRename() { if (renameValue.value.trim()) { const t = teams.value.find((t) => t.id === renameTargetId.value); if (t) t.name = renameValue.value.trim(); saveTeams(teams.value); } renameShow.value = false; }

function addMemberToPanel() { editingManagers.value.push({ name: "", email: "" }); }
function removeMemberFromPanel(i) { editingManagers.value.splice(i, 1); }

watch(teamPanelShow, (show, old) => {
  if (old && !show) {
    const t = teams.value.find((t) => t.id === activeTeamId.value);
    if (t) { t.managers = editingManagers.value.filter((m) => m.name || m.email); saveTeams(teams.value); local.managers = t.managers.map((m) => ({ ...m })); }
  }
});

// ── Manager pills ──────────────────

function removeManager(i) { local.managers.splice(i, 1); const t = teams.value.find((t) => t.id === activeTeamId.value); if (t) { t.managers = [...local.managers]; saveTeams(teams.value); } }
function addManagerRow() { newName.value = ""; newEmail.value = ""; addManagerShow.value = true; }
function confirmAddManager() { if (newName.value.trim() && newEmail.value.trim()) { local.managers.push({ name: newName.value.trim(), email: newEmail.value.trim() }); const t = teams.value.find((t) => t.id === activeTeamId.value); if (t) { t.managers = [...local.managers]; saveTeams(teams.value); } } addManagerShow.value = false; }

// ── Form state ─────────────────────

const defaultFormData = {
  status_prefix: "INITIAL",
  severity: "",
  ticket_id: "",
  category: "Network",
  title: "",
  date: todayStr(),
  current_status: "Initial",
  description: "",
  start_datetime: "Beijing Time(GMT+8) : ",
  impact: "No impact",
  managers: activeTeam.value?.managers.map((m) => ({ ...m })) || [],
  next_update: "30 minutes",
  resolution: "",
  end_datetime: "Beijing Time(GMT+8) : ",
};

const local = reactive({ ...defaultFormData, ...(props.modelValue || {}) });
if (!local.managers || local.managers.length === 0) {
  local.managers = activeTeam.value?.managers.map((m) => ({ ...m })) || [];
}

// ── Title preview ──────────────────

const titlePreview = computed(() => {
  const sev = local.severity || "Sev?";
  const tid = local.ticket_id || "Ticket ID";
  const cat = local.category || "Network";
  const ttl = local.title || "Title";
  return `${local.status_prefix || "INITIAL"} ${sev}-Incident [${tid}] - ${cat} - ${ttl}`;
});

// ── Emit ───────────────────────────

let suppressEmit = false;

watch(() => ({ ...local }), () => {
  if (suppressEmit) return;
  emit("update:modelValue", { ...local });
}, { deep: true });

watch(() => props.modelValue, (val) => {
  if (!val || Object.keys(val).length === 0) {
    suppressEmit = true;
    Object.assign(local, defaultFormData);
    local.managers = activeTeam.value?.managers.map((m) => ({ ...m })) || [];
    nextTick(() => { suppressEmit = false; });
    return;
  }
  // Sync non-empty changes from parent (template switch, lookup fill)
  suppressEmit = true;
  Object.assign(local, val);
  if (!local.managers || local.managers.length === 0) {
    local.managers = activeTeam.value?.managers.map((m) => ({ ...m })) || [];
  }
  nextTick(() => { suppressEmit = false; });
}, { deep: true });
</script>

<style scoped>
.hp-form { animation: hpFade 0.25s ease; }
@keyframes hpFade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

.hp-preview {
  background: #f0f7ff; border: 1px solid #c8ddf8; border-radius: 10px;
  padding: 12px 16px; margin-bottom: 24px; font-size: 14px; word-break: break-all;
}
.hp-preview-label { color: #0071e3; font-weight: 600; margin-right: 4px; }
.hp-preview-text { color: #1d1d1f; }

.hp-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
.hp-field { margin-bottom: 20px; }
.hp-label { display: block; font-size: 14px; font-weight: 500; color: #1d1d1f; margin-bottom: 6px; }
.hp-hint { display: block; font-size: 12px; color: #999; margin-top: 4px; }

.hp-mgr-bar { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.hp-mgr-team-label { font-size: 13px; color: #86868b; white-space: nowrap; }
.hp-mgr-pills {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  padding: 8px 12px; min-height: 40px; border: 1px solid #d0d0d0; border-radius: 8px; background: #fff;
}
.hp-mgr-pill {
  display: inline-flex; align-items: center; gap: 3px; padding: 2px 10px;
  background: #e6f4ea; color: #1e8e3e; border-radius: 12px; font-size: 13px; line-height: 1.6; white-space: nowrap;
}
.hp-mgr-x { background: none; border: none; color: inherit; cursor: pointer; font-size: 14px; padding: 0; line-height: 1; opacity: 0.5; }
.hp-mgr-x:hover { opacity: 1; }

/* Team panel */
.tm-panel { max-height: 60vh; overflow-y: auto; }
.tm-row { display: flex; align-items: center; gap: 12px; padding: 8px 12px; border-radius: 6px; cursor: pointer; transition: background 0.15s; }
.tm-row:hover { background: #f5f5f7; }
.tm-row.active { background: #e8f0fe; }
.tm-name { flex: 1; font-size: 14px; font-weight: 500; }
.tm-count { font-size: 13px; color: #86868b; }
.tm-members-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; }
.tm-member-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.tm-empty { font-size: 13px; color: #999; text-align: center; padding: 16px 0; }
</style>
