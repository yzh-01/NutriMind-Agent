<template>
  <div class="page-shell coach-page">
    <header class="page-head">
      <div>
        <span class="status-chip"><Sparkle :size="16" weight="fill" /> AI 营养教练</span>
        <h1 class="page-title">问清楚，再吃。</h1>
        <p class="page-description">围绕减脂、增肌、训练补给和食物选择，获得更容易执行的建议。</p>
      </div>
      <div class="page-actions">
        <button class="history-toggle" type="button" aria-label="打开历史对话" @click="historyOpen = true">
          <ClockCounterClockwise :size="18" weight="bold" />
          历史对话
        </button>
        <button
          class="stream-toggle"
          type="button"
          :disabled="generating"
          :aria-pressed="streamingEnabled"
          :aria-label="streamingEnabled ? '切换为经典模式' : '切换为流式输出'"
          :title="streamingEnabled ? '当前：流式输出（逐字显示）' : '当前：经典模式（等待完整回复）'"
          @click="toggleStreaming"
        >
          <Lightning v-if="streamingEnabled" :size="18" weight="fill" />
          <ChatCircleDots v-else :size="18" weight="bold" />
          {{ streamingEnabled ? '流式' : '经典' }}
        </button>
        <button
          class="context-toggle"
          type="button"
          :aria-pressed="contextHidden"
          :aria-label="contextHidden ? '显示当前计划' : '隐藏当前计划'"
          @click="toggleContext"
        >
          <SidebarSimple :size="18" weight="bold" />
          {{ contextHidden ? '显示计划' : '隐藏计划' }}
        </button>
        <FuelButton variant="secondary" :arrow="false" @click="resetChat"><ArrowsClockwise :size="18" /> 新对话</FuelButton>
      </div>
    </header>

    <section class="chat-workspace surface" :class="{ 'context-hidden': contextHidden, 'history-open': historyOpen }">
      <button v-if="historyOpen" class="history-scrim" type="button" aria-label="关闭历史对话" @click="historyOpen = false" />

      <aside class="session-panel" aria-label="历史对话">
        <header>
          <div><span>对话记录</span><small>最近 {{ sessions.length }} 条</small></div>
          <button type="button" :disabled="sessionsLoading" aria-label="刷新历史对话" title="刷新历史对话" @click="loadSessions()">
            <ArrowsClockwise :size="17" :class="{ spin: sessionsLoading }" />
          </button>
          <button class="session-close" type="button" aria-label="关闭历史对话" @click="historyOpen = false"><X :size="17" /></button>
        </header>

        <div v-if="sessionsLoading && !sessions.length" class="session-loading" aria-label="正在加载历史对话">
          <i v-for="number in 4" :key="number" />
        </div>
        <div v-else-if="sessionsError" class="session-state" role="alert">
          <WarningCircle :size="24" />
          <p>{{ sessionsError }}</p>
          <button type="button" @click="loadSessions()">重新加载</button>
        </div>
        <div v-else-if="!sessions.length" class="session-state">
          <ChatCircleDots :size="28" weight="thin" />
          <p>还没有历史对话<br><small>发送第一个问题后会自动保存。</small></p>
        </div>
        <div v-else class="session-list">
          <article v-for="session in sessions" :key="session.sessionId" :class="{ active: session.sessionId === activeSessionId }">
            <button
              class="session-select"
              type="button"
              :disabled="loadingSessionId === session.sessionId"
              :aria-current="session.sessionId === activeSessionId ? 'true' : undefined"
              @click="openSession(session.sessionId)"
            >
              <CircleNotch v-if="loadingSessionId === session.sessionId" class="spin" :size="16" />
              <ChatCircleDots v-else :size="17" />
              <span><b>{{ session.title }}</b><small>{{ formatSessionTime(session.updatedAt) }}</small></span>
            </button>
            <button
              class="session-delete"
              type="button"
              :disabled="deletingSessionId === session.sessionId"
              :aria-label="`删除对话：${session.title}`"
              title="删除对话"
              @click="removeSession(session)"
            >
              <CircleNotch v-if="deletingSessionId === session.sessionId" class="spin" :size="15" />
              <Trash v-else :size="15" />
            </button>
          </article>
        </div>
        <footer><span />最多显示后端返回的 50 条会话</footer>
      </aside>

      <div class="conversation">
        <div ref="messageArea" class="messages" aria-live="polite">
          <section v-if="messages.length === 1" class="welcome">
            <div class="coach-mark"><Lightning :size="34" weight="fill" /></div>
            <h2>今天想解决什么问题？</h2>
            <p>描述你的目标、训练时间和饮食情况，信息越具体，建议越容易执行。</p>
            <div class="quick-grid">
              <button v-for="item in prompts" :key="item.title" @click="selectPrompt(item.question)">
                <component :is="item.icon" :size="23" weight="duotone" />
                <span><b>{{ item.title }}</b><small>{{ item.detail }}</small></span>
                <ArrowRight :size="17" weight="bold" />
              </button>
            </div>
          </section>

          <article v-for="(message, index) in messages" :key="message.id || index" :class="['message', message.role]">
            <span v-if="message.role === 'assistant'" class="message-avatar"><Lightning :size="17" weight="fill" /></span>
            <div class="message-body">
              <small>{{ message.role === 'assistant' ? 'Nutri 教练' : '你' }}</small>
              <img v-if="message.imageUrl" class="message-image" :src="message.imageUrl" :alt="message.imageName ? `随问题上传的图片：${message.imageName}` : '随问题上传的食物图片'" />
              <div v-if="message.pending" class="typing"><i /><i /><i /><span>正在整理建议</span></div>
              <div v-else class="markdown" v-html="renderMarkdown(message.content)" />
              <div v-if="message.detections?.length || message.toolCalls?.length" class="response-meta" aria-label="智能体处理摘要">
                <span v-if="message.detections?.length"><Scan :size="15" />识别 {{ message.detections.length }} 个目标</span>
                <span v-if="message.toolCalls?.length"><Wrench :size="15" />调用 {{ message.toolCalls.length }} 个工具</span>
              </div>
              <details v-if="message.toolCalls?.length" class="tool-details">
                <summary>查看本次使用的工具</summary>
                <ul><li v-for="tool in message.toolCalls" :key="tool.id"><code>{{ toolDisplayName(tool.name) }}</code></li></ul>
              </details>
              <section v-if="message.nutrition" class="answer-card">
                <div v-for="item in message.nutrition" :key="item.label"><span>{{ item.label }}</span><strong class="metric-number">{{ item.value }}</strong></div>
              </section>
            </div>
          </article>
        </div>

        <div class="composer-wrap">
          <div class="composer">
            <input ref="fileInput" class="sr-only" type="file" accept="image/jpeg,image/png,image/webp" tabindex="-1" aria-hidden="true" @change="selectImage" />
            <div v-if="selectedImage" class="attachment-preview">
              <img :src="selectedImageUrl" alt="准备发送的食物图片" />
              <div><b>{{ selectedImage.name }}</b><small>{{ formatFileSize(selectedImage.size) }} · 将随问题发送</small></div>
              <button type="button" :disabled="generating" aria-label="移除待发送图片" @click="removeSelectedImage"><X :size="17" weight="bold" /></button>
            </div>
            <textarea
              ref="composerInput"
              v-model="question"
              rows="1"
              maxlength="500"
              aria-label="输入营养问题"
              placeholder="例如：晚上力量训练，减脂期晚饭怎么吃？"
              @input="resizeComposer"
              @keydown.enter.exact.prevent="sendMessage"
            />
            <div class="composer-footer">
              <button class="attach" type="button" :disabled="generating" aria-label="选择食物图片" title="选择食物图片" @click="fileInput?.click()"><Camera :size="20" /></button>
              <span>{{ selectedImage ? '图片会与当前问题一起发送' : 'Enter 发送，Shift + Enter 换行' }}</span>
              <button v-if="generating" class="stop-button" type="button" @click="stopGeneration">
                <Stop :size="18" weight="fill" />
                停止生成
              </button>
              <FuelButton v-else class="send-button" :arrow="false" :disabled="!question.trim()" @click="sendMessage">
                <PaperPlaneTilt :size="19" weight="fill" />
                发送
              </FuelButton>
            </div>
          </div>
          <p v-if="composerError" class="composer-error" role="alert"><WarningCircle :size="16" />{{ composerError }}</p>
          <small class="disclaimer">建议仅用于日常健康管理，不能替代专业医疗诊断。</small>
        </div>
      </div>

      <aside class="context-panel" :aria-hidden="contextHidden">
        <div class="context-title"><span>当前计划</span><Target :size="22" weight="duotone" /></div>
        <div v-if="contextLoading" class="context-loading" aria-label="正在加载当前计划">
          <i /><i /><i /><i />
        </div>
        <div v-else-if="contextError" class="context-error" role="alert">
          <WarningCircle :size="24" />
          <b>计划读取失败</b>
          <p>{{ contextError }}</p>
          <button type="button" :disabled="contextLoading" @click="loadCoachContext">重新读取</button>
        </div>
        <template v-else>
          <div class="goal-summary">
            <small>主要目标</small><strong>{{ goalModeLabel }}</strong><span>{{ dailyCaloriesLabel }}</span>
          </div>
          <div class="context-metrics">
            <div><span>每日蛋白质目标</span><strong class="metric-number">{{ proteinTargetLabel }}</strong></div>
            <div><span>每周训练频率</span><strong class="metric-number">{{ trainingDaysLabel }}</strong></div>
            <div><span>目标体重</span><strong class="metric-number">{{ targetWeightLabel }}</strong></div>
          </div>
          <div class="profile-context-note">
            <p>身体与目标资料会自动作为 Agent 的个性化上下文；不代表今日实际摄入或训练记录。</p>
            <a href="/app/profile">{{ contextIncomplete ? '完善个人资料' : '编辑个人目标' }}<ArrowRight :size="15" weight="bold" /></a>
          </div>
          <div class="source-box">
            <BookOpenText :size="21" weight="duotone" />
            <div><b>支持知识库检索</b><p>回答时可检索已上传的营养资料，实际引用以回复内容为准。</p></div>
          </div>
        </template>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  PhArrowRight as ArrowRight, PhArrowsClockwise as ArrowsClockwise,
  PhBookOpenText as BookOpenText, PhBowlFood as BowlFood, PhCamera as Camera,
  PhChatCircleDots as ChatCircleDots, PhCircleNotch as CircleNotch,
  PhClockCounterClockwise as ClockCounterClockwise, PhForkKnife as ForkKnife, PhLightning as Lightning,
  PhPaperPlaneTilt as PaperPlaneTilt, PhPersonSimpleRun as PersonSimpleRun,
  PhScan as Scan, PhSidebarSimple as SidebarSimple, PhSparkle as Sparkle, PhStop as Stop, PhTarget as Target,
  PhTrash as Trash, PhWarningCircle as WarningCircle, PhWrench as Wrench, PhX as X,
} from '@phosphor-icons/vue'
import FuelButton from '@/components/ui/FuelButton.vue'
import {
  deleteChatSessionApi, getChatSessionApi, getChatSessionsApi,
  sendChatImageApi, sendChatMessageApi, streamChatImageApi, streamChatMessageApi,
} from '@/api/chat'
import { getProfileApi } from '@/api/profile'
import { useUserStore } from '@/stores/user'
import { normalizeChatResponse, normalizeChatSession, normalizeChatSessions } from '@/utils/chatData'
import { renderMarkdown } from '@/utils/markdown'
import { emptyProfileForm, normalizeUserProfile } from '@/utils/profileData'

const userStore = useUserStore()
const question = ref('')
const generating = ref(false)
const messageArea = ref(null)
const composerInput = ref(null)
const fileInput = ref(null)
const selectedImage = ref(null)
const selectedImageUrl = ref('')
const composerError = ref('')
const contextHidden = ref(readContextPreference())
const streamingEnabled = ref(readStreamingPreference())
const sessionId = ref(createSessionId())
const activeSessionId = ref('')
const sessionPersisted = ref(false)
const sessions = ref([])
const sessionsLoading = ref(false)
const sessionsError = ref('')
const loadingSessionId = ref('')
const deletingSessionId = ref('')
const historyOpen = ref(false)
const coachProfile = ref(emptyProfileForm())
const contextLoading = ref(true)
const contextError = ref('')
const messageImageUrls = new Set()
let requestGeneration = 0
let activeRequestController = null
let demoTimerId = null
const CONTEXT_KEY = 'nutrimind_coach_context_hidden'
const STREAMING_KEY = 'nutrimind_coach_streaming'
const firstMessage = { role: 'assistant', content: '你好，我是 Nutri 教练。告诉我你的目标、训练安排或刚刚吃了什么。' }
const messages = ref([{ ...firstMessage }])
const demoSessions = [
  {
    session_id: 'demo-history-1', title: '训练后的晚餐怎么安排',
    created_at: '2026-07-20T18:20:00', updated_at: '2026-07-20T18:26:00',
    messages: [
      { id: 101, role: 'user', content: '晚上力量训练结束后，减脂期晚餐怎么安排？', tool_calls: [], created_at: '2026-07-20T18:20:00' },
      { id: 102, role: 'assistant', content: '**训练后晚餐**\n\n优先安排优质蛋白质、适量主食和蔬菜，例如鸡胸肉、米饭与绿叶菜。', tool_calls: [{ name: 'search_nutrition_knowledge', args: {} }], created_at: '2026-07-20T18:26:00' },
    ],
  },
  {
    session_id: 'demo-history-2', title: '早餐蛋白质补充',
    created_at: '2026-07-18T08:10:00', updated_at: '2026-07-18T08:14:00', messages: [],
  },
]
const goalModeLabels = { cut: '减脂', muscle: '增肌', maintain: '保持' }
const toolDisplayNames = {
  detect_food: '食物图片识别',
  query_food_calories: '食物营养查询',
  calculate_total_nutrition: '整餐营养计算',
  search_nutrition_knowledge: '营养知识库检索',
  search_web_evidence: 'Exa 联网搜索',
  exa_web_search: 'Exa 联网搜索（知识库 fallback）',
  vision_verify_food: '视觉模型复核',
}
const toolDisplayName = (name) => toolDisplayNames[name] || name
const goalModeLabel = computed(() => goalModeLabels[coachProfile.value.mode] || '尚未设置')
const dailyCaloriesLabel = computed(() => {
  const value = positiveNumber(coachProfile.value.dailyCalories)
  return value ? `每日热量目标 ${formatNumber(value)} kcal` : '尚未设置每日热量目标'
})
const proteinTargetLabel = computed(() => formatPlanMetric(coachProfile.value.proteinTarget, 'g / 天'))
const trainingDaysLabel = computed(() => formatPlanMetric(coachProfile.value.trainingDays, '天 / 周'))
const targetWeightLabel = computed(() => formatPlanMetric(coachProfile.value.targetWeight, 'kg'))
const contextIncomplete = computed(() => [
  coachProfile.value.mode,
  coachProfile.value.dailyCalories,
  coachProfile.value.proteinTarget,
  coachProfile.value.trainingDays,
  coachProfile.value.targetWeight,
].some((value) => value === '' || value === null || value === undefined))
const dinnerPrompt = computed(() => {
  const details = []
  if (goalModeLabels[coachProfile.value.mode]) details.push(`我的目标是${goalModeLabel.value}`)
  const calories = positiveNumber(coachProfile.value.dailyCalories)
  if (calories) details.push(`每日热量目标为 ${formatNumber(calories)} 千卡`)
  const context = details.length ? `${details.join('，')}。` : ''
  return `${context}请帮我安排今晚的晚饭，兼顾营养和饱腹感。`
})
const prompts = computed(() => [
  { title: '安排今晚饮食', detail: '结合目标，也保证饱腹感', question: dinnerPrompt.value, icon: markRaw(ForkKnife) },
  { title: '优化训练补给', detail: '训练前后应该怎样吃', question: '我晚上六点半力量训练，训练前后分别吃什么？', icon: markRaw(PersonSimpleRun) },
  { title: '分析一顿饭', detail: '判断热量和营养组成', question: '如何判断一顿饭的蛋白质和热量是否适合我的目标？', icon: markRaw(BowlFood) },
])

function positiveNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : null
}

function formatNumber(value) {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 }).format(value)
}

function formatPlanMetric(value, unit) {
  const number = positiveNumber(value)
  return number ? `${formatNumber(number)} ${unit}` : '未设置'
}

function createSessionId() {
  if (typeof crypto?.randomUUID === 'function') return `meal-${crypto.randomUUID()}`
  return `meal-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function readContextPreference() {
  try { return localStorage.getItem('nutrimind_coach_context_hidden') === 'true' }
  catch { return false }
}

function toggleContext() {
  contextHidden.value = !contextHidden.value
  try { localStorage.setItem(CONTEXT_KEY, String(contextHidden.value)) }
  catch { /* Keep the preference for this page session. */ }
}

function readStreamingPreference() {
  // 默认开启流式；仅当用户显式切到经典模式时才关闭。
  try { return localStorage.getItem(STREAMING_KEY) !== 'false' }
  catch { return true }
}

function toggleStreaming() {
  if (generating.value) return
  streamingEnabled.value = !streamingEnabled.value
  try { localStorage.setItem(STREAMING_KEY, String(streamingEnabled.value)) }
  catch { /* Keep the preference for this page session. */ }
  ElMessage.info(streamingEnabled.value ? '已切换为流式输出（逐字显示）' : '已切换为经典模式（等待完整回复）')
}

async function loadCoachContext() {
  contextLoading.value = true
  contextError.value = ''
  if (userStore.isDemo) {
    coachProfile.value = emptyProfileForm()
    contextLoading.value = false
    return
  }

  try {
    coachProfile.value = normalizeUserProfile(await getProfileApi({ silent: true })).form
  } catch {
    coachProfile.value = emptyProfileForm()
    contextError.value = '暂时无法获取个人资料，请稍后重试。'
  } finally {
    contextLoading.value = false
  }
}

function formatSessionTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未知'
  const today = new Date()
  if (date.toDateString() === today.toDateString()) {
    return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' }).format(date)
  }
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' }).format(date)
}

async function loadSessions(background = false) {
  if (!background) sessionsLoading.value = true
  sessionsError.value = ''
  try {
    const payload = userStore.isDemo ? demoSessions : await getChatSessionsApi()
    sessions.value = normalizeChatSessions(payload)
  } catch {
    if (!background) sessionsError.value = '历史对话暂时无法读取，请稍后重试。'
  } finally {
    if (!background) sessionsLoading.value = false
  }
}

async function openSession(targetSessionId) {
  if (!targetSessionId || loadingSessionId.value) return
  cancelActiveRequest(false)
  loadingSessionId.value = targetSessionId
  composerError.value = ''
  try {
    const payload = userStore.isDemo
      ? demoSessions.find((item) => item.session_id === targetSessionId)
      : await getChatSessionApi(targetSessionId)
    const result = normalizeChatSession(payload)
    if (!result.sessionId) throw new Error('missing session')
    releaseMessageImages()
    sessionId.value = result.sessionId
    activeSessionId.value = result.sessionId
    sessionPersisted.value = true
    messages.value = [{ ...firstMessage }, ...result.messages]
    question.value = ''
    removeSelectedImage()
    historyOpen.value = false
    nextTick(resizeComposer)
    scrollToEnd()
  } catch {
    ElMessage.error('历史对话加载失败，请重新选择')
  } finally {
    loadingSessionId.value = ''
  }
}

async function removeSession(session) {
  try {
    await ElMessageBox.confirm(`删除“${session.title}”后将无法恢复，是否继续？`, '删除历史对话', {
      type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消',
    })
    deletingSessionId.value = session.sessionId
    if (!userStore.isDemo) await deleteChatSessionApi(session.sessionId)
    sessions.value = sessions.value.filter((item) => item.sessionId !== session.sessionId)
    if (activeSessionId.value === session.sessionId) resetChat()
    ElMessage.success(userStore.isDemo ? '预览模式：已模拟删除对话' : '历史对话已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('历史对话删除失败')
  } finally {
    deletingSessionId.value = ''
  }
}

function resizeComposer() {
  const input = composerInput.value
  if (!input) return
  input.style.height = 'auto'
  input.style.height = `${Math.min(input.scrollHeight, 130)}px`
}

function selectImage(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  composerError.value = ''
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    composerError.value = '图片格式不支持，请选择 JPG、PNG 或 WEBP 文件。'
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    composerError.value = '图片超过 10 MB，请压缩后重新选择。'
    return
  }
  removeSelectedImage()
  selectedImage.value = file
  selectedImageUrl.value = URL.createObjectURL(file)
}

function removeSelectedImage() {
  if (selectedImageUrl.value) URL.revokeObjectURL(selectedImageUrl.value)
  selectedImage.value = null
  selectedImageUrl.value = ''
}

function releaseMessageImages() {
  messageImageUrls.forEach((url) => URL.revokeObjectURL(url))
  messageImageUrls.clear()
}

function formatFileSize(bytes) {
  const value = Number(bytes)
  if (!Number.isFinite(value) || value <= 0) return '大小未知'
  return value < 1024 ** 2 ? `${(value / 1024).toFixed(1)} KB` : `${(value / 1024 ** 2).toFixed(1)} MB`
}

async function selectPrompt(value) {
  question.value = value
  await nextTick()
  resizeComposer()
  composerInput.value?.focus()
}

async function scrollToEnd() {
  await nextTick()
  if (messageArea.value) messageArea.value.scrollTop = messageArea.value.scrollHeight
}

function demoResponse(hasImage) {
  if (hasImage) {
    return {
      session_id: sessionId.value,
      image_id: `preview-${Date.now()}`,
      detection_mode: 'mock',
      detections: [
        { class_name: 'rice', class_name_cn: '米饭', confidence: .93, bbox: [32, 58, 265, 318] },
        { class_name: 'chicken', class_name_cn: '鸡肉', confidence: .88, bbox: [278, 74, 512, 326] },
      ],
      response: '**图片分析完成**\n\n画面中主要包含米饭和鸡肉。按常见份量估算，这一餐可以优先确认鸡肉是否少油烹饪，并补充一份蔬菜，让蛋白质、碳水和膳食纤维更均衡。',
      tool_calls: [
        { name: 'detect_food', args: { image_id: 'preview' } },
        { name: 'query_food_calories', args: { food_name: 'rice' } },
        { name: 'calculate_total_nutrition', args: {} },
      ],
      analysis_result: null,
    }
  }
  return {
    session_id: sessionId.value,
    response: '**建议思路**\n\n把晚餐放在训练后，优先保证蛋白质和适量碳水。可以选择 150g 鸡胸肉、120g 熟米饭和 200g 绿叶蔬菜。少油烹饪后，这一餐更容易控制在你的剩余预算内。',
    tool_calls: [{ name: 'calculate_total_nutrition', args: {} }],
    analysis_result: null,
  }
}

function waitForDemo(signal) {
  return new Promise((resolve, reject) => {
    demoTimerId = window.setTimeout(() => {
      demoTimerId = null
      resolve()
    }, 700)
    signal.addEventListener('abort', () => {
      if (demoTimerId) window.clearTimeout(demoTimerId)
      demoTimerId = null
      const error = new Error('The request was aborted')
      error.name = 'AbortError'
      reject(error)
    }, { once: true })
  })
}

function cancelActiveRequest(markStopped = false) {
  const wasGenerating = generating.value
  activeRequestController?.abort()
  activeRequestController = null
  if (demoTimerId) window.clearTimeout(demoTimerId)
  demoTimerId = null
  requestGeneration += 1
  generating.value = false

  if (!markStopped || !wasGenerating) return
  for (let index = messages.value.length - 1; index >= 0; index -= 1) {
    if (!messages.value[index].pending) continue
    messages.value[index] = {
      role: 'assistant',
      content: '**已停止生成**\n\n本次回复已由你中断，可以修改问题后重新发送。',
      stopped: true,
    }
    break
  }
  composerError.value = ''
  scrollToEnd()
}

function stopGeneration() {
  cancelActiveRequest(true)
}

function requestErrorMessage(error, hasImage) {
  const status = error?.response?.status
  if (status === 413) return '图片超过服务端限制，请压缩后重新选择。'
  if (status === 422) return '问题或图片没有通过校验，请检查内容后重新发送。'
  if (error?.code === 'ECONNABORTED' || /idle timeout/.test(error?.message || '')) {
    return '智能体处理时间较长，连接已中断，请稍后重试。'
  }
  return hasImage ? '图片分析没有成功，请重新选择图片后再试。' : '消息没有发送成功，请稍后重新发送。'
}

async function sendMessage() {
  const content = question.value.trim()
  if (!content || generating.value) return
  const imageFile = selectedImage.value
  const imageUrl = selectedImageUrl.value
  const imageName = imageFile?.name || ''
  if (imageUrl) messageImageUrls.add(imageUrl)

  messages.value.push({ role: 'user', content, imageUrl, imageName })
  messages.value.push({ role: 'assistant', pending: true, content: '' })
  const responseIndex = messages.value.length - 1
  question.value = ''
  selectedImage.value = null
  selectedImageUrl.value = ''
  composerError.value = ''
  nextTick(resizeComposer)
  generating.value = true
  scrollToEnd()

  const generation = ++requestGeneration
  const controller = new AbortController()
  activeRequestController = controller
  let streamErrored = false
  try {
    if (userStore.isDemo) {
      await waitForDemo(controller.signal)
      const payload = demoResponse(Boolean(imageFile))
      if (generation !== requestGeneration) return
      const result = normalizeChatResponse(payload, sessionId.value)
      sessionId.value = result.sessionId || sessionId.value
      if (!imageFile) { activeSessionId.value = sessionId.value; sessionPersisted.value = true }
      messages.value[responseIndex] = {
        role: 'assistant', content: result.response, detections: result.detections,
        toolCalls: result.toolCalls, analysisResult: result.analysisResult,
        nutrition: !imageFile ? [
          { label: '预计热量', value: '520 kcal' },
          { label: '蛋白质', value: '48g' },
          { label: '碳水', value: '55g' },
        ] : null,
      }
      scrollToEnd()
      return
    }

    const onEvent = (event) => {
      if (generation !== requestGeneration) return
      const msg = messages.value[responseIndex]
      switch (event.type) {
        case 'session':
          if (event.session_id) {
            sessionId.value = event.session_id
            activeSessionId.value = event.session_id
            sessionPersisted.value = true
          }
          break
        case 'reset':
          msg.pending = false
          msg.content = ''
          break
        case 'token':
          msg.pending = false
          msg.content += event.text || ''
          scrollToEnd()
          break
        case 'done': {
          const result = normalizeChatResponse(event, sessionId.value)
          messages.value[responseIndex] = {
            role: 'assistant',
            content: result.response,
            detections: result.detections,
            toolCalls: result.toolCalls,
            analysisResult: result.analysisResult,
          }
          scrollToEnd()
          break
        }
        case 'error':
          streamErrored = true
          messages.value[responseIndex] = {
            role: 'assistant',
            content: `**暂时没有得到回复**\n\n${event.message || '智能体处理失败，请稍后重试。'}`,
            failed: true,
          }
          composerError.value = event.message || '智能体处理失败，请稍后重试。'
          scrollToEnd()
          break
        default:
          break
      }
    }

    if (streamingEnabled.value) {
      if (imageFile) {
        await streamChatImageApi(imageFile, { sessionId: sessionId.value, message: content }, { signal: controller.signal, onEvent })
      } else {
        await streamChatMessageApi({ sessionId: sessionId.value, message: content }, { signal: controller.signal, onEvent })
      }
    } else {
      // 经典模式：等待完整回复（超时更长 + 连接失败自动重试）
      const payload = imageFile
        ? await sendChatImageApi(imageFile, { sessionId: sessionId.value, message: content }, { signal: controller.signal })
        : await sendChatMessageApi({ sessionId: sessionId.value, message: content }, { signal: controller.signal })
      if (generation !== requestGeneration) return
      const result = normalizeChatResponse(payload, sessionId.value)
      sessionId.value = result.sessionId || sessionId.value
      activeSessionId.value = sessionId.value
      sessionPersisted.value = true
      messages.value[responseIndex] = {
        role: 'assistant',
        content: result.response,
        detections: result.detections,
        toolCalls: result.toolCalls,
        analysisResult: result.analysisResult,
      }
      scrollToEnd()
    }
    if (generation !== requestGeneration) return
    await loadSessions(true)
  } catch (error) {
    if (generation !== requestGeneration) return
    const errorMessage = requestErrorMessage(error, Boolean(imageFile))
    messages.value[responseIndex] = {
      role: 'assistant',
      content: `**暂时没有得到回复**\n\n${errorMessage}`,
      failed: true,
    }
    composerError.value = errorMessage
    scrollToEnd()
  } finally {
    if (generation === requestGeneration) {
      generating.value = false
      activeRequestController = null
    }
  }
}

function resetChat() {
  cancelActiveRequest(false)
  question.value = ''
  composerError.value = ''
  removeSelectedImage()
  releaseMessageImages()
  sessionId.value = createSessionId()
  activeSessionId.value = ''
  sessionPersisted.value = false
  historyOpen.value = false
  nextTick(resizeComposer)
  messages.value = [{ ...firstMessage }]
}

onMounted(() => {
  loadSessions()
  loadCoachContext()
})

onBeforeUnmount(() => {
  cancelActiveRequest(false)
  removeSelectedImage()
  releaseMessageImages()
})
</script>

<style lang="scss" scoped>
.coach-page { padding-bottom: 30px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.page-head { margin-bottom: 24px; display: flex; align-items: end; justify-content: space-between; gap: 24px; }
.page-head .status-chip { margin-bottom: 16px; }
.page-actions { display: flex; align-items: center; gap: 9px; }
.context-toggle, .history-toggle, .stream-toggle { min-height: 48px; padding: 0 14px; align-items: center; justify-content: center; gap: 8px; color: var(--text-secondary); background: transparent; border: 1px solid var(--border-strong); border-radius: 10px; font-size: .8rem; font-weight: 600; }
.context-toggle, .stream-toggle { display: inline-flex; }
.history-toggle { display: none; }
.context-toggle:hover, .history-toggle:hover, .stream-toggle:hover:not(:disabled) { color: var(--primary); background: var(--surface); border-color: rgba(159,226,75,.32); }
.stream-toggle[aria-pressed="true"] { color: var(--primary); border-color: rgba(159,226,75,.4); background: rgba(159,226,75,.08); }
.stream-toggle:disabled { opacity: .5; cursor: not-allowed; }
.chat-workspace { position: relative; height: max(680px, calc(100dvh - 220px)); display: grid; grid-template-columns: 240px minmax(0, 1fr) 290px; overflow: hidden; }
.chat-workspace.context-hidden { grid-template-columns: 240px minmax(0, 1fr); }
.context-hidden .context-panel { display: none; }
.history-scrim { display: none; }
.session-panel { min-width: 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden; background: rgba(13,16,15,.62); border-right: 1px solid var(--border); }
.session-panel > header { min-height: 68px; padding: 12px 11px 12px 16px; display: flex; align-items: center; gap: 6px; border-bottom: 1px solid var(--border); }
.session-panel > header > div { min-width: 0; margin-right: auto; display: grid; gap: 2px; }
.session-panel > header span { color: var(--text); font-size: .82rem; font-weight: 650; }
.session-panel > header small { color: var(--muted); font-size: .64rem; }
.session-panel > header button, .session-close { width: 40px; height: 40px; flex: 0 0 auto; display: grid; place-items: center; color: var(--muted); background: transparent; border: 1px solid transparent; border-radius: 9px; }
.session-panel > header button:hover:not(:disabled) { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.16); }
.session-panel > header button:disabled { cursor: wait; opacity: .5; }
.session-close { display: none !important; }
.session-list { min-height: 0; flex: 1; padding: 8px; display: grid; align-content: start; gap: 5px; overflow-y: auto; overscroll-behavior: contain; }
.session-list article { min-width: 0; display: grid; grid-template-columns: minmax(0,1fr) 40px; align-items: center; border: 1px solid transparent; border-radius: 10px; transition: background 160ms var(--ease-out), border-color 160ms var(--ease-out); }
.session-list article:hover { background: rgba(255,255,255,.025); border-color: var(--border); }
.session-list article.active { background: var(--primary-soft); border-color: rgba(159,226,75,.2); }
.session-select { min-width: 0; min-height: 64px; padding: 9px 4px 9px 10px; display: grid; grid-template-columns: 18px minmax(0,1fr); align-items: center; gap: 8px; color: var(--muted); background: transparent; border: 0; text-align: left; }
.session-select > span { min-width: 0; display: grid; gap: 5px; }
.session-select b { overflow: hidden; color: var(--text-secondary); font-size: .73rem; font-weight: 600; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }
.session-select small { color: var(--muted); font-size: .61rem; }
.session-list article.active .session-select, .session-list article.active .session-select b { color: var(--primary); }
.session-select:disabled, .session-delete:disabled { cursor: wait; opacity: .6; }
.session-delete { width: 40px; height: 40px; display: grid; place-items: center; color: var(--muted); background: transparent; border: 0; border-radius: 8px; }
.session-delete:hover:not(:disabled) { color: #ffc8c8; background: rgba(240,103,95,.1); }
.session-loading { min-height: 0; flex: 1; padding: 13px 9px; display: grid; align-content: start; gap: 8px; }
.session-loading i { height: 58px; background: linear-gradient(90deg, rgba(255,255,255,.025), rgba(255,255,255,.065), rgba(255,255,255,.025)); background-size: 200% 100%; border-radius: 10px; animation: session-shimmer 1.2s linear infinite; }
.session-state { min-height: 0; flex: 1; padding: 28px 18px; display: grid; place-items: center; align-content: center; gap: 12px; color: var(--muted); text-align: center; }
.session-state p { margin: 0; font-size: .73rem; line-height: 1.6; }
.session-state small { font-size: .65rem; }
.session-state button { min-height: 40px; padding: 0 12px; color: var(--primary); background: var(--primary-soft); border: 1px solid rgba(159,226,75,.2); border-radius: 8px; font-size: .7rem; }
.session-panel > footer { min-height: 40px; padding: 0 14px; display: flex; align-items: center; gap: 8px; color: var(--muted); border-top: 1px solid var(--border); font-size: .58rem; }
.session-panel > footer span { width: 5px; height: 5px; background: var(--primary); border-radius: 50%; }
@keyframes session-shimmer { to { background-position: -200% 0; } }
.conversation { min-width: 0; min-height: 0; display: flex; flex-direction: column; }
.messages { min-height: 0; flex: 1; padding: 30px clamp(20px, 5vw, 74px); overflow-y: auto; overscroll-behavior: contain; scrollbar-gutter: stable; scroll-behavior: smooth; }
.welcome { max-width: 820px; margin: 5vh auto 42px; text-align: center; }
.coach-mark { width: 72px; height: 72px; margin: 0 auto 20px; display: grid; place-items: center; color: #10150e; background: var(--primary); border-radius: 18px; transform: rotate(-4deg); box-shadow: 10px 10px 0 rgba(159,226,75,.13); }
.welcome h2 { margin: 0 0 10px; font-family: "Barlow Condensed", MiSans, sans-serif; font-size: clamp(2rem, 4vw, 3.2rem); line-height: 1; }
.welcome > p { max-width: 52ch; margin: 0 auto 28px; color: var(--text-secondary); line-height: 1.65; }
.quick-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: left; }
.quick-grid button { min-height: 112px; padding: 16px; display: grid; grid-template-columns: auto 1fr auto; align-items: start; gap: 10px; color: var(--text); background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 12px; transition: transform 180ms var(--ease-out), border-color 180ms var(--ease-out); }
.quick-grid button:hover { border-color: rgba(159,226,75,.35); transform: translateY(-2px); }
.quick-grid button > svg { color: var(--primary); }
.quick-grid button span { display: grid; gap: 4px; }
.quick-grid b { font-size: .85rem; }
.quick-grid small { color: var(--muted); font-size: .72rem; line-height: 1.45; }
.message { max-width: 820px; margin: 0 auto 26px; display: flex; gap: 12px; }
.message.user { justify-content: flex-end; }
.message-avatar { flex: 0 0 auto; width: 36px; height: 36px; display: grid; place-items: center; color: #11160f; background: var(--primary); border-radius: 10px; }
.message-body { max-width: min(680px, 85%); }
.message-body > small { margin-bottom: 6px; display: block; color: var(--muted); font-size: .72rem; }
.user .message-body > small { text-align: right; }
.message-image { width: min(360px, 100%); max-height: 260px; margin: 0 0 8px auto; display: block; object-fit: cover; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 13px 5px 13px 13px; }
.markdown { padding: 14px 17px; color: var(--text-secondary); background: var(--surface-raised); border: 1px solid var(--border); border-radius: 5px 15px 15px 15px; line-height: 1.7; }
.user .markdown { color: #151b12; background: var(--primary); border-color: var(--primary); border-radius: 15px 5px 15px 15px; }
.markdown :deep(p) { margin: 0 0 10px; }
.markdown :deep(p:last-child) { margin-bottom: 0; }
.response-meta { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.response-meta span { min-height: 30px; padding: 0 9px; display: inline-flex; align-items: center; gap: 6px; color: var(--primary); background: var(--primary-soft); border: 1px solid rgba(159, 226, 75, .14); border-radius: 8px; font-size: .65rem; }
.tool-details { margin-top: 7px; padding: 9px 11px; color: var(--muted); background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 9px; font-size: .66rem; }
.tool-details summary { min-height: 28px; display: flex; align-items: center; cursor: pointer; color: var(--text-secondary); }
.tool-details ul { margin: 7px 0 0; padding: 8px 0 0 18px; display: grid; gap: 5px; border-top: 1px solid var(--border); }
.tool-details code { color: var(--primary); }
.answer-card { margin-top: 8px; display: grid; grid-template-columns: repeat(3, 1fr); background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 10px; }
.answer-card div { padding: 12px; display: grid; gap: 4px; border-right: 1px solid var(--border); }
.answer-card div:last-child { border-right: 0; }
.answer-card span { color: var(--muted); font-size: .7rem; }
.answer-card strong { color: var(--primary); font-size: 1.25rem; font-weight: 500; }
.typing { min-width: 220px; padding: 16px; display: flex; align-items: center; gap: 5px; color: var(--muted); background: var(--surface-raised); border-radius: 5px 15px 15px 15px; font-size: .72rem; }
.typing i { width: 6px; height: 6px; background: var(--primary); border-radius: 50%; animation: pulse 900ms ease-in-out infinite alternate; }
.typing i:nth-child(2) { animation-delay: 120ms; }.typing i:nth-child(3) { animation-delay: 240ms; }.typing span { margin-left: 5px; }
@keyframes pulse { to { opacity: .28; transform: translateY(-3px); } }
.composer-wrap { flex: 0 0 auto; padding: 12px 22px 16px; border-top: 1px solid var(--border); }
.composer { padding: 11px; background: var(--canvas-soft); border: 1px solid var(--border-strong); border-radius: 14px; }
.attachment-preview { margin-bottom: 8px; padding: 8px; display: grid; grid-template-columns: 54px minmax(0, 1fr) 40px; align-items: center; gap: 10px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; }
.attachment-preview img { width: 54px; height: 48px; object-fit: cover; background: var(--canvas); border-radius: 7px; }
.attachment-preview > div { min-width: 0; display: grid; gap: 3px; }
.attachment-preview b { overflow: hidden; font-size: .72rem; text-overflow: ellipsis; white-space: nowrap; }
.attachment-preview small { color: var(--muted); font-size: .62rem; }
.attachment-preview button { width: 40px; height: 40px; display: grid; place-items: center; color: var(--muted); background: transparent; border: 1px solid transparent; border-radius: 8px; }
.attachment-preview button:hover:not(:disabled) { color: #ffc8c8; background: rgba(231, 76, 60, .08); border-color: rgba(231, 76, 60, .2); }
.attachment-preview button:disabled { cursor: not-allowed; opacity: .4; }
.composer textarea { width: 100%; height: 52px; min-height: 52px; max-height: 130px; padding: 8px; overflow-y: auto; color: var(--text); background: transparent; border: 0; outline: 0; resize: none; line-height: 1.55; }
.composer textarea::placeholder { color: var(--muted); }
.composer-footer { display: flex; align-items: center; gap: 10px; }
.attach { width: 44px; height: 44px; display: grid; place-items: center; color: var(--text-secondary); background: var(--surface); border: 1px solid var(--border); border-radius: 9px; }
.attach:hover:not(:disabled) { color: var(--primary); border-color: rgba(159, 226, 75, .35); }
.attach:disabled { cursor: not-allowed; opacity: .4; }
.composer-footer > span { color: var(--muted); font-size: .68rem; }
.send-button { min-height: 44px; margin-left: auto; }
.stop-button { min-height: 44px; margin-left: auto; padding: 0 15px; display: inline-flex; align-items: center; justify-content: center; gap: 7px; color: #ffc8c8; background: rgba(240, 103, 95, .1); border: 1px solid rgba(240, 103, 95, .28); border-radius: 9px; font-size: .76rem; font-weight: 600; transition: color 180ms var(--ease-out), background 180ms var(--ease-out), border-color 180ms var(--ease-out); }
.stop-button:hover { color: #fff; background: rgba(240, 103, 95, .18); border-color: rgba(240, 103, 95, .5); }
.composer-error { margin: 8px 2px 0; display: flex; align-items: flex-start; justify-content: center; gap: 6px; color: #ffc8c8; font-size: .68rem; line-height: 1.5; }
.composer-error svg { flex: 0 0 auto; margin-top: 1px; }
.disclaimer { margin: 9px 0 0; display: block; color: var(--muted); font-size: .7rem; text-align: center; }
.spin { animation: spin 800ms linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }
.context-panel { min-height: 0; padding: 24px; overflow-y: auto; background: rgba(13,16,15,.55); border-left: 1px solid var(--border); }
.context-title { display: flex; align-items: center; justify-content: space-between; color: var(--primary); font-size: .8rem; font-weight: 600; }
.context-loading { min-height: 360px; padding-top: 30px; display: grid; align-content: start; gap: 12px; }
.context-loading i { height: 52px; background: linear-gradient(90deg, rgba(255,255,255,.025), rgba(255,255,255,.065), rgba(255,255,255,.025)); background-size: 200% 100%; border-radius: 10px; animation: session-shimmer 1.2s linear infinite; }
.context-loading i:first-child { height: 116px; }
.context-error { min-height: 360px; padding: 28px 8px; display: grid; place-content: center; justify-items: center; gap: 9px; color: #ffaaa5; text-align: center; }
.context-error b { color: var(--text); font-size: .84rem; }
.context-error p { margin: 0; color: var(--muted); font-size: .7rem; line-height: 1.55; }
.context-error button { min-height: 44px; margin-top: 5px; padding: 0 14px; color: #10150e; background: var(--primary); border: 1px solid var(--primary); border-radius: 9px; font-size: .72rem; font-weight: 650; }
.context-error button:hover:not(:disabled) { filter: brightness(1.08); }
.context-error button:focus-visible, .profile-context-note a:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.context-error button:disabled { cursor: wait; opacity: .5; }
.goal-summary { margin: 30px 0; padding: 20px; display: grid; gap: 5px; background: var(--surface); border-radius: 12px; }
.goal-summary small, .goal-summary span { color: var(--muted); font-size: .7rem; }
.goal-summary strong { font-family: "Barlow Condensed"; font-size: 2.5rem; line-height: 1; }
.context-metrics { display: grid; }
.context-metrics div { padding: 15px 0; display: grid; gap: 4px; border-bottom: 1px solid var(--border); }
.context-metrics span { color: var(--muted); font-size: .68rem; }
.context-metrics strong { font-size: .85rem; font-weight: 500; }
.profile-context-note { margin-top: 18px; display: grid; gap: 9px; }
.profile-context-note p { margin: 0; color: var(--muted); font-size: .65rem; line-height: 1.55; }
.profile-context-note a { min-height: 44px; padding: 0 11px; display: flex; align-items: center; justify-content: space-between; color: var(--text-secondary); background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 9px; font-size: .7rem; font-weight: 600; text-decoration: none; transition: color 180ms var(--ease-out), background 180ms var(--ease-out), border-color 180ms var(--ease-out); }
.profile-context-note a:hover { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.28); }
.source-box { margin-top: 26px; padding: 15px; display: flex; gap: 10px; color: var(--primary); background: var(--primary-soft); border-radius: 10px; }
.source-box b { color: var(--text); font-size: .78rem; }.source-box p { margin: 4px 0 0; color: var(--muted); font-size: .68rem; line-height: 1.5; }

@media (max-width: 1180px) {
  .chat-workspace, .chat-workspace.context-hidden { grid-template-columns: 240px minmax(0, 1fr); }
  .context-panel, .context-toggle { display: none; }
}
@media (max-width: 900px) {
  .history-toggle { display: inline-flex; }
  .chat-workspace, .chat-workspace.context-hidden { grid-template-columns: minmax(0, 1fr); }
  .session-panel { position: absolute; z-index: 12; inset: 0 auto 0 0; width: min(320px, calc(100% - 36px)); background: var(--canvas-soft); box-shadow: 18px 0 48px rgba(0,0,0,.32); transform: translateX(-105%); transition: transform 220ms var(--ease-out); }
  .history-open .session-panel { transform: translateX(0); }
  .session-close { display: grid !important; }
  .history-scrim { position: absolute; z-index: 11; inset: 0; display: block; background: rgba(2,4,3,.58); border: 0; }
}
@media (max-width: 760px) {
  .page-head { align-items: flex-start; flex-direction: column; }
  .page-head > :last-child { width: 100%; }
  .page-actions > * { flex: 1; }
  .chat-workspace { height: calc(100dvh - 250px); min-height: 620px; }
  .messages { padding: 22px 14px; }
  .welcome { margin-top: 2vh; }
  .quick-grid { grid-template-columns: 1fr; }
  .quick-grid button { min-height: 80px; }
  .composer-wrap { padding: 10px; }
  .composer-footer > span { display: none; }
  .answer-card { grid-template-columns: 1fr; }
  .answer-card div { border-right: 0; border-bottom: 1px solid var(--border); }
  .answer-card div:last-child { border-bottom: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .quick-grid button, .context-toggle, .history-toggle, .session-panel, .session-list article, .attach, .stop-button { transition: none; }
  .typing i, .spin, .session-loading i, .context-loading i { animation: none; }
}
</style>
