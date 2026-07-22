<template>
  <div class="page-shell scan-page">
    <header class="page-head">
      <div>
        <span class="status-chip"><ScanSmiley :size="16" weight="bold" /> AI 餐食识别</span>
        <h1 class="page-title">拍下这一餐，看清画面里的食物。</h1>
        <p class="page-description">上传 JPG、PNG 或 WEBP 图片，识别并标出照片里的食物；也可以只把原图保存到个人影像库。</p>
      </div>
    </header>

    <section class="scan-grid" aria-label="上传餐食照片">
      <div class="upload-side surface">
        <input
          ref="fileInput"
          class="sr-only"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          @change="selectFile"
        />

        <button
          v-if="!previewUrl"
          type="button"
          class="drop-zone"
          @click="fileInput?.click()"
          @dragover.prevent
          @drop.prevent="selectDroppedFile"
        >
          <span><CameraPlus :size="34" weight="duotone" /></span>
          <b>拍照或从相册选择</b>
          <p>手机端可选择使用相机拍摄或从相册添加；电脑端也可以把图片拖到这里。支持 JPG、PNG、WEBP，文件不超过 10 MB。</p>
        </button>

        <div v-else class="preview">
          <img :src="previewUrl" alt="准备检测的餐食照片" @load="handlePreviewLoad" />
          <svg
            v-if="detectionResult && imageWidth && imageHeight"
            class="detection-overlay"
            :viewBox="`0 0 ${imageWidth} ${imageHeight}`"
            preserveAspectRatio="xMidYMid meet"
            aria-hidden="true"
          >
            <g v-for="(item, index) in detectionResult.detections" :key="`${item.className}-${index}`">
              <rect v-if="item.bbox"
                :x="item.bbox[0]" :y="item.bbox[1]"
                :width="Math.max(0, item.bbox[2] - item.bbox[0])"
                :height="Math.max(0, item.bbox[3] - item.bbox[1])"
                :class="{ 'low-confidence': item.lowConfidence }"
              />
            </g>
          </svg>
          <button type="button" aria-label="重新拍摄或从相册选择照片" @click="fileInput?.click()">
            <ArrowsClockwise :size="19" weight="bold" />
          </button>
        </div>

        <div class="detection-settings">
          <label>
            <span>检测场景</span>
            <select v-model.number="sceneId" :disabled="scenesLoading || detecting">
              <option v-for="scene in scenes" :key="scene.id" :value="scene.id">{{ scene.name }}</option>
            </select>
          </label>
          <button type="button" :aria-expanded="advancedOpen" @click="advancedOpen = !advancedOpen">
            <SlidersHorizontal :size="18" />高级参数
          </button>
          <div v-if="advancedOpen" class="thresholds">
            <label><span>置信度阈值 <b>{{ Math.round(confThreshold * 100) }}%</b></span><input v-model.number="confThreshold" type="range" min="0.05" max="0.95" step="0.05"></label>
            <label><span>IoU 阈值 <b>{{ Math.round(iouThreshold * 100) }}%</b></span><input v-model.number="iouThreshold" type="range" min="0.05" max="0.95" step="0.05"></label>
          </div>
        </div>

        <p v-if="uploadError" class="inline-error" role="alert">{{ uploadError }}</p>

        <div class="scan-actions">
          <div>
            <small>当前文件</small>
            <b>{{ selectedFile?.name || '尚未选择' }}</b>
          </div>
          <div class="action-buttons">
            <button v-if="selectedFile" type="button" class="clear-button" :disabled="detecting || uploading" @click="clearSelection">取消</button>
            <button type="button" class="save-button" :disabled="!selectedFile || detecting || uploading" @click="savePhoto">
              <CircleNotch v-if="uploading" class="spin" :size="17" />{{ uploading ? '保存中' : '仅保存原图' }}
            </button>
            <FuelButton :disabled="!selectedFile || uploading" :loading="detecting" @click="detectPhoto">识别照片</FuelButton>
          </div>
        </div>
      </div>

      <aside class="capability-side surface">
        <div class="capability-icon"><CloudCheck :size="25" weight="duotone" /></div>
        <h2 class="section-title">上传后，你可以</h2>
        <p>选择保存到餐食记录，或直接识别照片内容；两项操作互不影响。</p>
        <ul>
          <li><ImagesSquare :size="20" weight="duotone" /><span><b>保存餐食照片</b><small>原图会同步至账户，方便以后回看</small></span></li>
          <li><ClockCounterClockwise :size="20" weight="duotone" /><span><b>回顾历史餐食</b><small>在拍照记录中查看之前保存的照片</small></span></li>
          <li><ScanSmiley :size="20" weight="duotone" /><span><b>识别照片内容</b><small>自动标出识别到的食物，并显示参考可信度</small></span></li>
        </ul>
      </aside>
    </section>

    <section v-if="detectionResult" class="result-section surface" aria-labelledby="result-title" aria-live="polite">
      <header class="result-head">
        <div><span><Crosshair :size="17" weight="bold" /> 识别概览</span><h2 id="result-title" class="section-title">识别结果</h2></div>
        <dl><div><dt>识别数量</dt><dd>{{ detectionResult.totalObjects }}</dd></div><div><dt>处理耗时</dt><dd>{{ formatInferenceTime(detectionResult.inferenceTime) }}</dd></div></dl>
      </header>
      <p v-if="!detectionResult.detections.length" class="no-detection">暂时没有识别到照片内容。你可以换一张更清晰的照片，或在高级参数中降低可信度阈值后重试。</p>
      <div v-else class="detection-list">
        <article v-for="(item, index) in detectionResult.detections" :key="`${item.className}-${index}`">
          <span class="target-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <div><b>{{ item.classNameCn || item.className || '未知类别' }}</b><small>{{ item.className || 'unknown' }}</small></div>
          <div class="confidence-value"><small>参考可信度</small><strong>{{ formatConfidence(item.confidence) }}</strong></div>
          <span v-if="item.lowConfidence" class="confidence-warning">低置信度</span>
        </article>
      </div>
      <details class="result-technical">
        <summary>查看技术详情</summary>
        <p>任务编号：<code>{{ detectionResult.taskUuid || '未返回' }}</code></p>
      </details>
    </section>

    <section class="history-section surface" aria-labelledby="history-title">
      <header class="history-head">
        <div>
          <h2 id="history-title" class="section-title">我的上传历史</h2>
          <p>{{ historySummary }}</p>
        </div>
        <button type="button" class="refresh-button" :disabled="historyLoading" @click="loadHistory">
          <ArrowsClockwise :size="18" weight="bold" />
          刷新
        </button>
      </header>

      <div v-if="historyLoading" class="history-grid" aria-label="正在加载上传历史">
        <article v-for="index in pageSize" :key="index" class="history-card skeleton-card" aria-hidden="true">
          <div class="skeleton-image" />
          <div class="skeleton-line wide" />
          <div class="skeleton-line" />
        </article>
      </div>

      <div v-else-if="historyError" class="state-panel" role="alert">
        <WarningCircle :size="32" weight="duotone" />
        <h3>暂时无法读取影像库</h3>
        <p>{{ historyError }}</p>
        <button type="button" @click="loadHistory">重新加载</button>
      </div>

      <div v-else-if="!historyItems.length" class="state-panel empty-state">
        <ImagesSquare :size="36" weight="duotone" />
        <h3>还没有保存照片</h3>
        <p>上传第一张餐食照片后，它会出现在这里。</p>
        <button type="button" @click="fileInput?.click()">选择照片</button>
      </div>

      <div v-else class="history-grid">
        <article v-for="item in historyItems" :key="item.id" class="history-card">
          <button
            type="button"
            class="history-image"
            :disabled="!item.previewUrl"
            :aria-label="`查看 ${item.displayName}`"
            @click="openPreview(item)"
          >
            <img v-if="item.previewUrl" :src="item.previewUrl" :alt="item.displayName" />
            <span v-else-if="item.previewError" class="image-fallback"><ImageBroken :size="27" /><small>图片无法加载</small></span>
            <span v-else class="image-loading" aria-label="正在加载图片" />
          </button>
          <div class="history-meta">
            <div>
              <b :title="item.displayName">{{ item.displayName }}</b>
              <small>{{ formatDate(item.createdAt) }}<template v-if="item.size"> · {{ formatBytes(item.size) }}</template></small>
            </div>
            <button type="button" class="delete-button" :disabled="deletingId === item.id" :aria-label="`删除 ${item.displayName}`" @click="removePhoto(item)">
              <CircleNotch v-if="deletingId === item.id" class="spin" :size="18" weight="bold" />
              <Trash v-else :size="18" weight="bold" />
            </button>
          </div>
        </article>
      </div>

      <footer v-if="totalPages > 1 && !historyLoading && !historyError" class="pagination">
        <button type="button" :disabled="page <= 1" @click="changePage(page - 1)"><CaretLeft :size="17" weight="bold" /> 上一页</button>
        <span>第 {{ page }} / {{ totalPages }} 页</span>
        <button type="button" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页 <CaretRight :size="17" weight="bold" /></button>
      </footer>
    </section>

    <el-dialog v-model="previewVisible" class="scan-preview-dialog" width="min(880px, calc(100% - 32px))" align-center>
      <template #header>
        <div class="dialog-heading">
          <b>{{ previewItem?.displayName }}</b>
          <small>{{ formatDate(previewItem?.createdAt) }}</small>
        </div>
      </template>
      <img v-if="previewItem?.previewUrl" class="dialog-image" :src="previewItem.previewUrl" :alt="previewItem.displayName" />
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  PhArrowsClockwise as ArrowsClockwise, PhCameraPlus as CameraPlus,
  PhCaretLeft as CaretLeft, PhCaretRight as CaretRight, PhCircleNotch as CircleNotch,
  PhClockCounterClockwise as ClockCounterClockwise, PhCloudCheck as CloudCheck, PhCrosshair as Crosshair,
  PhImageBroken as ImageBroken, PhImagesSquare as ImagesSquare, PhScanSmiley as ScanSmiley,
  PhSlidersHorizontal as SlidersHorizontal, PhTrash as Trash, PhWarningCircle as WarningCircle,
} from '@phosphor-icons/vue'
import FuelButton from '@/components/ui/FuelButton.vue'
import { captureImageApi, deleteCameraImageApi, getCameraHistoryApi, getCameraImageApi } from '@/api/camera'
import { detectImageApi, getDetectionScenesApi } from '@/api/detection'
import { useUserStore } from '@/stores/user'
import { normalizeCameraHistory, normalizeCameraItem } from '@/utils/cameraData'
import { normalizeDetectionResult, normalizeDetectionScenes } from '@/utils/detectionTaskData'

const pageSize = 8
const fileInput = ref(null)
const selectedFile = ref(null)
const previewUrl = ref('')
const uploading = ref(false)
const detecting = ref(false)
const uploadError = ref('')
const detectionResult = ref(null)
const imageWidth = ref(0)
const imageHeight = ref(0)
const scenes = ref([{ id: 1, name: '默认场景' }])
const sceneId = ref(1)
const scenesLoading = ref(false)
const advancedOpen = ref(false)
const confThreshold = ref(.25)
const iouThreshold = ref(.45)
const historyLoading = ref(true)
const historyError = ref('')
const historyItems = ref([])
const page = ref(1)
const total = ref(0)
const deletingId = ref('')
const previewVisible = ref(false)
const previewItem = ref(null)
const userStore = useUserStore()
let historyGeneration = 0

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const historySummary = computed(() => {
  if (historyLoading.value) return '正在同步你的餐食影像'
  if (!total.value) return '照片只对当前账户可见'
  return `共保存 ${total.value} 张照片，只对当前账户可见`
})

function applyFile(file) {
  if (!file) return
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    ElMessage.warning('只支持 JPG、PNG 或 WEBP 图片')
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.warning('图片大小不能超过 10 MB')
    return
  }
  clearSelection()
  selectedFile.value = file
  previewUrl.value = URL.createObjectURL(file)
  uploadError.value = ''
}

function selectFile(event) {
  applyFile(event.target.files?.[0])
  event.target.value = ''
}

function selectDroppedFile(event) {
  applyFile(event.dataTransfer?.files?.[0])
}

function clearSelection() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  selectedFile.value = null
  uploadError.value = ''
  detectionResult.value = null
  imageWidth.value = 0
  imageHeight.value = 0
}

function handlePreviewLoad(event) {
  imageWidth.value = event.target?.naturalWidth || 0
  imageHeight.value = event.target?.naturalHeight || 0
}

async function loadScenes() {
  if (userStore.isDemo) return
  scenesLoading.value = true
  try {
    const items = normalizeDetectionScenes(await getDetectionScenesApi({ silent: true }))
    if (items.length) {
      scenes.value = items
      if (!items.some((item) => item.id === sceneId.value)) sceneId.value = items[0].id
    }
  } catch {
    scenes.value = [{ id: 1, name: '默认场景' }]
  } finally {
    scenesLoading.value = false
  }
}

async function detectPhoto() {
  if (!selectedFile.value) return
  detecting.value = true
  uploadError.value = ''
  detectionResult.value = null
  try {
    if (userStore.isDemo) {
      await new Promise((resolve) => window.setTimeout(resolve, 520))
      const width = imageWidth.value || 1200
      const height = imageHeight.value || 800
      detectionResult.value = normalizeDetectionResult({ data: {
        task_uuid: `preview-${Date.now()}`,
        detections: [
          { class_name: 'salad', class_name_cn: '蔬菜沙拉', confidence: .91, bbox: [width * .08, height * .12, width * .58, height * .86] },
          { class_name: 'chicken_breast', class_name_cn: '鸡胸肉', confidence: .78, bbox: [width * .48, height * .28, width * .91, height * .82] },
        ],
        total_objects: 2,
        inference_time: 86,
      } })
      ElMessage.success('体验模式：已生成示例检测结果')
      return
    }
    detectionResult.value = normalizeDetectionResult(await detectImageApi(selectedFile.value, {
      sceneId: sceneId.value,
      confThreshold: confThreshold.value,
      iouThreshold: iouThreshold.value,
    }))
    ElMessage.success(`检测完成，共识别 ${detectionResult.value.totalObjects} 个目标`)
  } catch {
    uploadError.value = '目标检测失败，请检查服务状态或调整图片后重试。'
  } finally {
    detecting.value = false
  }
}

async function savePhoto() {
  if (!selectedFile.value) return
  uploading.value = true
  uploadError.value = ''
  try {
    if (userStore.isDemo) {
      await new Promise((resolve) => window.setTimeout(resolve, 420))
      const localUrl = previewUrl.value
      const demoItem = normalizeCameraItem({
        id: `demo-${Date.now()}`,
        original_name: selectedFile.value.name,
        size: selectedFile.value.size,
        created_at: new Date().toISOString(),
      })
      demoItem.previewUrl = localUrl
      demoItem.previewLoading = false
      previewUrl.value = ''
      selectedFile.value = null
      detectionResult.value = null
      imageWidth.value = 0
      imageHeight.value = 0
      historyItems.value = [demoItem, ...historyItems.value]
      total.value += 1
      ElMessage.success('体验模式：照片已加入当前影像库')
      return
    }

    await captureImageApi(selectedFile.value)
    clearSelection()
    page.value = 1
    ElMessage.success('照片已保存到个人影像库')
    await loadHistory()
  } catch {
    uploadError.value = '照片保存失败，请检查网络后重试。'
  } finally {
    uploading.value = false
  }
}

function releaseHistoryUrls(items = historyItems.value) {
  items.forEach((item) => {
    if (item.previewUrl?.startsWith('blob:')) URL.revokeObjectURL(item.previewUrl)
  })
}

async function loadPreview(item, generation) {
  try {
    const blob = await getCameraImageApi(item.id)
    const url = URL.createObjectURL(blob)
    if (generation !== historyGeneration) {
      URL.revokeObjectURL(url)
      return
    }
    item.previewUrl = url
  } catch {
    item.previewError = true
  } finally {
    item.previewLoading = false
  }
}

async function loadHistory() {
  if (userStore.isDemo) {
    historyLoading.value = false
    historyError.value = ''
    return
  }

  const generation = ++historyGeneration
  historyLoading.value = true
  historyError.value = ''
  try {
    const data = normalizeCameraHistory(await getCameraHistoryApi({ page: page.value, page_size: pageSize }))
    if (generation !== historyGeneration) return
    releaseHistoryUrls()
    historyItems.value = data.items
    total.value = data.total
    page.value = data.page
    historyLoading.value = false
    await Promise.allSettled(historyItems.value.map((item) => loadPreview(item, generation)))
  } catch {
    if (generation !== historyGeneration) return
    historyError.value = '没有读取到照片记录，请稍后重新加载。'
  } finally {
    if (generation === historyGeneration) historyLoading.value = false
  }
}

async function removePhoto(item) {
  try {
    await ElMessageBox.confirm(`删除“${item.displayName}”后无法恢复，是否继续？`, '确认删除照片', {
      type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消',
    })
    deletingId.value = item.id
    if (userStore.isDemo) {
      if (item.previewUrl?.startsWith('blob:')) URL.revokeObjectURL(item.previewUrl)
      historyItems.value = historyItems.value.filter((entry) => entry.id !== item.id)
      total.value = Math.max(0, total.value - 1)
    } else {
      await deleteCameraImageApi(item.id)
      if (historyItems.value.length === 1 && page.value > 1) page.value -= 1
      await loadHistory()
    }
    ElMessage.success(userStore.isDemo ? '体验模式：照片已移除' : '照片已删除')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  } finally {
    deletingId.value = ''
  }
}

function changePage(nextPage) {
  if (nextPage < 1 || nextPage > totalPages.value || nextPage === page.value) return
  page.value = nextPage
  loadHistory()
}

function openPreview(item) {
  if (!item.previewUrl) return
  previewItem.value = item
  previewVisible.value = true
}

function formatBytes(bytes) {
  const value = Number(bytes)
  if (!Number.isFinite(value) || value <= 0) return ''
  if (value < 1024) return `${value} B`
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 ** 2).toFixed(1)} MB`
}

function formatDate(value) {
  if (!value) return '时间未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(date)
}

function formatConfidence(value) {
  const number = Number(value)
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : '--'
}

function formatInferenceTime(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '--'
  return number >= 1000 ? `${(number / 1000).toFixed(2)} s` : `${Math.round(number)} ms`
}

onMounted(() => {
  loadHistory()
  loadScenes()
})

onBeforeUnmount(() => {
  historyGeneration += 1
  clearSelection()
  releaseHistoryUrls()
})
</script>

<style lang="scss" scoped>
.scan-page { padding-bottom: 34px; }
.page-head { margin-bottom: 26px; }
.page-head .status-chip { margin-bottom: 16px; }
.scan-grid { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(310px, .75fr); gap: 18px; }
.upload-side { min-height: 540px; padding: 22px; display: flex; flex-direction: column; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); }
.drop-zone { min-height: 420px; padding: 32px; display: grid; place-content: center; justify-items: center; color: var(--text); background: radial-gradient(circle at 50% 42%, rgba(159, 226, 75, .08), transparent 13rem), var(--canvas-soft); border: 1px dashed var(--border-strong); border-radius: 14px; text-align: center; transition: border-color 200ms var(--ease-out), background 200ms var(--ease-out), transform 180ms var(--ease-out); }
.drop-zone:hover { border-color: var(--primary); background-color: rgba(159, 226, 75, .03); }
.drop-zone:active { transform: scale(.995); }
.drop-zone > span { width: 70px; height: 70px; margin-bottom: 18px; display: grid; place-items: center; color: var(--primary); background: var(--primary-soft); border-radius: 17px; }
.drop-zone b { font-family: "Barlow Condensed", MiSans, sans-serif; font-size: 1.75rem; }
.drop-zone p { max-width: 44ch; margin: 9px 0 0; color: var(--muted); line-height: 1.6; }
.preview { position: relative; min-height: 420px; overflow: hidden; background: #080b0a; border: 1px solid var(--border); border-radius: 14px; }
.preview img { width: 100%; height: 420px; display: block; object-fit: contain; }
.detection-overlay { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.detection-overlay rect { fill: rgba(159, 226, 75, .08); stroke: var(--primary); stroke-width: 4; vector-effect: non-scaling-stroke; }
.detection-overlay rect.low-confidence { fill: rgba(246, 173, 85, .08); stroke: var(--warning); stroke-dasharray: 9 6; }
.preview button { position: absolute; top: 14px; right: 14px; width: 46px; height: 46px; display: grid; place-items: center; color: var(--text); background: rgba(13, 16, 15, .86); border: 1px solid var(--border-strong); border-radius: 10px; backdrop-filter: blur(10px); }
.detection-settings { margin-top: 14px; padding: 13px; display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: 12px; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 12px; }
.detection-settings > label, .thresholds label { display: grid; gap: 7px; color: var(--muted); font-size: .68rem; }
.detection-settings select { min-height: 44px; padding: 0 12px; color: var(--text); background: var(--surface-soft); border: 1px solid var(--border-strong); border-radius: 9px; }
.detection-settings > button { min-height: 44px; padding: 0 13px; display: inline-flex; align-items: center; justify-content: center; gap: 7px; color: var(--text-secondary); background: transparent; border: 1px solid var(--border-strong); border-radius: 9px; }
.detection-settings > button:hover { color: var(--primary); border-color: var(--primary); }
.thresholds { grid-column: 1 / -1; padding-top: 4px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.thresholds label span { display: flex; justify-content: space-between; }
.thresholds label b { color: var(--primary); }
.thresholds input { width: 100%; accent-color: var(--primary); }
.inline-error { margin: 12px 0 0; padding: 11px 13px; color: #ffc8c8; background: rgba(231, 76, 60, .09); border: 1px solid rgba(231, 76, 60, .24); border-radius: 10px; font-size: .78rem; }
.scan-actions { margin-top: 18px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.scan-actions > div:first-child { min-width: 0; display: grid; gap: 4px; }
.scan-actions small { color: var(--muted); font-size: .7rem; }
.scan-actions b { max-width: 360px; overflow: hidden; font-size: .82rem; text-overflow: ellipsis; white-space: nowrap; }
.action-buttons { display: flex; align-items: center; gap: 9px; }
.clear-button, .save-button, .refresh-button, .pagination button, .state-panel button { min-height: 42px; padding: 0 14px; color: var(--text-secondary); background: transparent; border: 1px solid var(--border-strong); border-radius: 10px; font-weight: 600; transition: color 180ms var(--ease-out), border-color 180ms var(--ease-out), transform 180ms var(--ease-out); }
.save-button { display: inline-flex; align-items: center; justify-content: center; gap: 7px; color: var(--text); background: var(--surface-soft); }
.clear-button:hover:not(:disabled), .save-button:hover:not(:disabled), .refresh-button:hover, .pagination button:hover:not(:disabled), .state-panel button:hover { color: var(--primary); border-color: var(--primary); }
.clear-button:active, .refresh-button:active, .pagination button:active, .state-panel button:active { transform: scale(.98); }
.clear-button:disabled, .save-button:disabled { cursor: not-allowed; opacity: .45; }
.capability-side { padding: 28px; }
.capability-icon { width: 52px; height: 52px; margin-bottom: 22px; display: grid; place-items: center; color: var(--primary); background: var(--primary-soft); border-radius: 13px; }
.capability-side > p { margin: 8px 0 26px; color: var(--muted); font-size: .82rem; line-height: 1.65; }
.capability-side ul { margin: 0; padding: 0; display: grid; list-style: none; }
.capability-side li { padding: 17px 0; display: grid; grid-template-columns: 24px 1fr; align-items: start; gap: 11px; color: var(--primary); border-bottom: 1px solid var(--border); }
.capability-side li:last-child { border-bottom: 0; }
.capability-side li.pending { color: var(--warning); }
.capability-side li span { display: grid; gap: 4px; }
.capability-side li b { color: var(--text); font-size: .84rem; }
.capability-side li small { color: var(--muted); font-size: .72rem; }
.result-section { margin-top: 18px; padding: clamp(20px, 3vw, 30px); }
.result-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 22px; }
.result-head > div > span { margin-bottom: 5px; display: inline-flex; align-items: center; gap: 7px; color: var(--primary); font-size: .66rem; font-weight: 700; text-transform: uppercase; }
.result-head dl { margin: 0; display: flex; gap: 10px; }
.result-head dl div { min-width: 100px; padding: 10px 13px; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 10px; }
.result-head dt { color: var(--muted); font-size: .62rem; }
.result-head dd { margin: 3px 0 0; font-family: "Barlow Condensed", MiSans, sans-serif; font-size: 1.22rem; font-weight: 700; }
.detection-list { margin-top: 20px; display: grid; gap: 8px; }
.detection-list article { min-width: 0; padding: 12px 14px; display: grid; grid-template-columns: 38px minmax(120px, 1fr) minmax(86px, auto) auto; align-items: center; gap: 12px; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 11px; }
.target-index { color: var(--primary); font-family: "Barlow Condensed", sans-serif; font-size: 1.12rem; font-weight: 700; }
.detection-list article > div { min-width: 0; display: grid; gap: 2px; }
.detection-list article b { overflow: hidden; font-size: .8rem; text-overflow: ellipsis; white-space: nowrap; }
.detection-list article small { color: var(--muted); font-size: .64rem; }
.detection-list article strong { color: var(--primary); font-family: "Barlow Condensed", sans-serif; font-size: 1.08rem; }
.confidence-value { display: grid; justify-items: end; gap: 2px; }
.confidence-value small { color: var(--muted); font-size: .6rem; }
.confidence-warning { padding: 4px 7px; color: var(--warning); background: rgba(246, 173, 85, .08); border-radius: 6px; font-size: .6rem; }
.result-technical { margin-top: 16px; padding-top: 12px; color: var(--muted); border-top: 1px solid var(--border); font-size: .66rem; }
.result-technical summary { width: fit-content; min-height: 44px; padding: 0 4px; display: flex; align-items: center; cursor: pointer; color: var(--text-secondary); }
.result-technical summary:hover { color: var(--primary); }
.result-technical summary:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.result-technical p { margin: 7px 0 0; }
.result-technical code { color: var(--text-secondary); font-size: .67rem; }
.no-detection { margin: 20px 0 0; padding: 18px; color: var(--muted); background: var(--canvas-soft); border: 1px dashed var(--border-strong); border-radius: 11px; text-align: center; }
.history-section { margin-top: 18px; padding: clamp(20px, 3vw, 30px); }
.history-head { margin-bottom: 22px; display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.history-head p { margin: 7px 0 0; color: var(--muted); font-size: .78rem; }
.refresh-button { display: inline-flex; align-items: center; gap: 8px; }
.refresh-button:disabled, .pagination button:disabled { cursor: not-allowed; opacity: .4; }
.history-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.history-card { min-width: 0; overflow: hidden; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 13px; transition: border-color 180ms var(--ease-out), transform 180ms var(--ease-out); }
.history-card:hover { border-color: var(--border-strong); transform: translateY(-2px); }
.history-image { position: relative; width: 100%; aspect-ratio: 4 / 3; display: grid; place-items: center; overflow: hidden; color: var(--muted); background: var(--surface-soft); border: 0; border-radius: 0; }
.history-image:not(:disabled) { cursor: zoom-in; }
.history-image img { width: 100%; height: 100%; object-fit: cover; transition: transform 320ms var(--ease-out); }
.history-image:hover img { transform: scale(1.035); }
.image-fallback { display: grid; justify-items: center; gap: 7px; }
.image-fallback small { font-size: .68rem; }
.image-loading, .skeleton-image, .skeleton-line { background: linear-gradient(100deg, var(--surface-soft) 20%, var(--surface-raised) 36%, var(--surface-soft) 52%); background-size: 200% 100%; animation: shimmer 1.35s linear infinite; }
.image-loading { width: 100%; height: 100%; }
.history-meta { padding: 13px; display: grid; grid-template-columns: minmax(0, 1fr) 36px; align-items: center; gap: 8px; }
.history-meta > div { min-width: 0; display: grid; gap: 5px; }
.history-meta b { overflow: hidden; font-size: .78rem; text-overflow: ellipsis; white-space: nowrap; }
.history-meta small { color: var(--muted); font-size: .66rem; }
.delete-button { width: 36px; height: 36px; display: grid; place-items: center; color: var(--muted); background: transparent; border: 1px solid transparent; border-radius: 9px; transition: color 180ms var(--ease-out), background 180ms var(--ease-out), border-color 180ms var(--ease-out); }
.delete-button:hover:not(:disabled) { color: #ffc8c8; background: rgba(231, 76, 60, .08); border-color: rgba(231, 76, 60, .22); }
.delete-button:disabled { opacity: .55; }
.state-panel { min-height: 260px; display: grid; place-content: center; justify-items: center; color: var(--warning); text-align: center; }
.state-panel h3 { margin: 14px 0 5px; color: var(--text); font-family: "Barlow Condensed", MiSans, sans-serif; font-size: 1.45rem; }
.state-panel p { max-width: 42ch; margin: 0 0 18px; color: var(--muted); font-size: .78rem; line-height: 1.6; }
.state-panel button { color: var(--text); }
.empty-state { color: var(--primary); }
.skeleton-card { min-height: 230px; }
.skeleton-card:hover { transform: none; }
.skeleton-image { aspect-ratio: 4 / 3; }
.skeleton-line { width: 46%; height: 8px; margin: 0 13px 14px; border-radius: 4px; }
.skeleton-line.wide { width: 70%; margin-top: 16px; }
.pagination { margin-top: 22px; display: flex; align-items: center; justify-content: center; gap: 16px; }
.pagination button { display: inline-flex; align-items: center; gap: 6px; }
.pagination span { color: var(--muted); font-size: .74rem; }
.spin { animation: spin 800ms linear infinite; }

:global(.scan-preview-dialog.el-dialog) { padding: 0; overflow: hidden; background: var(--surface-raised); border: 1px solid var(--border-strong); border-radius: 14px; box-shadow: var(--shadow-lg); }
:global(.scan-preview-dialog .el-dialog__header) { margin: 0; padding: 18px 56px 16px 20px; border-bottom: 1px solid var(--border); }
:global(.scan-preview-dialog .el-dialog__headerbtn) { top: 9px; right: 10px; }
:global(.scan-preview-dialog .el-dialog__close) { color: var(--muted); }
:global(.scan-preview-dialog .el-dialog__body) { padding: 0; }
.dialog-heading { display: grid; gap: 3px; }
.dialog-heading b { color: var(--text); font-size: .84rem; }
.dialog-heading small { color: var(--muted); font-size: .68rem; }
.dialog-image { width: 100%; max-height: 72dvh; display: block; object-fit: contain; background: var(--canvas); }

@keyframes shimmer { to { background-position-x: -200%; } }
@keyframes spin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .history-card, .history-image img, .drop-zone, .clear-button, .refresh-button, .pagination button, .state-panel button { transition: none; }
  .image-loading, .skeleton-image, .skeleton-line, .spin { animation: none; }
}

@media (max-width: 1000px) {
  .scan-grid { grid-template-columns: 1fr; }
  .upload-side { min-height: auto; }
  .history-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

@media (max-width: 720px) {
  .history-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .detection-list article { grid-template-columns: 32px minmax(0, 1fr) 58px; }
  .confidence-warning { grid-column: 2 / -1; justify-self: start; }
}

@media (max-width: 620px) {
  .upload-side { padding: 12px; }
  .drop-zone, .preview, .preview img { min-height: 330px; height: 330px; }
  .scan-actions { align-items: stretch; flex-direction: column; }
  .action-buttons { display: grid; grid-template-columns: auto 1fr 1fr; }
  .action-buttons > :last-child { width: 100%; }
  .detection-settings { grid-template-columns: 1fr; }
  .detection-settings > button { width: 100%; }
  .thresholds { grid-column: auto; grid-template-columns: 1fr; }
  .result-head { align-items: flex-start; flex-direction: column; }
  .result-head dl { width: 100%; }
  .result-head dl div { min-width: 0; flex: 1; }
  .history-section { padding: 17px 12px; }
  .history-head { align-items: flex-start; }
  .refresh-button { min-width: 44px; padding: 0; justify-content: center; font-size: 0; }
  .history-grid { gap: 8px; }
  .history-meta { padding: 10px; grid-template-columns: minmax(0, 1fr) 34px; }
  .history-meta small { font-size: .62rem; }
  .pagination { gap: 8px; }
  .pagination button { padding: 0 10px; }
}

@media (max-width: 390px) {
  .history-grid { grid-template-columns: 1fr; }
  .action-buttons { grid-template-columns: 1fr 1fr; }
  .action-buttons .clear-button { grid-column: 1 / -1; }
}
</style>
