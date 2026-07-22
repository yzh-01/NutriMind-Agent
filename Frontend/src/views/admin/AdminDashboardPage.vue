<template>
  <div class="page-shell admin-dashboard">
    <section v-if="isPreviewMode" class="preview-console surface" aria-labelledby="preview-console-title">
      <div class="preview-console-copy">
        <Flask :size="22" weight="duotone" />
        <span>
          <b id="preview-console-title">管理员界面预览</b>
          <small>当前为本地演示数据，不会请求后端，也不代表真实系统状态。</small>
        </span>
      </div>
      <div class="preview-state-switch" role="group" aria-label="切换看板预览状态">
        <button
          v-for="item in previewStates"
          :key="item.value"
          type="button"
          :class="{ active: previewState === item.value }"
          :aria-pressed="previewState === item.value"
          @click="setPreviewState(item.value)"
        >
          {{ item.label }}
        </button>
      </div>
    </section>

    <header class="page-head">
      <div>
        <span class="status-chip"><Gauge :size="16" weight="bold" /> Dashboard API</span>
        <h1 class="page-title">系统运行，一屏总览。</h1>
        <p class="page-description">查看用户、检测任务、训练任务与食物数据的实时聚合统计。</p>
      </div>
      <button class="refresh-action" type="button" :disabled="loading" @click="loadDashboard">
        <CircleNotch v-if="loading" class="spin" :size="18" weight="bold" />
        <ArrowsClockwise v-else :size="18" weight="bold" />
        {{ loading ? '正在刷新' : '刷新数据' }}
      </button>
    </header>

    <div v-if="loading && !dashboard" class="dashboard-loading" aria-label="正在加载系统看板">
      <section class="overview-grid">
        <article v-for="index in 6" :key="index" class="metric-card surface skeleton-card" aria-hidden="true">
          <span class="skeleton icon-skeleton" />
          <span class="skeleton value-skeleton" />
          <span class="skeleton label-skeleton" />
        </article>
      </section>
      <section class="operations-grid">
        <article class="surface panel-skeleton skeleton" />
        <article class="surface panel-skeleton skeleton" />
      </section>
    </div>

    <section v-else-if="loadError" class="error-state surface" role="alert">
      <WarningCircle :size="38" weight="duotone" />
      <h2>系统看板暂时无法加载</h2>
      <p>{{ loadError }}</p>
      <button type="button" @click="isPreviewMode ? setPreviewState('data') : loadDashboard()">
        {{ isPreviewMode ? '查看正常数据' : '重新加载' }}
      </button>
    </section>

    <template v-else-if="dashboard">
      <p class="refresh-time" aria-live="polite">{{ refreshLabel }}</p>

      <section v-if="isDashboardEmpty" class="empty-notice surface" role="status">
        <Info :size="24" weight="duotone" />
        <div>
          <b>当前没有业务数据</b>
          <p>页面结构保持可见，所有统计指标均显示为 0。</p>
        </div>
      </section>

      <section class="overview-grid" aria-label="系统总览数据">
        <article v-for="item in overviewMetrics" :key="item.key" class="metric-card surface">
          <span class="metric-icon"><component :is="item.icon" :size="21" weight="duotone" /></span>
          <strong class="metric-number">
            <CountUp v-if="hasMetric(item.value)" :to="item.value" />
            <span v-else>--</span>
          </strong>
          <div><b>{{ item.label }}</b><small>{{ item.hint }}</small></div>
        </article>
      </section>

      <section class="operations-grid">
        <article class="status-panel surface" aria-labelledby="detection-title">
          <header class="panel-heading">
            <div>
              <span>检测任务</span>
              <h2 id="detection-title" class="section-title">任务状态分布</h2>
            </div>
            <strong>{{ formatMetric(dashboard.detection.total) }}</strong>
          </header>

          <div class="detection-highlights">
            <div>
              <Target :size="20" weight="duotone" />
              <span><small>累计检测目标</small><b>{{ formatMetric(dashboard.detection.total_objects_detected) }}</b></span>
            </div>
            <div>
              <Timer :size="20" weight="duotone" />
              <span><small>平均推理耗时</small><b>{{ formatSeconds(dashboard.detection.avg_inference_time) }}</b></span>
            </div>
          </div>

          <ul class="status-bars" aria-label="检测任务各状态数量">
            <li v-for="item in detectionStatuses" :key="item.key">
              <div><span>{{ item.label }}</span><strong>{{ formatMetric(item.value) }}</strong></div>
              <span class="bar-track" aria-hidden="true"><i :class="item.tone" :style="{ width: statusWidth(item.value, dashboard.detection.total) }" /></span>
            </li>
          </ul>
        </article>

        <article class="status-panel surface" aria-labelledby="training-title">
          <header class="panel-heading">
            <div>
              <span>模型训练</span>
              <h2 id="training-title" class="section-title">训练任务状态</h2>
            </div>
            <strong>{{ formatMetric(dashboard.training.total) }}</strong>
          </header>

          <div class="training-summary">
            <Cpu :size="32" weight="duotone" />
            <div>
              <b>{{ formatMetric(dashboard.training.running) }}</b>
              <small>个任务正在运行</small>
            </div>
          </div>

          <ul class="status-bars" aria-label="训练任务各状态数量">
            <li v-for="item in trainingStatuses" :key="item.key">
              <div><span>{{ item.label }}</span><strong>{{ formatMetric(item.value) }}</strong></div>
              <span class="bar-track" aria-hidden="true"><i :class="item.tone" :style="{ width: statusWidth(item.value, dashboard.training.total) }" /></span>
            </li>
          </ul>
        </article>
      </section>

      <section class="users-panel surface" aria-labelledby="users-title">
        <header class="panel-heading users-heading">
          <div>
            <span>用户统计</span>
            <h2 id="users-title" class="section-title">账户与活跃情况</h2>
          </div>
          <p>“今日新增”按照后端 UTC 自然日统计。</p>
        </header>

        <div class="user-metrics">
          <article v-for="item in userMetrics" :key="item.key">
            <component :is="item.icon" :size="22" weight="duotone" />
            <span><small>{{ item.label }}</small><strong class="metric-number">{{ formatMetric(item.value) }}</strong></span>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, markRaw, onMounted, ref } from 'vue'
import {
  PhArrowsClockwise as ArrowsClockwise, PhCheckCircle as CheckCircle,
  PhCircleNotch as CircleNotch, PhCpu as Cpu,
  PhFlask as Flask, PhForkKnife as ForkKnife, PhGauge as Gauge, PhInfo as Info,
  PhListChecks as ListChecks, PhPulse as Pulse,
  PhStack as Stack, PhTarget as Target, PhTimer as Timer, PhUserCheck as UserCheck,
  PhUserGear as UserGear, PhUsers as Users, PhWarningCircle as WarningCircle,
} from '@phosphor-icons/vue'
import CountUp from '@/components/motion/CountUp.vue'
import { getDashboardStatsApi } from '@/api/dashboard'
import { useUserStore } from '@/stores/user'
import { normalizeDashboardStats } from '@/utils/dashboardData'

const userStore = useUserStore()
const dashboard = ref(null)
const loading = ref(false)
const loadError = ref('')
const refreshedAt = ref(null)
const previewState = ref('data')
const previewStates = [
  { value: 'data', label: '正常数据' },
  { value: 'empty', label: '空数据' },
  { value: 'loading', label: '加载中' },
  { value: 'error', label: '接口异常' },
]
let previewLoadId = 0
const isPreviewMode = computed(() => userStore.isAdminPreview)

const overviewMetrics = computed(() => dashboard.value ? [
  { key: 'users', label: '用户总数', hint: '系统注册账户', value: dashboard.value.overview.total_users, icon: markRaw(Users) },
  { key: 'active', label: '活跃用户', hint: '当前启用账户', value: dashboard.value.overview.active_users, icon: markRaw(UserCheck) },
  { key: 'scenes', label: '检测场景', hint: '已配置场景', value: dashboard.value.overview.total_detection_scenes, icon: markRaw(Stack) },
  { key: 'detections', label: '检测任务', hint: '累计任务数量', value: dashboard.value.overview.total_detection_tasks, icon: markRaw(ListChecks) },
  { key: 'training', label: '训练任务', hint: '累计训练任务', value: dashboard.value.overview.total_training_tasks, icon: markRaw(Cpu) },
  { key: 'foods', label: '食物数据', hint: '营养数据条目', value: dashboard.value.overview.total_food_items, icon: markRaw(ForkKnife) },
] : [])

const detectionStatuses = computed(() => dashboard.value ? [
  { key: 'completed', label: '已完成', value: dashboard.value.detection.completed, tone: 'success' },
  { key: 'processing', label: '处理中', value: dashboard.value.detection.processing, tone: 'active' },
  { key: 'pending', label: '等待中', value: dashboard.value.detection.pending, tone: 'pending' },
  { key: 'failed', label: '失败', value: dashboard.value.detection.failed, tone: 'danger' },
] : [])

const trainingStatuses = computed(() => dashboard.value ? [
  { key: 'completed', label: '已完成', value: dashboard.value.training.completed, tone: 'success' },
  { key: 'running', label: '运行中', value: dashboard.value.training.running, tone: 'active' },
  { key: 'pending', label: '等待中', value: dashboard.value.training.pending, tone: 'pending' },
  { key: 'paused', label: '已暂停', value: dashboard.value.training.paused, tone: 'paused' },
  { key: 'failed', label: '失败', value: dashboard.value.training.failed, tone: 'danger' },
] : [])

const userMetrics = computed(() => dashboard.value ? [
  { key: 'total', label: '用户总数', value: dashboard.value.users.total, icon: markRaw(Users) },
  { key: 'active', label: '启用用户', value: dashboard.value.users.active, icon: markRaw(Pulse) },
  { key: 'superusers', label: '管理员', value: dashboard.value.users.superusers, icon: markRaw(UserGear) },
  { key: 'newToday', label: '今日新增', value: dashboard.value.users.new_today, icon: markRaw(CheckCircle) },
] : [])

const refreshLabel = computed(() => {
  if (!refreshedAt.value) return ''
  return `数据刷新于 ${new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(refreshedAt.value)}`
})

const isDashboardEmpty = computed(() => dashboard.value && [
  dashboard.value.overview.total_users,
  dashboard.value.overview.total_detection_tasks,
  dashboard.value.overview.total_training_tasks,
  dashboard.value.overview.total_food_items,
].every((value) => value === 0))

function hasMetric(value) {
  return Number.isFinite(value)
}

function formatMetric(value) {
  return hasMetric(value) ? new Intl.NumberFormat('zh-CN').format(value) : '--'
}

function formatSeconds(value) {
  return hasMetric(value) ? `${value.toFixed(4)} 秒` : '暂无数据'
}

function statusWidth(value, total) {
  if (!hasMetric(value) || !hasMetric(total) || total <= 0) return '0%'
  return `${Math.min(100, Math.max(0, value / total * 100))}%`
}

async function loadDashboard() {
  if (isPreviewMode.value) {
    await applyPreviewState()
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    dashboard.value = normalizeDashboardStats(await getDashboardStatsApi({ silent: true }))
    refreshedAt.value = new Date()
  } catch {
    loadError.value = '没有读取到 Dashboard API 数据，请确认后端服务和当前账户权限后重试。'
  } finally {
    loading.value = false
  }
}

async function applyPreviewState() {
  if (!import.meta.env.DEV) return
  const loadId = ++previewLoadId
  loading.value = false
  loadError.value = ''
  dashboard.value = null

  if (previewState.value === 'loading') {
    loading.value = true
    return
  }
  if (previewState.value === 'error') {
    loadError.value = '这是用于审查错误反馈的演示状态。你可以切换其他状态继续检查页面。'
    return
  }

  const { dashboardPreviewStats, emptyDashboardPreviewStats } = await import('@/mocks/dashboardPreview')
  if (loadId !== previewLoadId) return
  const payload = previewState.value === 'empty' ? emptyDashboardPreviewStats : dashboardPreviewStats
  dashboard.value = normalizeDashboardStats(payload)
  refreshedAt.value = new Date()
}

function setPreviewState(state) {
  previewState.value = state
  applyPreviewState()
}

onMounted(loadDashboard)
</script>

<style lang="scss" scoped>
.admin-dashboard { padding-bottom: 36px; }
.preview-console { margin-bottom: 18px; padding: 13px 14px; display: flex; align-items: center; justify-content: space-between; gap: 18px; border-color: rgba(159, 226, 75, .24); }
.preview-console-copy { display: flex; align-items: center; gap: 10px; color: var(--primary); }
.preview-console-copy span { display: grid; gap: 2px; }
.preview-console-copy b { color: var(--text); font-size: .8rem; }
.preview-console-copy small { color: var(--muted); font-size: .7rem; line-height: 1.45; }
.preview-state-switch { padding: 4px; display: flex; gap: 4px; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 10px; }
.preview-state-switch button { min-height: 44px; padding: 0 11px; color: var(--muted); background: transparent; border: 1px solid transparent; border-radius: 7px; font-size: .72rem; font-weight: 600; transition: color 180ms var(--ease-out), background 180ms var(--ease-out), border-color 180ms var(--ease-out); }
.preview-state-switch button:hover { color: var(--text-secondary); }
.preview-state-switch button.active { color: var(--primary); background: var(--primary-soft); border-color: rgba(159, 226, 75, .2); }
.page-head { margin-bottom: 22px; display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; }
.page-head .status-chip { margin-bottom: 15px; }
.refresh-action, .error-state button { min-height: 46px; padding: 0 16px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; color: #11160f; background: var(--primary); border: 1px solid var(--primary); border-radius: 10px; font-weight: 600; transition: background 180ms var(--ease-out), transform 180ms var(--ease-out); }
.refresh-action:hover:not(:disabled), .error-state button:hover { background: var(--primary-hover); }
.refresh-action:active:not(:disabled), .error-state button:active { transform: scale(.98); }
.refresh-action:disabled { opacity: .55; }
.refresh-time { margin: 0 0 10px; color: var(--muted); font-size: .72rem; text-align: right; }
.empty-notice { margin-bottom: 12px; padding: 15px 17px; display: flex; align-items: center; gap: 12px; color: var(--primary); }
.empty-notice div { display: grid; gap: 2px; }
.empty-notice b { color: var(--text); font-size: .82rem; }
.empty-notice p { margin: 0; color: var(--muted); font-size: .72rem; line-height: 1.5; }
.overview-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; }
.metric-card { min-height: 154px; padding: 17px; display: flex; flex-direction: column; }
.metric-icon { width: 38px; height: 38px; display: grid; place-items: center; color: var(--primary); background: var(--primary-soft); border-radius: 10px; }
.metric-card > strong { margin: auto 0 10px; font-size: clamp(2rem, 3vw, 2.8rem); font-weight: 600; line-height: 1; }
.metric-card > div { display: grid; gap: 2px; }
.metric-card b { font-size: .78rem; }
.metric-card small { color: var(--muted); font-size: .68rem; }
.operations-grid { margin-top: 12px; display: grid; grid-template-columns: 1.15fr .85fr; gap: 12px; }
.status-panel { min-height: 440px; padding: clamp(20px, 2.5vw, 28px); }
.panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.panel-heading span { color: var(--primary); font-size: .72rem; font-weight: 600; }
.panel-heading h2 { margin-top: 5px; }
.panel-heading > strong { font-family: "Barlow Condensed"; font-size: 2.35rem; font-weight: 600; line-height: 1; }
.detection-highlights { margin: 24px 0 26px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.detection-highlights > div { min-height: 76px; padding: 13px; display: flex; align-items: center; gap: 11px; color: var(--accent); background: var(--canvas-soft); border-radius: 11px; }
.detection-highlights span { display: grid; gap: 3px; }
.detection-highlights small { color: var(--muted); font-size: .66rem; }
.detection-highlights b { color: var(--text); font-size: .9rem; font-variant-numeric: tabular-nums; }
.training-summary { margin: 24px 0 26px; min-height: 94px; padding: 17px; display: flex; align-items: center; gap: 15px; color: var(--primary); background: linear-gradient(135deg, var(--primary-soft), transparent), var(--canvas-soft); border-radius: 12px; }
.training-summary div { display: grid; }
.training-summary b { color: var(--text); font-family: "Barlow Condensed"; font-size: 2rem; line-height: 1; }
.training-summary small { margin-top: 4px; color: var(--muted); font-size: .7rem; }
.status-bars { margin: 0; padding: 0; display: grid; gap: 17px; list-style: none; }
.status-bars li > div { margin-bottom: 7px; display: flex; justify-content: space-between; gap: 14px; }
.status-bars li span { color: var(--text-secondary); font-size: .74rem; }
.status-bars li strong { font-size: .76rem; font-variant-numeric: tabular-nums; }
.bar-track { height: 7px; display: block; overflow: hidden; background: rgba(255, 255, 255, .05); border-radius: 7px; }
.bar-track i { height: 100%; display: block; border-radius: inherit; transition: width 360ms var(--ease-out); }
.bar-track .success { background: var(--primary); }
.bar-track .active { background: var(--accent); }
.bar-track .pending { background: var(--text-secondary); }
.bar-track .paused { background: var(--text-secondary); }
.bar-track .danger { background: var(--danger); }
.users-panel { margin-top: 12px; padding: clamp(20px, 2.5vw, 28px); }
.users-heading { align-items: flex-end; }
.users-heading p { max-width: 40ch; margin: 0; color: var(--muted); font-size: .72rem; text-align: right; }
.user-metrics { margin-top: 22px; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.user-metrics article { min-height: 94px; padding: 16px; display: flex; align-items: center; gap: 13px; color: var(--primary); background: var(--canvas-soft); border-radius: 11px; }
.user-metrics article span { display: grid; gap: 4px; }
.user-metrics small { color: var(--muted); font-size: .68rem; }
.user-metrics strong { color: var(--text); font-size: 1.65rem; font-weight: 600; line-height: 1; }
.error-state { min-height: 430px; display: grid; place-content: center; justify-items: center; padding: 28px; color: var(--danger); text-align: center; }
.error-state h2 { margin: 15px 0 7px; color: var(--text); font-family: "Barlow Condensed"; font-size: 2rem; }
.error-state p { max-width: 54ch; margin: 0 0 20px; color: var(--text-secondary); line-height: 1.65; }
.skeleton { background: linear-gradient(100deg, var(--surface-soft) 20%, var(--surface-raised) 36%, var(--surface-soft) 52%); background-size: 200% 100%; animation: shimmer 1.35s linear infinite; }
.skeleton-card { gap: 12px; }
.icon-skeleton { width: 38px; height: 38px; border-radius: 10px; }
.value-skeleton { width: 65%; height: 34px; margin-top: auto; border-radius: 7px; }
.label-skeleton { width: 82%; height: 11px; border-radius: 5px; }
.panel-skeleton { min-height: 440px; }
.spin { animation: spin 800ms linear infinite; }
@keyframes shimmer { to { background-position-x: -200%; } }
@keyframes spin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .skeleton, .spin { animation: none; }
  .bar-track i, .refresh-action, .error-state button, .preview-state-switch button { transition: none; }
}

@media (max-width: 1180px) {
  .overview-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

@media (max-width: 820px) {
  .preview-console { align-items: stretch; flex-direction: column; }
  .preview-state-switch { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .page-head { align-items: flex-start; flex-direction: column; }
  .refresh-action { width: 100%; }
  .operations-grid { grid-template-columns: 1fr; }
  .user-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .preview-state-switch { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .preview-state-switch button { min-height: 44px; }
  .overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .metric-card { min-height: 142px; padding: 14px; }
  .status-panel, .users-panel { padding: 18px 14px; }
  .detection-highlights { grid-template-columns: 1fr; }
  .users-heading { align-items: flex-start; flex-direction: column; }
  .users-heading p { text-align: left; }
  .user-metrics { grid-template-columns: 1fr; }
}
</style>
