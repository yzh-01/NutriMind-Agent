<template>
  <div class="page-shell training-page">
    <section v-if="isPreviewMode" class="preview-notice surface" role="status">
      <Flask :size="22" weight="duotone" />
      <div><b>模型训练管理预览</b><p>以下是本地演示数据；创建、启动、暂停和删除操作已禁用。</p></div>
    </section>

    <header class="page-head">
      <div>
        <span class="status-chip"><Cpu :size="16" weight="bold" /> Training API</span>
        <h1 class="page-title">训练进度，统一管理。</h1>
        <p class="page-description">创建模型训练任务，跟踪运行状态与训练指标，并管理已生成的模型文件。</p>
      </div>
      <div class="head-actions">
        <button class="secondary-action" type="button" :disabled="listLoading" @click="loadAll">
          <CircleNotch v-if="listLoading" class="spin" :size="18" /><ArrowsClockwise v-else :size="18" />刷新
        </button>
        <button class="primary-action" type="button" :disabled="isPreviewMode" :title="isPreviewMode ? '预览模式不执行创建' : ''" @click="openCreate">
          <Plus :size="18" weight="bold" />创建训练
        </button>
      </div>
    </header>

    <section class="stats-grid" aria-label="训练任务状态统计">
      <article v-for="item in statCards" :key="item.key" class="stat-card surface">
        <span :class="item.tone"><component :is="item.icon" :size="20" weight="duotone" /></span>
        <strong>{{ formatMetric(item.value) }}</strong>
        <div><b>{{ item.label }}</b><small>{{ item.hint }}</small></div>
      </article>
    </section>

    <section class="training-distribution surface" aria-labelledby="training-distribution-title">
      <header>
        <div><span>Status distribution</span><h2 id="training-distribution-title" class="section-title">训练状态分布</h2></div>
        <p><strong>{{ formatMetric(distributionTotal) }}</strong> 个任务<span v-if="distributionFallback"> · 使用任务统计补全</span></p>
      </header>
      <ul v-if="distributionRows.length" aria-label="训练任务各状态数量与占比">
        <li v-for="item in distributionRows" :key="item.status">
          <div><span class="status-tag" :class="item.tone"><i />{{ item.label }}</span><span><strong>{{ formatMetric(item.count) }}</strong><small>{{ formatPercent(item.percentage) }}</small></span></div>
          <span class="distribution-track" aria-hidden="true"><i :class="item.tone" :style="{ width: `${item.percentage}%` }" /></span>
        </li>
      </ul>
      <div v-else class="distribution-empty" role="status">当前没有可展示的训练状态数据。</div>
    </section>

    <section class="task-panel surface" aria-labelledby="training-task-title">
      <header class="panel-heading">
        <div><span>Training queue</span><h2 id="training-task-title" class="section-title">训练任务</h2></div>
        <div class="sync-state" :class="{ active: pollingActive }"><Pulse :size="17" />{{ pollingActive ? '每 5 秒同步运行任务' : '手动刷新' }}</div>
      </header>

      <div v-if="listLoading && !tasks.length" class="loading-list" aria-label="正在加载训练任务">
        <div v-for="index in 4" :key="index" class="loading-row" aria-hidden="true"><span class="skeleton wide" /><span class="skeleton" /><span class="skeleton" /><span class="skeleton short" /></div>
      </div>
      <div v-else-if="listError" class="feedback-state error-state" role="alert">
        <WarningCircle :size="36" weight="duotone" /><h3>训练任务暂时无法加载</h3><p>{{ listError }}</p><button class="primary-action" type="button" @click="loadTasks()">重新加载</button>
      </div>
      <div v-else-if="!tasks.length" class="feedback-state" role="status">
        <Cpu :size="38" weight="duotone" /><h3>还没有训练任务</h3><p>创建第一个训练配置后，任务会出现在这里。</p><button class="primary-action" type="button" :disabled="isPreviewMode" @click="openCreate">创建训练</button>
      </div>
      <template v-else>
        <div class="desktop-table">
          <table>
            <thead><tr><th>任务与模型</th><th>状态</th><th>训练进度</th><th>配置</th><th>更新时间</th><th><span class="sr-only">操作</span></th></tr></thead>
            <tbody>
              <tr v-for="task in tasks" :key="task.uuid">
                <td><div class="task-identity"><span><Cpu :size="20" weight="duotone" /></span><div><b>{{ task.modelName || '未命名模型' }}</b><small>{{ task.uuid || '任务编号未知' }}</small></div></div></td>
                <td><span class="status-tag" :class="statusMeta(task.status).tone"><i />{{ statusMeta(task.status).label }}</span></td>
                <td><div class="progress-cell"><div><strong>{{ formatProgress(task.progress) }}</strong><small>{{ epochLabel(task) }}</small></div><span><i :style="{ width: `${task.progress || 0}%` }" /></span></div></td>
                <td><span class="config-cell"><b>{{ task.imgSize ? `${task.imgSize}px` : '--' }}</b><small>{{ task.batchSize ? `Batch ${task.batchSize}` : 'Batch --' }} · {{ task.epochs ? `${task.epochs} Epochs` : 'Epochs --' }}</small></span></td>
                <td><time :datetime="task.updatedAt || task.createdAt || undefined">{{ formatDate(task.updatedAt || task.createdAt) }}</time></td>
                <td><div class="row-actions"><button type="button" @click="openDetail(task)"><Eye :size="17" />详情</button><button v-if="task.status === 'pending'" type="button" :disabled="isPreviewMode || actionTaskId === task.uuid" @click="startTask(task)"><Play :size="17" />启动</button><button v-if="task.status === 'running'" class="warning" type="button" :disabled="isPreviewMode || actionTaskId === task.uuid" @click="pauseTask(task)"><Pause :size="17" />暂停</button></div></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mobile-cards">
          <article v-for="task in tasks" :key="task.uuid" class="task-card">
            <header><div class="task-identity"><span><Cpu :size="20" /></span><div><b>{{ task.modelName || '未命名模型' }}</b><small>{{ task.uuid || '任务编号未知' }}</small></div></div><span class="status-tag" :class="statusMeta(task.status).tone"><i />{{ statusMeta(task.status).label }}</span></header>
            <div class="mobile-progress"><div><strong>{{ formatProgress(task.progress) }}</strong><small>{{ epochLabel(task) }}</small></div><span><i :style="{ width: `${task.progress || 0}%` }" /></span></div>
            <dl><div><dt>图像尺寸</dt><dd>{{ task.imgSize ? `${task.imgSize}px` : '--' }}</dd></div><div><dt>Batch</dt><dd>{{ formatMetric(task.batchSize) }}</dd></div><div><dt>Epochs</dt><dd>{{ formatMetric(task.epochs) }}</dd></div><div><dt>更新时间</dt><dd>{{ formatDate(task.updatedAt || task.createdAt) }}</dd></div></dl>
            <footer class="row-actions"><button type="button" @click="openDetail(task)"><Eye :size="17" />详情</button><button v-if="task.status === 'pending'" type="button" :disabled="isPreviewMode || actionTaskId === task.uuid" @click="startTask(task)"><Play :size="17" />启动</button><button v-if="task.status === 'running'" class="warning" type="button" :disabled="isPreviewMode || actionTaskId === task.uuid" @click="pauseTask(task)"><Pause :size="17" />暂停</button></footer>
          </article>
        </div>

        <footer class="pagination-bar"><span>共 {{ total }} 个任务 · 第 {{ page }} / {{ totalPages }} 页</span><div><button type="button" :disabled="page <= 1 || listLoading" aria-label="上一页" @click="changePage(page - 1)"><CaretLeft :size="18" /></button><button type="button" :disabled="page >= totalPages || listLoading" aria-label="下一页" @click="changePage(page + 1)"><CaretRight :size="18" /></button></div></footer>
      </template>
    </section>

    <section class="model-panel surface" aria-labelledby="model-list-title">
      <header class="panel-heading"><div><span>Model artifacts</span><h2 id="model-list-title" class="section-title">已训练模型</h2></div><button class="icon-action" type="button" :disabled="modelsLoading" aria-label="刷新模型列表" @click="loadModels"><ArrowsClockwise :class="{ spin: modelsLoading }" :size="18" /></button></header>
      <div v-if="modelsError" class="model-error" role="alert"><WarningCircle :size="19" />{{ modelsError }}<button type="button" @click="loadModels">重试</button></div>
      <div v-else-if="modelsLoading && !models.length" class="model-grid"><article v-for="index in 3" :key="index" class="model-card skeleton" aria-hidden="true" /></div>
      <div v-else-if="!models.length" class="model-empty" role="status">暂无已训练模型文件</div>
      <div v-else class="model-grid">
        <article v-for="model in models" :key="model.name" class="model-card"><span><Cube :size="22" weight="duotone" /></span><div><b :title="model.name">{{ model.name }}</b><small>{{ formatBytes(model.size) }} · {{ formatDate(model.createdAt) }}</small></div><button type="button" :disabled="isPreviewMode || deletingModel === model.name" :aria-label="`删除模型 ${model.name}`" @click="removeModel(model)"><CircleNotch v-if="deletingModel === model.name" class="spin" :size="18" /><Trash v-else :size="18" /></button></article>
      </div>
    </section>

    <el-dialog v-model="createVisible" class="training-dialog" width="min(620px, calc(100vw - 32px))" destroy-on-close append-to-body>
      <template #header><div class="dialog-title"><span><Plus :size="18" weight="bold" /></span><div><b>创建训练任务</b><small>填写后端可识别的模型与数据集配置</small></div></div></template>
      <form id="training-create-form" class="create-form" @submit.prevent="submitCreate">
        <label><span>模型名称</span><input v-model.trim="createForm.modelName" required placeholder="例如 yolo11s"><small>接口暂未提供可选模型字典，请填写后端支持的模型名称。</small></label>
        <label class="full"><span>数据集 YAML 路径</span><input v-model.trim="createForm.dataYaml" required placeholder="例如 /datasets/food/data.yaml"><small>当前没有数据集列表接口，只能填写后端服务器可访问的路径。</small></label>
        <label><span>训练轮次</span><input v-model.number="createForm.epochs" type="number" inputmode="numeric" min="1" required></label>
        <label><span>图像尺寸</span><input v-model.number="createForm.imgSize" type="number" inputmode="numeric" min="32" step="32" required></label>
        <label><span>Batch Size</span><input v-model.number="createForm.batchSize" type="number" inputmode="numeric" min="1" required></label>
        <label class="auto-start"><input v-model="createForm.autoStart" type="checkbox"><span>创建后立即启动</span></label>
        <p v-if="createError" class="inline-error full" role="alert"><WarningCircle :size="17" />{{ createError }}</p>
      </form>
      <template #footer><div class="dialog-actions"><button class="secondary-action" type="button" :disabled="creating" @click="createVisible = false">取消</button><button class="primary-action" type="submit" form="training-create-form" :disabled="creating"><CircleNotch v-if="creating" class="spin" :size="17" />{{ creating ? '正在创建' : '确认创建' }}</button></div></template>
    </el-dialog>

    <el-dialog v-model="detailVisible" class="training-dialog detail-dialog" width="min(1080px, calc(100vw - 32px))" destroy-on-close append-to-body>
      <template #header><div class="dialog-title"><span><ChartLine :size="18" weight="bold" /></span><div><b>训练详情与指标</b><small>{{ selectedTask?.uuid || '任务详情' }}</small></div></div></template>
      <div v-if="detailLoading" class="dialog-loading"><CircleNotch class="spin" :size="28" /><span>正在读取训练任务与指标</span></div>
      <div v-else-if="detailError" class="dialog-error" role="alert"><WarningCircle :size="24" />{{ detailError }}<button type="button" @click="loadDetail(selectedTask.uuid)">重试</button></div>
      <div v-else-if="selectedTask" class="detail-content">
        <section class="detail-summary"><div><span class="status-tag" :class="statusMeta(selectedTask.status).tone"><i />{{ statusMeta(selectedTask.status).label }}</span><h3>{{ selectedTask.modelName || '未命名模型' }}</h3><p>{{ selectedTask.uuid }}</p></div><strong>{{ formatProgress(selectedTask.progress) }}</strong></section>
        <dl class="detail-grid"><div><dt>数据集</dt><dd>{{ selectedTask.dataYaml || '--' }}</dd></div><div><dt>训练轮次</dt><dd>{{ epochLabel(selectedTask) }}</dd></div><div><dt>图像尺寸</dt><dd>{{ selectedTask.imgSize ? `${selectedTask.imgSize}px` : '--' }}</dd></div><div><dt>Batch Size</dt><dd>{{ formatMetric(selectedTask.batchSize) }}</dd></div><div><dt>开始时间</dt><dd>{{ formatDate(selectedTask.startedAt) }}</dd></div><div><dt>完成时间</dt><dd>{{ formatDate(selectedTask.completedAt) }}</dd></div></dl>
        <p v-if="selectedTask.errorMessage" class="task-error" role="alert"><WarningOctagon :size="18" />{{ selectedTask.errorMessage }}</p>
        <section v-if="metrics" class="metrics-content">
          <div class="final-metrics"><article v-for="item in finalMetricCards" :key="item.key"><small>{{ item.label }}</small><strong>{{ formatDecimal(item.value) }}</strong></article></div>
          <div class="charts-grid"><TrainingMetricChart title="Loss 曲线" :rows="metrics.epochs" :series="lossSeries" /><TrainingMetricChart title="准确率与召回率" :rows="metrics.epochs" :series="qualitySeries" /></div>
        </section>
        <div v-else class="metrics-empty" role="status"><ChartLine :size="28" weight="duotone" /><p>{{ metricsError || '当前任务暂时没有训练指标数据。' }}</p></div>
      </div>
      <template #footer><button class="secondary-action" type="button" @click="detailVisible = false">关闭</button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, markRaw, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  PhArrowsClockwise as ArrowsClockwise, PhCaretLeft as CaretLeft,
  PhCaretRight as CaretRight, PhChartLine as ChartLine,
  PhCheckCircle as CheckCircle, PhCircleNotch as CircleNotch,
  PhCpu as Cpu, PhCube as Cube, PhEye as Eye, PhFlask as Flask,
  PhHourglassMedium as HourglassMedium, PhPause as Pause, PhPlay as Play,
  PhPlus as Plus, PhPulse as Pulse, PhStopCircle as StopCircle,
  PhTrash as Trash, PhWarningCircle as WarningCircle,
  PhWarningOctagon as WarningOctagon,
} from '@phosphor-icons/vue'
import TrainingMetricChart from '@/components/admin/TrainingMetricChart.vue'
import { getTrainingStatsApi, getTrainingStatusDistributionApi } from '@/api/dashboard'
import {
  createTrainingTaskApi, deleteTrainingModelApi, getTrainingMetricsApi,
  getTrainingModelsApi, getTrainingTaskApi, getTrainingTasksApi,
  pauseTrainingTaskApi, startTrainingTaskApi,
} from '@/api/training'
import { useUserStore } from '@/stores/user'
import {
  deriveTrainingStats, deriveTrainingStatusDistribution, normalizeTrainingMetrics,
  normalizeTrainingModels, normalizeTrainingStats, normalizeTrainingStatusDistribution,
  normalizeTrainingTaskDetail, normalizeTrainingTaskList,
} from '@/utils/trainingData'

const pageSize = 20
const userStore = useUserStore()
const tasks = ref([])
const total = ref(0)
const page = ref(1)
const stats = ref(deriveTrainingStats([]))
const statusDistribution = ref([])
const distributionFallback = ref(false)
const listLoading = ref(false)
const listError = ref('')
const models = ref([])
const modelsLoading = ref(false)
const modelsError = ref('')
const deletingModel = ref('')
const actionTaskId = ref('')
const pollingActive = ref(false)
const createVisible = ref(false)
const creating = ref(false)
const createError = ref('')
const createForm = ref(defaultCreateForm())
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const selectedTask = ref(null)
const metrics = ref(null)
const metricsError = ref('')
let pollTimer = null
let previewLoaded = false

const isPreviewMode = computed(() => userStore.isAdminPreview)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const distributionTotal = computed(() => statusDistribution.value.reduce((sum, item) => sum + item.count, 0))
const distributionRows = computed(() => statusDistribution.value.map((item) => ({
  ...item,
  ...statusMeta(item.status),
  percentage: distributionTotal.value > 0 ? Math.max(0, item.count / distributionTotal.value * 100) : 0,
})))
const statCards = computed(() => [
  { key: 'total', label: '训练任务', hint: '累计任务总数', value: stats.value.total, icon: markRaw(Cpu), tone: 'neutral' },
  { key: 'running', label: '运行中', hint: '当前训练任务', value: stats.value.running, icon: markRaw(Pulse), tone: 'active' },
  { key: 'pending', label: '等待中', hint: '等待启动任务', value: stats.value.pending, icon: markRaw(HourglassMedium), tone: 'pending' },
  { key: 'paused', label: '已暂停', hint: '暂停训练任务', value: stats.value.paused, icon: markRaw(Pause), tone: 'paused' },
  { key: 'completed', label: '已完成', hint: '成功完成训练', value: stats.value.completed, icon: markRaw(CheckCircle), tone: 'success' },
  { key: 'failed', label: '失败', hint: '异常结束任务', value: stats.value.failed, icon: markRaw(StopCircle), tone: 'danger' },
])
const finalMetricCards = computed(() => metrics.value ? [
  { key: 'map50', label: 'mAP@50', value: metrics.value.finalMetrics.map50 },
  { key: 'map5095', label: 'mAP@50–95', value: metrics.value.finalMetrics.map50_95 },
  { key: 'precision', label: 'Precision', value: metrics.value.finalMetrics.precision },
  { key: 'recall', label: 'Recall', value: metrics.value.finalMetrics.recall },
] : [])
const lossSeries = [
  { key: 'trainBoxLoss', label: 'Train Box', tone: 'green', dash: 'solid' },
  { key: 'trainClsLoss', label: 'Train Cls', tone: 'orange', dash: 'dashed' },
  { key: 'valBoxLoss', label: 'Val Box', tone: 'blue', dash: 'solid' },
  { key: 'valClsLoss', label: 'Val Cls', tone: 'red', dash: 'dotted' },
]
const qualitySeries = [
  { key: 'map50', label: 'mAP@50', tone: 'green', dash: 'solid' },
  { key: 'map50_95', label: 'mAP@50–95', tone: 'orange', dash: 'dashed' },
  { key: 'precision', label: 'Precision', tone: 'blue', dash: 'solid' },
  { key: 'recall', label: 'Recall', tone: 'red', dash: 'dotted' },
]

function defaultCreateForm() { return { modelName: 'yolo11s', dataYaml: '', epochs: 100, imgSize: 640, batchSize: 32, autoStart: true } }
function statusMeta(status) { return ({ pending: { label: '等待中', tone: 'pending' }, running: { label: '运行中', tone: 'active' }, paused: { label: '已暂停', tone: 'paused' }, completed: { label: '已完成', tone: 'success' }, failed: { label: '失败', tone: 'danger' } })[status] || { label: status || '未知', tone: 'unknown' } }
function formatMetric(value) { return Number.isFinite(value) ? new Intl.NumberFormat('zh-CN').format(value) : '--' }
function formatDecimal(value) { return Number.isFinite(value) ? value.toFixed(4) : '--' }
function formatProgress(value) { return Number.isFinite(value) ? `${value.toFixed(0)}%` : '--' }
function formatPercent(value) { return Number.isFinite(value) ? `${value.toFixed(1)}%` : '--' }
function epochLabel(task) { if (!Number.isFinite(task?.epochs)) return 'Epoch --'; return Number.isFinite(task.currentEpoch) ? `${task.currentEpoch} / ${task.epochs} Epoch` : `${task.epochs} Epochs` }
function formatDate(value) { if (!value) return '--'; const date = new Date(value); return Number.isNaN(date.getTime()) ? '--' : new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(date) }
function formatBytes(value) { if (!Number.isFinite(value)) return '大小未知'; if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`; return `${(value / 1024 ** 2).toFixed(1)} MB` }

async function loadPreview() {
  if (!import.meta.env.DEV) return
  const preview = await import('@/mocks/trainingPreview')
  const result = normalizeTrainingTaskList(preview.trainingPreviewTasks)
  tasks.value = result.items; total.value = result.total; stats.value = normalizeTrainingStats(preview.trainingPreviewStats); statusDistribution.value = deriveTrainingStatusDistribution(stats.value); distributionFallback.value = false; models.value = normalizeTrainingModels(preview.trainingPreviewModels); previewLoaded = true
}

async function loadTasks(background = false) {
  if (isPreviewMode.value) { if (!previewLoaded) await loadPreview(); return }
  if (!background) listLoading.value = true
  listError.value = ''
  try {
    const [taskResult, statResult, distributionResult] = await Promise.allSettled([
      getTrainingTasksApi({ page: page.value, page_size: pageSize }, { silent: true }),
      getTrainingStatsApi({ silent: true }),
      getTrainingStatusDistributionApi({ silent: true }),
    ])
    if (taskResult.status === 'rejected') throw taskResult.reason
    const normalized = normalizeTrainingTaskList(taskResult.value)
    tasks.value = normalized.items; total.value = normalized.total; page.value = normalized.page
    stats.value = statResult.status === 'fulfilled' ? normalizeTrainingStats(statResult.value) : deriveTrainingStats(tasks.value, total.value)
    statusDistribution.value = distributionResult.status === 'fulfilled'
      ? normalizeTrainingStatusDistribution(distributionResult.value)
      : deriveTrainingStatusDistribution(stats.value)
    distributionFallback.value = distributionResult.status === 'rejected'
    syncPolling()
  } catch { if (!background) listError.value = '没有读取到训练任务列表，请稍后重试。' }
  finally { if (!background) listLoading.value = false }
}

async function loadModels() {
  if (isPreviewMode.value) { if (!previewLoaded) await loadPreview(); return }
  modelsLoading.value = true; modelsError.value = ''
  try { models.value = normalizeTrainingModels(await getTrainingModelsApi({ silent: true })) }
  catch { modelsError.value = '模型列表暂时不可用。' }
  finally { modelsLoading.value = false }
}

function loadAll() { loadTasks(); loadModels() }
function changePage(next) { if (next < 1 || next > totalPages.value) return; page.value = next; loadTasks() }
function syncPolling() { const shouldPoll = !isPreviewMode.value && tasks.value.some((task) => task.status === 'running'); if (shouldPoll && !pollTimer) { pollingActive.value = true; pollTimer = window.setInterval(() => loadTasks(true), 5000) } else if (!shouldPoll && pollTimer) { window.clearInterval(pollTimer); pollTimer = null; pollingActive.value = false } }
function openCreate() { createForm.value = defaultCreateForm(); createError.value = ''; createVisible.value = true }

async function submitCreate() {
  const form = createForm.value
  if (!form.modelName || !form.dataYaml || ![form.epochs, form.imgSize, form.batchSize].every((value) => Number.isInteger(value) && value > 0)) { createError.value = '请填写完整配置，并确保数值为大于 0 的整数。'; return }
  creating.value = true; createError.value = ''
  try {
    const created = normalizeTrainingTaskDetail(await createTrainingTaskApi({ model_name: form.modelName, data_yaml: form.dataYaml, epochs: form.epochs, img_size: form.imgSize, batch_size: form.batchSize }))
    if (form.autoStart && created.uuid) await startTrainingTaskApi(created.uuid)
    else if (form.autoStart && !created.uuid) ElMessage.warning('任务已创建，但响应中没有任务编号，无法自动启动')
    ElMessage.success(form.autoStart && created.uuid ? '训练任务已创建并启动' : '训练任务已创建')
    createVisible.value = false; page.value = 1; await loadTasks()
  } catch { createError.value = '训练任务创建失败，请检查配置或稍后重试。' }
  finally { creating.value = false }
}

async function startTask(task) { actionTaskId.value = task.uuid; try { await startTrainingTaskApi(task.uuid); ElMessage.success('训练任务已启动'); await loadTasks(true) } catch { ElMessage.error('训练任务启动失败') } finally { actionTaskId.value = '' } }
async function pauseTask(task) {
  try {
    await ElMessageBox.confirm('当前文档没有提供恢复训练接口。暂停后可能无法在前端恢复，仍要继续吗？', '确认暂停训练', { type: 'warning', confirmButtonText: '确认暂停', cancelButtonText: '取消' })
    actionTaskId.value = task.uuid; await pauseTrainingTaskApi(task.uuid); ElMessage.success('训练任务已暂停'); await loadTasks(true)
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error('训练任务暂停失败') }
  finally { actionTaskId.value = '' }
}

async function openDetail(task) { selectedTask.value = task; metrics.value = null; detailVisible.value = true; await loadDetail(task.uuid) }
async function loadDetail(uuid) {
  detailLoading.value = true; detailError.value = ''; metricsError.value = ''
  try {
    if (isPreviewMode.value) {
      const preview = await import('@/mocks/trainingPreview'); selectedTask.value = tasks.value.find((task) => task.uuid === uuid) || selectedTask.value; metrics.value = normalizeTrainingMetrics(preview.trainingPreviewMetrics)
    } else {
      const [taskResult, metricResult] = await Promise.allSettled([getTrainingTaskApi(uuid, { silent: true }), getTrainingMetricsApi(uuid, { silent: true })])
      if (taskResult.status === 'rejected') throw taskResult.reason
      selectedTask.value = normalizeTrainingTaskDetail(taskResult.value)
      if (metricResult.status === 'fulfilled') metrics.value = normalizeTrainingMetrics(metricResult.value)
      else metricsError.value = '当前任务尚无可读取的指标数据。'
    }
  } catch { detailError.value = '训练任务详情暂时无法读取。' }
  finally { detailLoading.value = false }
}

async function removeModel(model) {
  try {
    await ElMessageBox.confirm(`删除模型“${model.name}”后无法恢复，是否继续？`, '确认删除模型', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
    deletingModel.value = model.name; await deleteTrainingModelApi(model.name); ElMessage.success('模型已删除'); await loadModels()
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error('模型删除失败') }
  finally { deletingModel.value = '' }
}

onMounted(loadAll)
onBeforeUnmount(() => { if (pollTimer) window.clearInterval(pollTimer) })
</script>

<style lang="scss" scoped>
.training-page { padding-bottom: 36px; }
.preview-notice { margin-bottom: 18px; padding: 13px 15px; display: flex; align-items: center; gap: 11px; color: var(--primary); border-color: rgba(159,226,75,.24); }
.preview-notice div { display: grid; gap: 2px; }.preview-notice b { color: var(--text); font-size: .8rem; }.preview-notice p { margin: 0; color: var(--muted); font-size: .7rem; }
.page-head { margin-bottom: 22px; display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; }.page-head .status-chip { margin-bottom: 15px; }.head-actions { display: flex; gap: 8px; }
.primary-action,.secondary-action { min-height: 44px; padding: 0 15px; display: inline-flex; align-items: center; justify-content: center; gap: 7px; border-radius: 9px; font-weight: 600; transition: background 180ms var(--ease-out),border-color 180ms var(--ease-out),transform 180ms var(--ease-out); }
.primary-action { color:#11160f;background:var(--primary);border:1px solid var(--primary); }.primary-action:hover:not(:disabled){background:var(--primary-hover)}.secondary-action{color:var(--text-secondary);background:var(--surface);border:1px solid var(--border)}.secondary-action:hover:not(:disabled){color:var(--primary);border-color:rgba(159,226,75,.3)}.primary-action:active:not(:disabled),.secondary-action:active:not(:disabled){transform:scale(.98)}.primary-action:disabled,.secondary-action:disabled{opacity:.45}
.stats-grid { display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px; }.stat-card{min-height:140px;padding:15px;display:flex;flex-direction:column}.stat-card>span{width:36px;height:36px;display:grid;place-items:center;color:var(--text-secondary);background:var(--surface-soft);border-radius:9px}.stat-card>span.active{color:var(--accent);background:rgba(240,177,92,.1)}.stat-card>span.success{color:var(--primary);background:var(--primary-soft)}.stat-card>span.danger{color:#ff938d;background:rgba(240,103,95,.09)}.stat-card>strong{margin:auto 0 8px;font-family:"Barlow Condensed";font-size:2.25rem;line-height:1}.stat-card>div{display:grid;gap:2px}.stat-card b{font-size:.72rem}.stat-card small{color:var(--muted);font-size:.62rem}
.training-distribution{margin-top:12px;padding:18px 20px}.training-distribution>header{display:flex;align-items:flex-end;justify-content:space-between;gap:16px}.training-distribution>header>div>span{color:var(--primary);font-size:.66rem;font-weight:600;text-transform:uppercase}.training-distribution>header h2{margin-top:4px}.training-distribution>header p{margin:0;color:var(--muted);font-size:.64rem}.training-distribution>header p strong{color:var(--text);font-family:"Barlow Condensed";font-size:1.3rem}.training-distribution ul{margin:17px 0 0;padding:0;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px;list-style:none}.training-distribution li{min-width:0}.training-distribution li>div{margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;gap:8px}.training-distribution li>div>span:last-child{display:flex;align-items:baseline;gap:5px}.training-distribution li strong{font-size:.67rem}.training-distribution li small{color:var(--muted);font-size:.58rem}.distribution-track{height:7px;display:block;overflow:hidden;background:var(--canvas-soft);border-radius:7px}.distribution-track i{height:100%;display:block;background:var(--text-secondary);border-radius:inherit;transition:width 260ms var(--ease-out)}.distribution-track i.active{background:var(--accent)}.distribution-track i.success{background:var(--primary)}.distribution-track i.danger{background:var(--danger)}.distribution-track i.paused{background:#8e7bd9}.distribution-empty{min-height:80px;display:grid;place-content:center;color:var(--muted);font-size:.68rem}
.task-panel,.model-panel{margin-top:12px;padding:20px}.panel-heading{margin-bottom:16px;display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.panel-heading>div:first-child>span{color:var(--primary);font-size:.66rem;font-weight:600;text-transform:uppercase}.panel-heading h2{margin-top:4px}.sync-state{min-height:32px;padding:0 9px;display:inline-flex;align-items:center;gap:6px;color:var(--muted);background:var(--canvas-soft);border-radius:7px;font-size:.64rem}.sync-state.active{color:var(--primary)}
.desktop-table{overflow-x:auto}table{width:100%;border-collapse:collapse}th{padding:10px;color:var(--muted);border-bottom:1px solid var(--border);font-size:.64rem;text-align:left}td{padding:13px 10px;border-bottom:1px solid rgba(255,255,255,.055);font-size:.7rem;vertical-align:middle}tbody tr:last-child td{border-bottom:0}.task-identity{min-width:170px;display:flex;align-items:center;gap:9px}.task-identity>span{width:36px;height:36px;flex:0 0 auto;display:grid;place-items:center;color:var(--primary);background:var(--primary-soft);border-radius:9px}.task-identity>div,.config-cell{display:grid;gap:3px}.task-identity b,.config-cell b{color:var(--text);font-size:.72rem}.task-identity small{max-width:170px;overflow:hidden;color:var(--muted);font-size:.61rem;text-overflow:ellipsis;white-space:nowrap}.config-cell small{color:var(--muted);font-size:.61rem;white-space:nowrap}.status-tag{display:inline-flex;align-items:center;gap:6px;color:var(--muted);font-size:.64rem;white-space:nowrap}.status-tag i{width:7px;height:7px;background:currentColor;border-radius:50%}.status-tag.active{color:var(--accent)}.status-tag.success{color:var(--primary)}.status-tag.danger{color:#ff938d}.status-tag.paused{color:#b7a5ff}.progress-cell{min-width:150px;display:grid;gap:7px}.progress-cell>div,.mobile-progress>div{display:flex;justify-content:space-between;gap:9px}.progress-cell strong,.mobile-progress strong{color:var(--text);font-size:.7rem}.progress-cell small,.mobile-progress small{color:var(--muted);font-size:.6rem}.progress-cell>span,.mobile-progress>span{height:6px;display:block;overflow:hidden;background:var(--canvas-soft);border-radius:6px}.progress-cell i,.mobile-progress i{height:100%;display:block;background:var(--primary);border-radius:inherit;transition:width 260ms var(--ease-out)}time{color:var(--muted);white-space:nowrap}.row-actions{display:flex;justify-content:flex-end;gap:4px}.row-actions button{min-height:38px;padding:0 8px;display:inline-flex;align-items:center;gap:5px;color:var(--text-secondary);background:transparent;border:1px solid transparent;border-radius:8px;font-size:.64rem}.row-actions button:hover:not(:disabled){color:var(--primary);background:var(--primary-soft)}.row-actions button.warning:hover:not(:disabled){color:var(--accent);background:rgba(240,177,92,.09)}.row-actions button:disabled{opacity:.34}.mobile-cards{display:none}
.pagination-bar{margin-top:12px;padding-top:13px;display:flex;align-items:center;justify-content:flex-end;gap:16px;color:var(--muted);border-top:1px solid var(--border);font-size:.65rem}.pagination-bar>div{display:flex;gap:6px}.pagination-bar button,.icon-action{width:40px;height:40px;display:grid;place-items:center;color:var(--text-secondary);background:var(--surface-soft);border:1px solid var(--border);border-radius:8px}.pagination-bar button:disabled{opacity:.35}.model-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.model-card{min-height:78px;padding:13px;display:grid;grid-template-columns:38px minmax(0,1fr) 38px;align-items:center;gap:10px;background:var(--canvas-soft);border:1px solid var(--border);border-radius:11px}.model-card>span{width:38px;height:38px;display:grid;place-items:center;color:var(--primary);background:var(--primary-soft);border-radius:9px}.model-card>div{min-width:0;display:grid;gap:4px}.model-card b{overflow:hidden;font-size:.7rem;text-overflow:ellipsis;white-space:nowrap}.model-card small{color:var(--muted);font-size:.6rem}.model-card>button{width:38px;height:38px;display:grid;place-items:center;color:var(--muted);background:transparent;border:1px solid transparent;border-radius:8px}.model-card>button:hover:not(:disabled){color:#ff938d;background:rgba(240,103,95,.08)}.model-card.skeleton{display:block;min-height:78px}.model-error{min-height:90px;display:flex;align-items:center;justify-content:center;gap:7px;color:#ff938d;font-size:.7rem}.model-error button{color:var(--primary);background:transparent;border:0;text-decoration:underline}.model-empty{min-height:100px;display:grid;place-content:center;color:var(--muted);font-size:.7rem}
.feedback-state{min-height:280px;display:grid;place-content:center;justify-items:center;color:var(--muted);text-align:center}.feedback-state h3{margin:12px 0 5px;color:var(--text);font-family:"Barlow Condensed";font-size:1.5rem}.feedback-state p{margin:0 0 17px;color:var(--muted)}.error-state{color:var(--danger)}.loading-list{display:grid}.loading-row{min-height:66px;padding:10px;display:grid;grid-template-columns:1.2fr .5fr .8fr .4fr;align-items:center;gap:15px;border-bottom:1px solid var(--border)}.skeleton{height:13px;background:linear-gradient(100deg,var(--surface-soft) 20%,var(--surface-raised) 36%,var(--surface-soft) 52%);background-size:200% 100%;border-radius:6px;animation:shimmer 1.35s linear infinite}.skeleton.wide{width:76%}.skeleton.short{width:55%}
:global(.training-dialog.el-dialog){--el-dialog-bg-color:var(--surface);overflow:hidden;background:var(--surface);border:1px solid var(--border);border-radius:16px;box-shadow:var(--shadow)}:global(.training-dialog .el-dialog__header){margin:0;padding:18px 20px;border-bottom:1px solid var(--border)}:global(.training-dialog .el-dialog__headerbtn){top:14px;right:12px;width:44px;height:44px}:global(.training-dialog .el-dialog__close){color:var(--muted)}:global(.training-dialog .el-dialog__body){padding:20px;color:var(--text-secondary)}:global(.training-dialog .el-dialog__footer){padding:0 20px 20px}.dialog-title{display:flex;align-items:center;gap:10px}.dialog-title>span{width:36px;height:36px;display:grid;place-items:center;color:var(--primary);background:var(--primary-soft);border-radius:9px}.dialog-title>div{display:grid;gap:2px}.dialog-title b{color:var(--text);font-size:.8rem}.dialog-title small{color:var(--muted);font-size:.65rem}.create-form{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.create-form label{display:grid;gap:7px;color:var(--text-secondary);font-size:.68rem;font-weight:600}.create-form label:first-child{grid-column:span 3}.create-form .full{grid-column:1/-1}.create-form input:not([type=checkbox]){min-height:44px;width:100%;padding:0 11px;color:var(--text);background:var(--canvas-soft);border:1px solid var(--border);border-radius:9px;outline:0}.create-form input:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-soft)}.create-form label small{color:var(--muted);font-size:.61rem;font-weight:400;line-height:1.5}.auto-start{grid-column:1/-1;min-height:44px;display:flex!important;grid-template-columns:auto 1fr!important;align-items:center}.auto-start input{width:18px;height:18px;accent-color:var(--primary)}.inline-error,.task-error{margin:0;padding:10px 12px;display:flex;align-items:flex-start;gap:7px;color:#ff938d;background:rgba(240,103,95,.08);border-radius:8px;font-size:.67rem;line-height:1.5}.dialog-actions{display:flex;justify-content:flex-end;gap:8px}.dialog-loading{min-height:260px;display:grid;place-content:center;justify-items:center;gap:10px;color:var(--primary)}.dialog-loading span{color:var(--muted);font-size:.68rem}.dialog-error{min-height:220px;display:flex;align-items:center;justify-content:center;gap:8px;color:#ff938d}.dialog-error button{color:var(--primary);background:transparent;border:0;text-decoration:underline}.detail-summary{padding:15px;display:flex;align-items:center;justify-content:space-between;gap:16px;background:var(--canvas-soft);border-radius:12px}.detail-summary h3{margin:8px 0 2px;color:var(--text);font-family:"Barlow Condensed";font-size:1.45rem}.detail-summary p{margin:0;color:var(--muted);font-size:.62rem}.detail-summary>strong{font-family:"Barlow Condensed";font-size:2.3rem}.detail-grid{margin:12px 0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;overflow:hidden;background:var(--border);border:1px solid var(--border);border-radius:11px}.detail-grid>div{min-height:70px;padding:12px;display:grid;align-content:center;gap:5px;background:var(--surface)}.detail-grid dt{color:var(--muted);font-size:.61rem}.detail-grid dd{margin:0;overflow-wrap:anywhere;color:var(--text-secondary);font-size:.7rem}.metrics-content{margin-top:15px}.final-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}.final-metrics article{min-height:72px;padding:12px;display:grid;align-content:center;gap:5px;background:var(--canvas-soft);border-radius:10px}.final-metrics small{color:var(--muted);font-size:.61rem}.final-metrics strong{font-family:"Barlow Condensed";font-size:1.45rem}.charts-grid{margin-top:8px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.metrics-empty{min-height:200px;display:grid;place-content:center;justify-items:center;gap:8px;color:var(--muted)}.metrics-empty p{margin:0;font-size:.68rem}.sr-only{position:absolute;width:1px;height:1px;padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.spin{animation:spin 800ms linear infinite}
@keyframes shimmer{to{background-position-x:-200%}}@keyframes spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.skeleton,.spin{animation:none}.progress-cell i,.distribution-track i,.primary-action,.secondary-action{transition:none}}
@media(max-width:1180px){.stats-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.training-distribution ul{grid-template-columns:repeat(3,minmax(0,1fr))}.model-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.charts-grid{grid-template-columns:1fr}}
@media(max-width:760px){.page-head{align-items:stretch;flex-direction:column}.head-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.desktop-table{display:none}.mobile-cards{display:grid;gap:8px}.task-card{padding:14px;background:var(--canvas-soft);border:1px solid var(--border);border-radius:12px}.task-card>header{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.mobile-progress{margin:14px 0;display:grid;gap:7px}.task-card dl{margin:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.task-card dl div{display:grid;gap:3px}.task-card dt{color:var(--muted);font-size:.59rem}.task-card dd{margin:0;color:var(--text-secondary);font-size:.67rem}.task-card footer{margin-top:12px;padding-top:10px;border-top:1px solid var(--border)}.task-card footer button{min-height:42px}.model-grid{grid-template-columns:1fr}.detail-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.final-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:520px){.preview-notice{align-items:flex-start}.stats-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.stat-card{min-height:132px}.training-distribution{padding:15px 14px}.training-distribution>header{align-items:flex-start;flex-direction:column}.training-distribution ul{grid-template-columns:1fr}.task-panel,.model-panel{padding:14px}.panel-heading{align-items:flex-start;flex-direction:column}.sync-state{align-self:flex-start}.create-form{grid-template-columns:1fr}.create-form label,.create-form label:first-child,.create-form .full{grid-column:1}.detail-grid{grid-template-columns:1fr}.detail-summary{align-items:flex-start}.detail-summary>strong{font-size:1.8rem}.final-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
