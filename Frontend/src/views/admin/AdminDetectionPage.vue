<template>
  <div class="page-shell detection-monitor">
    <section v-if="isPreviewMode" class="preview-console surface" aria-labelledby="detection-preview-title">
      <div class="preview-console-copy">
        <Flask :size="22" weight="duotone" />
        <span>
          <b id="detection-preview-title">目标检测监控预览</b>
          <small>当前为本地聚合数据，不会请求后端，也不代表真实任务状态。</small>
        </span>
      </div>
      <div class="preview-state-switch" role="group" aria-label="切换检测监控预览状态">
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
        <span class="status-chip"><Scan :size="16" weight="bold" /> Detection Dashboard API</span>
        <h1 class="page-title">检测负载，集中掌握。</h1>
        <p class="page-description">观察目标检测任务的总体状态、处理积压、失败占比和模型推理效率。</p>
      </div>
      <button class="refresh-action" type="button" :disabled="loading || taskLoading" @click="refreshAll">
        <CircleNotch v-if="loading || taskLoading" class="spin" :size="18" weight="bold" />
        <ArrowsClockwise v-else :size="18" weight="bold" />
        {{ loading || taskLoading ? '正在刷新' : '刷新数据' }}
      </button>
    </header>

    <div v-if="loading && !stats" class="monitor-loading" aria-label="正在加载目标检测监控">
      <section class="metrics-grid">
        <article v-for="index in 4" :key="index" class="metric-card surface" aria-hidden="true">
          <span class="skeleton icon-skeleton" />
          <span class="skeleton value-skeleton" />
          <span class="skeleton label-skeleton" />
        </article>
      </section>
      <section class="monitor-grid">
        <article class="surface panel-skeleton skeleton" />
        <article class="surface panel-skeleton skeleton" />
      </section>
    </div>

    <section v-else-if="loadError" class="error-state surface" role="alert">
      <WarningCircle :size="40" weight="duotone" />
      <h2>目标检测统计暂时无法加载</h2>
      <p>{{ loadError }}</p>
      <button type="button" @click="isPreviewMode ? setPreviewState('data') : loadDetection()">
        {{ isPreviewMode ? '查看正常数据' : '重新加载' }}
      </button>
    </section>

    <template v-else-if="stats">
      <div class="data-meta">
        <p aria-live="polite">{{ refreshLabel }}</p>
        <span class="read-only-tag"><Eye :size="15" />只读监控</span>
      </div>

      <section v-if="partialSource" class="data-notice surface" role="status">
        <Info :size="21" weight="duotone" />
        <div><b>部分接口暂时不可用</b><p>{{ partialSource }}，页面已使用可用数据补全当前统计。</p></div>
      </section>

      <section v-if="isEmpty" class="empty-notice surface" role="status">
        <CheckCircle :size="23" weight="duotone" />
        <div><b>当前没有目标检测任务</b><p>统计接口返回了有效的零值，页面仍保留完整监控结构。</p></div>
      </section>

      <section class="metrics-grid" aria-label="目标检测核心指标">
        <article v-for="item in metricCards" :key="item.key" class="metric-card surface">
          <span class="metric-icon" :class="item.tone"><component :is="item.icon" :size="22" weight="duotone" /></span>
          <strong>{{ item.formatter(item.value) }}</strong>
          <div><b>{{ item.label }}</b><small>{{ item.hint }}</small></div>
        </article>
      </section>

      <section class="monitor-grid">
        <article class="distribution-panel surface" aria-labelledby="distribution-title">
          <header class="panel-heading">
            <div>
              <span>任务分布</span>
              <h2 id="distribution-title" class="section-title">状态负载</h2>
            </div>
            <div class="panel-total"><small>分布合计</small><strong>{{ formatMetric(distributionTotal) }}</strong></div>
          </header>

          <p v-if="consistencyNote" class="consistency-note" role="status">
            <WarningCircle :size="17" />{{ consistencyNote }}
          </p>

          <ul v-if="statusRows.length" class="status-list" aria-label="检测任务状态数量与占比">
            <li v-for="item in statusRows" :key="item.status">
              <div class="status-row-head">
                <span class="status-name" :class="item.tone"><component :is="item.icon" :size="19" weight="duotone" />{{ item.label }}</span>
                <span><strong>{{ formatMetric(item.count) }}</strong><small>{{ formatPercent(item.percentage) }}</small></span>
              </div>
              <span class="bar-track" aria-hidden="true"><i :class="item.tone" :style="{ width: `${item.percentage || 0}%` }" /></span>
            </li>
          </ul>
          <div v-else class="distribution-empty" role="status">
            <ChartBar :size="30" weight="duotone" />
            <p>接口没有返回可用的状态分布。</p>
          </div>

          <p class="chart-summary">{{ chartSummary }}</p>
        </article>

        <article class="health-panel surface" aria-labelledby="health-title">
          <header class="panel-heading">
            <div>
              <span>运行质量</span>
              <h2 id="health-title" class="section-title">处理概况</h2>
            </div>
            <Pulse :size="25" weight="duotone" />
          </header>

          <div class="success-gauge">
            <div
              class="gauge-ring"
              :class="healthTone"
              :style="gaugeStyle"
              role="img"
              :aria-label="successRate === null ? '暂无任务完成率' : `任务完成率 ${formatPercent(successRate)}`"
            >
              <span><strong>{{ formatPercent(successRate) }}</strong><small>完成率</small></span>
            </div>
            <div class="gauge-copy">
              <b>{{ healthLabel }}</b>
              <p>{{ healthDescription }}</p>
            </div>
          </div>

          <div class="health-details">
            <article>
              <span class="detail-icon active"><HourglassMedium :size="20" weight="duotone" /></span>
              <div><small>等待与处理中</small><strong>{{ formatMetric(activeWorkload) }}</strong><p>当前尚未完成的任务</p></div>
            </article>
            <article>
              <span class="detail-icon danger"><WarningOctagon :size="20" weight="duotone" /></span>
              <div><small>失败占比</small><strong>{{ formatPercent(failedRate) }}</strong><p>{{ formatMetric(stats.failed) }} 个失败任务</p></div>
            </article>
          </div>
        </article>
      </section>

      <section class="scope-panel surface" aria-labelledby="scope-title">
        <span class="scope-icon"><ShieldCheck :size="24" weight="duotone" /></span>
        <div>
          <span>数据范围</span>
          <h2 id="scope-title" class="section-title">聚合监控与只读任务历史</h2>
          <p>上方统计用于观察整体负载，下方历史由检测任务接口提供真实任务编号和结果详情；当前页面只读取任务，不提供文档之外的取消、重跑或删除操作。</p>
        </div>
      </section>
    </template>

    <section class="history-panel surface" aria-labelledby="detection-history-title">
      <header class="history-heading">
        <div>
          <span>Task history</span>
          <h2 id="detection-history-title" class="section-title">检测任务历史</h2>
          <p>查看后端保存的检测任务、处理状态与识别结果。</p>
        </div>
        <button type="button" :disabled="taskLoading" aria-label="刷新检测任务历史" @click="loadTasks">
          <ArrowsClockwise :class="{ spin: taskLoading }" :size="18" />
        </button>
      </header>

      <div v-if="taskLoading && !tasks.length" class="history-loading" aria-label="正在加载检测任务历史">
        <div v-for="index in 4" :key="index" aria-hidden="true"><span class="skeleton wide" /><span class="skeleton" /><span class="skeleton" /></div>
      </div>
      <div v-else-if="taskError" class="history-feedback error" role="alert">
        <WarningCircle :size="30" weight="duotone" /><b>检测任务历史暂时无法加载</b><p>{{ taskError }}</p><button type="button" @click="loadTasks">重新加载</button>
      </div>
      <div v-else-if="!tasks.length" class="history-feedback" role="status">
        <ListChecks :size="32" weight="duotone" /><b>还没有检测任务</b><p>{{ isPreviewMode ? '预览模式不会生成真实任务历史。' : '用户完成第一次图片检测后，任务会出现在这里。' }}</p>
      </div>
      <template v-else>
        <div class="history-table">
          <table>
            <thead><tr><th>任务编号</th><th>状态</th><th>场景</th><th>检测目标</th><th>推理耗时</th><th>创建时间</th><th><span class="sr-only">操作</span></th></tr></thead>
            <tbody>
              <tr v-for="task in tasks" :key="task.uuid">
                <td><span class="task-id" :title="task.uuid || ''">{{ task.uuid || '--' }}</span></td>
                <td><span class="task-status" :class="taskStatusMeta(task.status).tone"><i />{{ taskStatusMeta(task.status).label }}</span></td>
                <td>{{ task.sceneName || (task.sceneId ? `场景 ${task.sceneId}` : '--') }}</td>
                <td>{{ formatMetric(task.totalObjects) }}</td>
                <td>{{ formatSeconds(task.inferenceTime) }}</td>
                <td><time :datetime="task.createdAt || undefined">{{ formatTaskDate(task.createdAt) }}</time></td>
                <td><button class="detail-action" type="button" :disabled="!task.uuid" @click="openTaskDetail(task)"><Eye :size="17" />详情</button></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="history-cards">
          <article v-for="task in tasks" :key="task.uuid">
            <header><span class="task-status" :class="taskStatusMeta(task.status).tone"><i />{{ taskStatusMeta(task.status).label }}</span><time :datetime="task.createdAt || undefined">{{ formatTaskDate(task.createdAt) }}</time></header>
            <b :title="task.uuid || ''">{{ task.uuid || '任务编号未知' }}</b>
            <dl><div><dt>场景</dt><dd>{{ task.sceneName || '--' }}</dd></div><div><dt>目标数</dt><dd>{{ formatMetric(task.totalObjects) }}</dd></div><div><dt>推理耗时</dt><dd>{{ formatSeconds(task.inferenceTime) }}</dd></div></dl>
            <button class="detail-action" type="button" :disabled="!task.uuid" @click="openTaskDetail(task)"><Eye :size="17" />查看详情</button>
          </article>
        </div>

        <footer class="history-pagination">
          <span>共 {{ taskTotal }} 个任务 · 第 {{ taskPage }} / {{ taskTotalPages }} 页</span>
          <div><button type="button" :disabled="taskPage <= 1 || taskLoading" aria-label="上一页" @click="changeTaskPage(taskPage - 1)"><CaretLeft :size="18" /></button><button type="button" :disabled="taskPage >= taskTotalPages || taskLoading" aria-label="下一页" @click="changeTaskPage(taskPage + 1)"><CaretRight :size="18" /></button></div>
        </footer>
      </template>
    </section>

    <el-drawer v-model="taskDetailVisible" class="detection-detail-drawer" size="min(560px, 100vw)" append-to-body destroy-on-close>
      <template #header><div class="drawer-title"><span><Eye :size="19" /></span><div><b>检测任务详情</b><small>{{ selectedTask?.uuid || '正在读取任务' }}</small></div></div></template>
      <div v-if="taskDetailLoading" class="drawer-feedback"><CircleNotch class="spin" :size="28" /><p>正在读取检测结果…</p></div>
      <div v-else-if="taskDetailError" class="drawer-feedback error" role="alert"><WarningCircle :size="30" /><p>{{ taskDetailError }}</p><button type="button" @click="loadTaskDetail(selectedTask?.uuid)">重试</button></div>
      <template v-else-if="selectedTask">
        <section class="task-detail-summary">
          <span class="task-status" :class="taskStatusMeta(selectedTask.status).tone"><i />{{ taskStatusMeta(selectedTask.status).label }}</span>
          <h3>{{ selectedTask.sceneName || '未命名检测场景' }}</h3>
          <p>{{ selectedTask.uuid || '--' }}</p>
          <dl><div><dt>检测目标</dt><dd>{{ formatMetric(selectedTask.totalObjects) }}</dd></div><div><dt>推理耗时</dt><dd>{{ formatSeconds(selectedTask.inferenceTime) }}</dd></div><div><dt>创建时间</dt><dd>{{ formatTaskDate(selectedTask.createdAt) }}</dd></div><div><dt>完成时间</dt><dd>{{ formatTaskDate(selectedTask.completedAt || selectedTask.updatedAt) }}</dd></div></dl>
        </section>
        <img v-if="selectedTask.imageUrl" class="task-image" :src="selectedTask.imageUrl" alt="检测任务原始图片">
        <p v-if="selectedTask.errorMessage" class="task-detail-error" role="alert"><WarningOctagon :size="18" />{{ selectedTask.errorMessage }}</p>
        <section class="detection-results" aria-labelledby="detection-results-title">
          <header><div><span>Objects</span><h3 id="detection-results-title">识别结果</h3></div><strong>{{ selectedTask.detections.length }}</strong></header>
          <div v-if="!selectedTask.detections.length" class="result-empty">接口没有返回可展示的目标明细。</div>
          <ul v-else>
            <li v-for="item in selectedTask.detections" :key="item.id"><div><b>{{ item.classNameCn || item.className }}</b><small>{{ item.classNameCn ? item.className : '未提供英文类别' }}</small></div><span><strong>{{ formatConfidence(item.confidence) }}</strong><small>{{ formatBox(item.bbox) }}</small></span></li>
          </ul>
        </section>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, markRaw, onMounted, ref } from 'vue'
import {
  PhArrowsClockwise as ArrowsClockwise, PhCaretLeft as CaretLeft,
  PhCaretRight as CaretRight, PhChartBar as ChartBar,
  PhCheckCircle as CheckCircle, PhCircleNotch as CircleNotch,
  PhCrosshair as Crosshair, PhEye as Eye, PhFlask as Flask,
  PhHourglassMedium as HourglassMedium, PhInfo as Info,
  PhListChecks as ListChecks, PhPulse as Pulse, PhScan as Scan,
  PhShieldCheck as ShieldCheck, PhTarget as Target, PhTimer as Timer,
  PhWarningCircle as WarningCircle, PhWarningOctagon as WarningOctagon,
} from '@phosphor-icons/vue'
import { getDetectionTaskDetailApi, getDetectionTasksApi } from '@/api/detection'
import {
  getDetectionStatsApi, getDetectionStatusDistributionApi,
} from '@/api/dashboard'
import { useUserStore } from '@/stores/user'
import {
  deriveDetectionDistribution, deriveDetectionStats,
  normalizeDetectionDistribution, normalizeDetectionStats,
} from '@/utils/detectionData'
import {
  normalizeDetectionTaskDetail, normalizeDetectionTaskList,
} from '@/utils/detectionTaskData'

const taskPageSize = 20
const userStore = useUserStore()
const stats = ref(null)
const distribution = ref([])
const loading = ref(false)
const loadError = ref('')
const partialSource = ref('')
const refreshedAt = ref(null)
const previewState = ref('data')
const tasks = ref([])
const taskTotal = ref(0)
const taskPage = ref(1)
const taskLoading = ref(false)
const taskError = ref('')
const taskDetailVisible = ref(false)
const taskDetailLoading = ref(false)
const taskDetailError = ref('')
const selectedTask = ref(null)
const previewStates = [
  { value: 'data', label: '正常数据' },
  { value: 'empty', label: '空数据' },
  { value: 'loading', label: '加载中' },
  { value: 'error', label: '接口异常' },
]
let previewLoadId = 0

const isPreviewMode = computed(() => userStore.isAdminPreview)
const taskTotalPages = computed(() => Math.max(1, Math.ceil(taskTotal.value / taskPageSize)))
const distributionTotal = computed(() => distribution.value.reduce((sum, item) => sum + (Number.isFinite(item.count) ? item.count : 0), 0))
const effectiveTotal = computed(() => Number.isFinite(stats.value?.total) ? stats.value.total : distributionTotal.value)
const successRate = computed(() => rate(stats.value?.completed, effectiveTotal.value))
const failedRate = computed(() => rate(stats.value?.failed, effectiveTotal.value))
const activeWorkload = computed(() => sumMetrics(stats.value?.pending, stats.value?.processing))
const isEmpty = computed(() => effectiveTotal.value === 0)

const metricCards = computed(() => stats.value ? [
  { key: 'total', label: '检测任务', hint: '累计任务总数', value: effectiveTotal.value, icon: markRaw(ListChecks), tone: '', formatter: formatMetric },
  { key: 'completed', label: '已完成', hint: '成功结束任务', value: stats.value.completed, icon: markRaw(CheckCircle), tone: 'success', formatter: formatMetric },
  { key: 'objects', label: '检测目标', hint: '累计识别目标数', value: stats.value.totalObjectsDetected, icon: markRaw(Target), tone: 'accent', formatter: formatMetric },
  { key: 'latency', label: '平均推理耗时', hint: '单次推理平均秒数', value: stats.value.avgInferenceTime, icon: markRaw(Timer), tone: 'neutral', formatter: formatSeconds },
] : [])

const statusMeta = {
  completed: { label: '已完成', tone: 'success', icon: markRaw(CheckCircle) },
  processing: { label: '处理中', tone: 'active', icon: markRaw(Crosshair) },
  pending: { label: '等待中', tone: 'pending', icon: markRaw(HourglassMedium) },
  failed: { label: '失败', tone: 'danger', icon: markRaw(WarningOctagon) },
}

const statusRows = computed(() => distribution.value.map((item) => ({
  ...item,
  ...(statusMeta[item.status] || { label: item.status, tone: 'unknown', icon: markRaw(Pulse) }),
  percentage: rate(item.count, effectiveTotal.value) || 0,
})))

const refreshLabel = computed(() => refreshedAt.value
  ? `数据刷新于 ${new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(refreshedAt.value)}`
  : '')

const consistencyNote = computed(() => {
  if (!Number.isFinite(stats.value?.total) || !distribution.value.length) return ''
  if (stats.value.total === distributionTotal.value) return ''
  return `任务总数为 ${formatMetric(stats.value.total)}，状态分布合计为 ${formatMetric(distributionTotal.value)}。两项数据暂不一致。`
})

const chartSummary = computed(() => {
  if (!statusRows.value.length) return '暂无可总结的状态数据。'
  if (distributionTotal.value === 0) return '当前所有任务状态数量均为 0。'
  const largest = [...statusRows.value].sort((a, b) => b.count - a.count)[0]
  return `状态分布中“${largest.label}”数量最多，共 ${formatMetric(largest.count)} 个，占 ${formatPercent(largest.percentage)}。`
})

const healthTone = computed(() => {
  if (successRate.value === null) return 'idle'
  if (successRate.value >= 90) return 'healthy'
  if (successRate.value >= 70) return 'watch'
  return 'critical'
})

const healthLabel = computed(() => ({
  healthy: '整体处理稳定', watch: '需要关注积压', critical: '失败或积压偏高', idle: '暂无任务数据',
})[healthTone.value])

const healthDescription = computed(() => {
  if (healthTone.value === 'idle') return '有新任务后，这里会根据完成率展示运行概况。'
  if (healthTone.value === 'healthy') return '大部分检测任务已经完成，可以继续关注等待和失败数量。'
  if (healthTone.value === 'watch') return '完成率低于 90%，建议结合等待、处理和失败数量观察。'
  return '完成率低于 70%，当前聚合数据提示需要优先检查检测服务。'
})

const gaugeStyle = computed(() => ({
  '--gauge-angle': `${Math.max(0, Math.min(100, successRate.value || 0)) * 3.6}deg`,
}))

function rate(value, total) {
  if (!Number.isFinite(value) || !Number.isFinite(total) || total <= 0) return null
  return Math.max(0, value / total * 100)
}

function sumMetrics(...values) {
  const valid = values.filter(Number.isFinite)
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) : null
}

function formatMetric(value) {
  return Number.isFinite(value) ? new Intl.NumberFormat('zh-CN').format(value) : '--'
}

function formatSeconds(value) {
  return Number.isFinite(value) ? `${value.toFixed(4)} 秒` : '--'
}

function formatPercent(value) {
  return Number.isFinite(value) ? `${value.toFixed(1)}%` : '--'
}

function formatTaskDate(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(date)
}

function formatConfidence(value) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : '--'
}

function formatBox(value) {
  return Array.isArray(value) ? `坐标 ${value.map((item) => Math.round(item)).join(', ')}` : '未提供坐标'
}

function taskStatusMeta(status) {
  return ({
    completed: { label: '已完成', tone: 'success' },
    processing: { label: '处理中', tone: 'active' },
    running: { label: '处理中', tone: 'active' },
    pending: { label: '等待中', tone: 'pending' },
    failed: { label: '失败', tone: 'danger' },
  })[status] || { label: status || '未知', tone: 'unknown' }
}

async function loadDetection() {
  if (isPreviewMode.value) {
    await applyPreviewState()
    return
  }

  loading.value = true
  loadError.value = ''
  partialSource.value = ''
  try {
    const [statsResult, distributionResult] = await Promise.allSettled([
      getDetectionStatsApi({ silent: true }),
      getDetectionStatusDistributionApi({ silent: true }),
    ])

    if (statsResult.status === 'rejected' && distributionResult.status === 'rejected') {
      throw new Error('Both detection dashboard requests failed')
    }

    const nextDistribution = distributionResult.status === 'fulfilled'
      ? normalizeDetectionDistribution(distributionResult.value)
      : []
    const nextStats = statsResult.status === 'fulfilled'
      ? normalizeDetectionStats(statsResult.value)
      : deriveDetectionStats(nextDistribution)

    stats.value = nextStats
    distribution.value = nextDistribution.length
      ? nextDistribution
      : deriveDetectionDistribution(nextStats)

    if (statsResult.status === 'rejected') partialSource.value = '检测统计接口读取失败'
    if (distributionResult.status === 'rejected') partialSource.value = '状态分布接口读取失败'
    refreshedAt.value = new Date()
  } catch {
    stats.value = null
    distribution.value = []
    loadError.value = '没有读取到检测统计或状态分布数据，请稍后重试。'
  } finally {
    loading.value = false
  }
}

async function loadTasks() {
  if (isPreviewMode.value) {
    tasks.value = []
    taskTotal.value = 0
    taskError.value = ''
    return
  }
  taskLoading.value = true
  taskError.value = ''
  try {
    const normalized = normalizeDetectionTaskList(await getDetectionTasksApi({
      page: taskPage.value, page_size: taskPageSize,
    }, { silent: true }))
    tasks.value = normalized.items
    taskTotal.value = normalized.total
    taskPage.value = normalized.page
  } catch {
    taskError.value = '没有读取到检测任务列表，请稍后重试。'
  } finally {
    taskLoading.value = false
  }
}

function changeTaskPage(nextPage) {
  if (nextPage < 1 || nextPage > taskTotalPages.value) return
  taskPage.value = nextPage
  loadTasks()
}

async function openTaskDetail(task) {
  selectedTask.value = task
  taskDetailVisible.value = true
  await loadTaskDetail(task.uuid)
}

async function loadTaskDetail(uuid) {
  if (!uuid || isPreviewMode.value) return
  taskDetailLoading.value = true
  taskDetailError.value = ''
  try {
    selectedTask.value = normalizeDetectionTaskDetail(await getDetectionTaskDetailApi(uuid, { silent: true }))
  } catch {
    taskDetailError.value = '检测任务详情暂时无法读取，请稍后重试。'
  } finally {
    taskDetailLoading.value = false
  }
}

function refreshAll() {
  loadDetection()
  loadTasks()
}

async function loadPreviewPayload(useEmptyData) {
  if (!import.meta.env.DEV) return null
  const { dashboardPreviewStats, emptyDashboardPreviewStats } = await import('@/mocks/dashboardPreview')
  return useEmptyData ? emptyDashboardPreviewStats.detection : dashboardPreviewStats.detection
}

async function applyPreviewState() {
  if (!import.meta.env.DEV) return
  const loadId = ++previewLoadId
  loading.value = false
  loadError.value = ''
  partialSource.value = ''
  stats.value = null
  distribution.value = []

  if (previewState.value === 'loading') {
    loading.value = true
    return
  }
  if (previewState.value === 'error') {
    loadError.value = '这是用于检查检测监控错误反馈的本地演示状态。'
    return
  }

  const payload = await loadPreviewPayload(previewState.value === 'empty')
  if (loadId !== previewLoadId || !payload) return
  stats.value = normalizeDetectionStats(payload)
  distribution.value = deriveDetectionDistribution(stats.value)
  refreshedAt.value = new Date()
}

function setPreviewState(state) {
  previewState.value = state
  applyPreviewState()
}

onMounted(refreshAll)
</script>

<style lang="scss" scoped>
.detection-monitor { padding-bottom: 36px; }
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
.data-meta { margin: 0 0 10px; display: flex; align-items: center; justify-content: flex-end; gap: 10px; }
.data-meta p { margin: 0; color: var(--muted); font-size: .7rem; }
.read-only-tag { min-height: 29px; padding: 0 8px; display: inline-flex; align-items: center; gap: 5px; color: var(--text-secondary); background: var(--surface); border: 1px solid var(--border); border-radius: 7px; font-size: .65rem; }
.data-notice, .empty-notice { margin-bottom: 12px; padding: 14px 16px; display: flex; align-items: center; gap: 11px; color: var(--accent); }
.empty-notice { color: var(--primary); }
.data-notice div, .empty-notice div { display: grid; gap: 2px; }
.data-notice b, .empty-notice b { color: var(--text); font-size: .78rem; }
.data-notice p, .empty-notice p { margin: 0; color: var(--muted); font-size: .69rem; line-height: 1.5; }
.metrics-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.metric-card { min-height: 166px; padding: 18px; display: flex; flex-direction: column; }
.metric-icon { width: 40px; height: 40px; display: grid; place-items: center; color: var(--primary); background: var(--primary-soft); border-radius: 10px; }
.metric-icon.accent { color: var(--accent); background: rgba(240, 177, 92, .1); }
.metric-icon.neutral { color: var(--text-secondary); background: var(--surface-soft); }
.metric-card > strong { margin: auto 0 11px; font-family: "Barlow Condensed"; font-size: clamp(2rem, 4vw, 3rem); font-weight: 600; line-height: 1; font-variant-numeric: tabular-nums; }
.metric-card > div { display: grid; gap: 2px; }
.metric-card b { font-size: .78rem; }
.metric-card small { color: var(--muted); font-size: .67rem; }
.monitor-grid { margin-top: 12px; display: grid; grid-template-columns: 1.2fr .8fr; gap: 12px; }
.distribution-panel, .health-panel { min-height: 470px; padding: clamp(20px, 2.5vw, 28px); }
.panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.panel-heading > div:first-child > span { color: var(--primary); font-size: .7rem; font-weight: 600; }
.panel-heading h2 { margin-top: 5px; }
.panel-total { display: grid; justify-items: end; gap: 2px; }
.panel-total small { color: var(--muted); font-size: .64rem; }
.panel-total strong { font-family: "Barlow Condensed"; font-size: 2rem; line-height: 1; font-variant-numeric: tabular-nums; }
.consistency-note { margin: 16px 0 -2px; padding: 10px 11px; display: flex; align-items: flex-start; gap: 7px; color: var(--accent); background: rgba(240,177,92,.08); border-radius: 8px; font-size: .68rem; line-height: 1.5; }
.status-list { margin: 27px 0 0; padding: 0; display: grid; gap: 24px; list-style: none; }
.status-row-head { margin-bottom: 9px; display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.status-name { display: inline-flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: .74rem; font-weight: 600; }
.status-name.success { color: var(--primary); }
.status-name.active { color: var(--accent); }
.status-name.danger { color: #ff938d; }
.status-row-head > span:last-child { display: flex; align-items: baseline; gap: 8px; }
.status-row-head strong { color: var(--text); font-size: .76rem; font-variant-numeric: tabular-nums; }
.status-row-head small { min-width: 42px; color: var(--muted); font-size: .64rem; text-align: right; font-variant-numeric: tabular-nums; }
.bar-track { height: 9px; display: block; overflow: hidden; background: var(--canvas-soft); border-radius: 9px; }
.bar-track i { height: 100%; display: block; border-radius: inherit; transition: width 360ms var(--ease-out); }
.bar-track i.success { background: var(--primary); }
.bar-track i.active { background: var(--accent); }
.bar-track i.pending { background: var(--text-secondary); }
.bar-track i.danger { background: var(--danger); }
.bar-track i.unknown { background: var(--muted); }
.chart-summary { margin: 24px 0 0; padding-top: 16px; color: var(--muted); border-top: 1px solid var(--border); font-size: .68rem; line-height: 1.6; }
.distribution-empty { min-height: 270px; display: grid; place-content: center; justify-items: center; gap: 9px; color: var(--muted); }
.distribution-empty p { margin: 0; font-size: .72rem; }
.health-panel > .panel-heading > svg { color: var(--primary); }
.success-gauge { margin: 28px 0 24px; display: flex; align-items: center; gap: 22px; }
.gauge-ring { --gauge-color: var(--primary); width: 142px; height: 142px; flex: 0 0 auto; padding: 10px; display: grid; place-items: center; background: conic-gradient(var(--gauge-color) var(--gauge-angle), var(--surface-soft) 0); border-radius: 50%; }
.gauge-ring.watch { --gauge-color: var(--accent); }
.gauge-ring.critical { --gauge-color: var(--danger); }
.gauge-ring.idle { --gauge-color: var(--muted); }
.gauge-ring > span { width: 100%; height: 100%; display: grid; place-content: center; justify-items: center; background: var(--surface); border-radius: 50%; }
.gauge-ring strong { font-family: "Barlow Condensed"; font-size: 2.2rem; line-height: 1; font-variant-numeric: tabular-nums; }
.gauge-ring small { margin-top: 5px; color: var(--muted); font-size: .64rem; }
.gauge-copy { min-width: 0; }
.gauge-copy b { color: var(--text); font-family: "Barlow Condensed"; font-size: 1.4rem; }
.gauge-copy p { margin: 7px 0 0; color: var(--muted); font-size: .7rem; line-height: 1.65; }
.health-details { display: grid; gap: 8px; }
.health-details article { min-height: 84px; padding: 14px; display: flex; align-items: center; gap: 12px; background: var(--canvas-soft); border-radius: 11px; }
.detail-icon { width: 38px; height: 38px; flex: 0 0 auto; display: grid; place-items: center; color: var(--accent); background: rgba(240,177,92,.1); border-radius: 9px; }
.detail-icon.danger { color: #ff938d; background: rgba(240,103,95,.09); }
.health-details article > div { display: grid; grid-template-columns: 1fr auto; align-items: baseline; gap: 3px 12px; width: 100%; }
.health-details small { color: var(--muted); font-size: .65rem; }
.health-details strong { color: var(--text); font-family: "Barlow Condensed"; font-size: 1.35rem; font-variant-numeric: tabular-nums; }
.health-details p { grid-column: 1 / -1; margin: 0; color: var(--muted); font-size: .64rem; }
.history-panel { margin-top: 12px; padding: clamp(18px, 2.5vw, 26px); }
.history-heading { margin-bottom: 15px; display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.history-heading > div > span, .detection-results header span { color: var(--primary); font-size: .68rem; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; }
.history-heading h2 { margin-top: 5px; }
.history-heading p { margin: 6px 0 0; color: var(--muted); font-size: .7rem; }
.history-heading > button { width: 44px; height: 44px; display: grid; place-items: center; color: var(--text-secondary); background: var(--surface-soft); border: 1px solid var(--border); border-radius: 9px; }
.history-heading > button:hover:not(:disabled) { color: var(--primary); border-color: rgba(159,226,75,.28); }
.history-heading > button:disabled { opacity: .45; }
.history-table { overflow-x: auto; }
.history-table table { width: 100%; border-collapse: collapse; }
.history-table th { padding: 11px 10px; color: var(--muted); border-bottom: 1px solid var(--border); font-size: .64rem; font-weight: 600; text-align: left; white-space: nowrap; }
.history-table td { min-height: 64px; padding: 12px 10px; color: var(--text-secondary); border-bottom: 1px solid var(--border); font-size: .69rem; }
.history-table tbody tr { transition: background 180ms var(--ease-out); }
.history-table tbody tr:hover { background: rgba(255,255,255,.018); }
.task-id { display: block; max-width: 180px; overflow: hidden; color: var(--text); font-variant-numeric: tabular-nums; text-overflow: ellipsis; white-space: nowrap; }
.task-status { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); font-size: .65rem; white-space: nowrap; }
.task-status i { width: 7px; height: 7px; background: currentColor; border-radius: 50%; }
.task-status.success { color: var(--primary); }
.task-status.active { color: var(--accent); }
.task-status.danger { color: #ff938d; }
.task-status.pending { color: var(--text-secondary); }
.detail-action { min-height: 40px; padding: 0 9px; display: inline-flex; align-items: center; justify-content: center; gap: 5px; color: var(--text-secondary); background: transparent; border: 1px solid transparent; border-radius: 8px; font-size: .65rem; }
.detail-action:hover:not(:disabled) { color: var(--primary); background: var(--primary-soft); }
.detail-action:disabled { opacity: .36; }
.history-cards { display: none; }
.history-pagination { margin-top: 12px; padding-top: 14px; display: flex; align-items: center; justify-content: flex-end; gap: 15px; color: var(--muted); border-top: 1px solid var(--border); font-size: .65rem; }
.history-pagination > div { display: flex; gap: 6px; }
.history-pagination button { width: 40px; height: 40px; display: grid; place-items: center; color: var(--text-secondary); background: var(--surface-soft); border: 1px solid var(--border); border-radius: 8px; }
.history-pagination button:disabled { opacity: .35; }
.history-loading { display: grid; }
.history-loading > div { min-height: 62px; padding: 10px; display: grid; grid-template-columns: 1.2fr .6fr .5fr; align-items: center; gap: 18px; border-bottom: 1px solid var(--border); }
.history-loading .skeleton { height: 12px; border-radius: 6px; }
.history-loading .wide { width: 72%; }
.history-feedback { min-height: 250px; display: grid; place-content: center; justify-items: center; gap: 7px; color: var(--muted); text-align: center; }
.history-feedback.error { color: #ff938d; }
.history-feedback b { color: var(--text); }
.history-feedback p { max-width: 52ch; margin: 0; color: var(--muted); font-size: .7rem; line-height: 1.55; }
.history-feedback button, .drawer-feedback button { min-height: 42px; margin-top: 8px; padding: 0 14px; color: #11160f; background: var(--primary); border: 0; border-radius: 8px; font-weight: 600; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
:global(.detection-detail-drawer.el-drawer) { --el-drawer-bg-color: var(--surface); color: var(--text-secondary); background: var(--surface); border-left: 1px solid var(--border); }
:global(.detection-detail-drawer .el-drawer__header) { margin: 0; padding: 18px 20px; border-bottom: 1px solid var(--border); }
:global(.detection-detail-drawer .el-drawer__body) { padding: 20px; }
:global(.detection-detail-drawer .el-drawer__close-btn) { width: 44px; height: 44px; color: var(--muted); }
.drawer-title { display: flex; align-items: center; gap: 10px; }
.drawer-title > span { width: 38px; height: 38px; display: grid; place-items: center; color: var(--primary); background: var(--primary-soft); border-radius: 9px; }
.drawer-title > div { min-width: 0; display: grid; gap: 3px; }
.drawer-title b { color: var(--text); font-size: .8rem; }
.drawer-title small { max-width: 340px; overflow: hidden; color: var(--muted); font-size: .64rem; text-overflow: ellipsis; white-space: nowrap; }
.drawer-feedback { min-height: 420px; display: grid; place-content: center; justify-items: center; gap: 10px; color: var(--primary); text-align: center; }
.drawer-feedback.error { color: #ff938d; }
.drawer-feedback p { max-width: 42ch; margin: 0; color: var(--muted); font-size: .72rem; line-height: 1.6; }
.task-detail-summary { padding: 17px; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 12px; }
.task-detail-summary h3 { margin: 10px 0 3px; color: var(--text); font-family: "Barlow Condensed"; font-size: 1.5rem; }
.task-detail-summary > p { margin: 0; overflow-wrap: anywhere; color: var(--muted); font-size: .64rem; }
.task-detail-summary dl { margin: 17px 0 0; display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 1px; overflow: hidden; background: var(--border); border: 1px solid var(--border); border-radius: 9px; }
.task-detail-summary dl div { min-height: 64px; padding: 10px; display: grid; align-content: center; gap: 4px; background: var(--surface); }
.task-detail-summary dt { color: var(--muted); font-size: .61rem; }
.task-detail-summary dd { margin: 0; color: var(--text-secondary); font-size: .7rem; }
.task-image { width: 100%; max-height: 330px; margin-top: 12px; display: block; object-fit: contain; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 12px; }
.task-detail-error { margin: 12px 0 0; padding: 11px; display: flex; align-items: flex-start; gap: 7px; color: #ff938d; background: rgba(240,103,95,.08); border-radius: 9px; font-size: .68rem; line-height: 1.55; }
.detection-results { margin-top: 20px; }
.detection-results header { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; }
.detection-results h3 { margin: 3px 0 0; color: var(--text); font-size: .95rem; }
.detection-results header > strong { font-family: "Barlow Condensed"; font-size: 2rem; }
.detection-results ul { margin: 12px 0 0; padding: 0; display: grid; gap: 7px; list-style: none; }
.detection-results li { min-height: 64px; padding: 11px 12px; display: flex; align-items: center; justify-content: space-between; gap: 16px; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 9px; }
.detection-results li > div, .detection-results li > span { min-width: 0; display: grid; gap: 3px; }
.detection-results li > span { justify-items: end; }
.detection-results li b { color: var(--text); font-size: .72rem; }
.detection-results li strong { color: var(--primary); font-size: .72rem; }
.detection-results li small { max-width: 250px; overflow: hidden; color: var(--muted); font-size: .61rem; text-overflow: ellipsis; white-space: nowrap; }
.result-empty { min-height: 150px; display: grid; place-content: center; color: var(--muted); font-size: .7rem; text-align: center; }
.scope-panel { margin-top: 12px; padding: 20px; display: flex; align-items: flex-start; gap: 14px; }
.scope-icon { width: 44px; height: 44px; flex: 0 0 auto; display: grid; place-items: center; color: var(--primary); background: var(--primary-soft); border-radius: 10px; }
.scope-panel > div > span { color: var(--primary); font-size: .68rem; font-weight: 600; }
.scope-panel h2 { margin-top: 4px; }
.scope-panel p { max-width: 90ch; margin: 7px 0 0; color: var(--muted); font-size: .7rem; line-height: 1.65; }
.error-state { min-height: 440px; display: grid; place-content: center; justify-items: center; padding: 28px; color: var(--danger); text-align: center; }
.error-state h2 { margin: 15px 0 7px; color: var(--text); font-family: "Barlow Condensed"; font-size: 2rem; }
.error-state p { max-width: 54ch; margin: 0 0 20px; color: var(--text-secondary); line-height: 1.65; }
.skeleton { background: linear-gradient(100deg, var(--surface-soft) 20%, var(--surface-raised) 36%, var(--surface-soft) 52%); background-size: 200% 100%; animation: shimmer 1.35s linear infinite; }
.icon-skeleton { width: 40px; height: 40px; border-radius: 10px; }
.value-skeleton { width: 65%; height: 38px; margin-top: auto; border-radius: 7px; }
.label-skeleton { width: 80%; height: 11px; margin-top: 10px; border-radius: 5px; }
.panel-skeleton { min-height: 470px; }
.spin { animation: spin 800ms linear infinite; }
@keyframes shimmer { to { background-position-x: -200%; } }
@keyframes spin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .skeleton, .spin { animation: none; }
  .bar-track i, .refresh-action, .preview-state-switch button, .history-table tbody tr { transition: none; }
}
@media (max-width: 980px) {
  .monitor-grid { grid-template-columns: 1fr; }
  .health-panel { min-height: auto; }
  .health-details { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .preview-console { align-items: stretch; flex-direction: column; }
  .preview-state-switch { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .page-head { align-items: stretch; flex-direction: column; }
  .refresh-action { width: 100%; }
  .metrics-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .data-meta { justify-content: space-between; }
  .history-table { display: none; }
  .history-cards { display: grid; gap: 8px; }
  .history-cards article { padding: 14px; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 11px; }
  .history-cards article > header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .history-cards time { color: var(--muted); font-size: .62rem; }
  .history-cards article > b { margin-top: 12px; display: block; overflow: hidden; color: var(--text); font-size: .7rem; text-overflow: ellipsis; white-space: nowrap; }
  .history-cards dl { margin: 13px 0; display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 9px; }
  .history-cards dl div { display: grid; gap: 3px; }
  .history-cards dt { color: var(--muted); font-size: .58rem; }
  .history-cards dd { margin: 0; color: var(--text-secondary); font-size: .67rem; }
  .history-cards .detail-action { width: 100%; border-color: var(--border); }
}
@media (max-width: 540px) {
  .preview-state-switch { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .metric-card { min-height: 150px; padding: 14px; }
  .distribution-panel, .health-panel { padding: 18px 14px; }
  .success-gauge { align-items: flex-start; flex-direction: column; }
  .gauge-ring { width: 132px; height: 132px; }
  .health-details { grid-template-columns: 1fr; }
  .scope-panel { padding: 16px 14px; }
  .scope-icon { width: 40px; height: 40px; }
  .history-panel { padding: 16px 14px; }
  .history-heading { align-items: flex-start; }
  .history-cards dl { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .history-pagination { align-items: flex-start; flex-direction: column; }
  .history-pagination > div { align-self: flex-end; }
  .task-detail-summary dl { grid-template-columns: 1fr; }
}
</style>
