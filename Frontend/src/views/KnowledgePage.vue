<template>
  <div class="knowledge-page page-shell">
    <header class="hero">
      <div>
        <span class="eyebrow"><BookOpenText :size="16" weight="bold" /> FUEL LIBRARY</span>
        <h1 class="page-title">把营养知识，<br><em>变成行动。</em></h1>
        <p class="page-description">{{ activeView === 'library' ? '检索可信资料中的饮食建议，用它校准下一餐、下一次训练和你的减脂计划。' : '从食物、分类与营养素的连接中，更直观地理解每一种选择。' }}</p>
      </div>
      <button class="refresh-button" :disabled="currentViewLoading" :aria-label="activeView === 'library' ? '刷新知识库统计' : '刷新营养知识图谱'" @click="refreshCurrentView">
        <ArrowsClockwise :size="18" :class="{ spinning: currentViewLoading }" aria-hidden="true" />
        刷新
      </button>
    </header>

    <nav class="library-sections surface" aria-label="知识库视图">
      <button type="button" :class="{ active: activeView === 'library' }" :aria-current="activeView === 'library' ? 'page' : undefined" @click="setActiveView('library')">
        <BookOpenText :size="20" /><span><b>知识检索</b><small>问答、搜索与资料管理</small></span>
      </button>
      <button type="button" :class="{ active: activeView === 'graph' }" :aria-current="activeView === 'graph' ? 'page' : undefined" @click="setActiveView('graph')">
        <GraphIcon :size="20" /><span><b>营养图谱</b><small>探索食物与营养关系</small></span>
      </button>
    </nav>

    <template v-if="activeView === 'library'">
    <section class="search-command surface" aria-labelledby="search-title">
      <div class="command-index">01</div>
      <div class="command-content">
        <div class="command-heading">
          <div>
            <span>ASK THE LIBRARY</span>
            <h2 id="search-title" class="section-title">你想解决什么营养问题？</h2>
          </div>
          <label class="result-limit">
            <span>返回数量</span>
            <select v-model.number="limit" aria-label="检索结果数量">
              <option v-for="number in [3, 5, 10]" :key="number" :value="number">{{ number }} 条</option>
            </select>
          </label>
        </div>
        <div class="query-modes" role="tablist" aria-label="知识库使用方式">
          <button
            type="button"
            role="tab"
            :aria-selected="mode === 'ask'"
            :class="{ active: mode === 'ask' }"
            :disabled="searching"
            @click="mode = 'ask'"
          >
            <Sparkle :size="17" weight="fill" />生成知识回答
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="mode === 'search'"
            :class="{ active: mode === 'search' }"
            :disabled="searching"
            @click="mode = 'search'"
          >
            <MagnifyingGlass :size="17" />查找原始片段
          </button>
        </div>
        <div v-if="mode === 'ask'" class="ask-options" aria-label="知识回答选项">
          <button type="button" :aria-pressed="verifyWeb" :class="{ active: verifyWeb }" @click="verifyWeb = !verifyWeb">
            <GlobeHemisphereWest :size="18" />
            <span><b>网页交叉核验</b><small>同时查询网页来源进行补充与核验</small></span>
          </button>
          <button type="button" :aria-pressed="storeWeb" :class="{ active: storeWeb }" @click="storeWeb = !storeWeb">
            <Database :size="18" />
            <span><b>保留网页结果</b><small>若使用网页资料，允许后端写入知识库</small></span>
          </button>
        </div>
        <div class="query-box">
          <Sparkle v-if="mode === 'ask'" :size="22" weight="fill" aria-hidden="true" />
          <MagnifyingGlass v-else :size="22" aria-hidden="true" />
          <textarea
            v-model="query"
            rows="2"
            maxlength="200"
            placeholder="例如：减脂期力量训练后，蛋白质和碳水应该怎么搭配？"
            aria-label="营养知识问题"
            @keydown.ctrl.enter="runQuery"
          />
          <FuelButton class="search-action" :loading="searching" :disabled="!query.trim()" @click="runQuery">
            {{ mode === 'ask' ? '生成回答' : '开始检索' }}
          </FuelButton>
        </div>
        <div class="quick-queries" aria-label="快捷问题">
          <span>快速开始</span>
          <button v-for="item in quickQueries" :key="item" @click="useQuickQuery(item)">{{ item }}</button>
          <small>Ctrl + Enter 提交</small>
        </div>
      </div>
    </section>

    <section class="stats-grid" aria-label="知识库概览">
      <SpotlightCard class="stat-card" spotlight-color="rgba(159, 226, 75, .13)">
        <Files :size="24" weight="duotone" aria-hidden="true" />
        <div><strong class="metric-number"><CountUp :to="stats.total_documents" /></strong><span>份可信资料</span></div>
        <small>已完成解析</small>
      </SpotlightCard>
      <SpotlightCard class="stat-card" spotlight-color="rgba(242, 117, 63, .12)">
        <Stack :size="24" weight="duotone" aria-hidden="true" />
        <div><strong class="metric-number"><CountUp :to="stats.total_chunks" /></strong><span>个知识片段</span></div>
        <small>可用于语义检索</small>
      </SpotlightCard>
      <div class="stat-card formats surface">
        <FileText :size="24" weight="duotone" aria-hidden="true" />
        <div><strong class="metric-number">09</strong><span>种文件格式</span></div>
        <small>PDF · MD · TXT + 常见图片</small>
      </div>
    </section>

    <section class="workspace-grid">
      <div class="results-panel surface" aria-live="polite">
        <div class="panel-heading">
          <div>
            <span class="panel-kicker">{{ mode === 'ask' ? 'GROUNDED ANSWER' : 'SEARCH OUTPUT' }}</span>
            <h2 class="section-title">{{ mode === 'ask' ? '知识库回答' : '检索结果' }}</h2>
          </div>
          <span v-if="mode === 'ask' && answer" class="status-chip">{{ answer.sources.length }} 个来源</span>
          <span v-else-if="mode === 'search' && hasSearched" class="status-chip">{{ results.length }} 条匹配</span>
        </div>

        <div v-if="searching" class="loading-results" aria-label="正在检索">
          <div v-for="number in 3" :key="number" class="result-skeleton"><i /><i /><i /></div>
        </div>
        <template v-else-if="mode === 'ask'">
          <div v-if="askError" class="answer-error" role="alert">
            <WarningCircle :size="28" />
            <div><h3>这次回答没有生成成功</h3><p>{{ askError }}</p></div>
            <button type="button" @click="runQuery">重新生成</button>
          </div>
          <div v-else-if="!answer" class="empty-state">
            <Sparkle :size="42" weight="thin" aria-hidden="true" />
            <h3>{{ hasAsked ? '后端没有返回可展示的回答' : '等待你的第一个问题' }}</h3>
            <p>系统会先检索知识库，再生成带来源的完整建议；需要时也能补充网页资料。</p>
          </div>
          <article v-else class="answer-output">
            <header class="answer-meta">
              <span><CheckCircle :size="17" weight="fill" />基于检索资料生成</span>
              <span v-if="answer.usedWebFallback"><GlobeHemisphereWest :size="17" />已使用网页补充</span>
              <span v-if="answer.crossVerified"><ShieldCheck :size="17" />已交叉核验</span>
            </header>
            <div class="answer-markdown" v-html="renderMarkdown(answer.answer)" />
            <section v-if="answer.sources.length" class="answer-sources" aria-labelledby="answer-sources-title">
              <div class="source-heading">
                <div><span>REFERENCES</span><h3 id="answer-sources-title">回答来源</h3></div>
                <small>本地分值为向量距离，越低通常越相关</small>
              </div>
              <div class="source-cards">
                <component
                  :is="source.url ? 'a' : 'div'"
                  v-for="source in answer.sources"
                  :key="source.id"
                  class="answer-source"
                  :href="source.url || undefined"
                  :target="source.url ? '_blank' : undefined"
                  :rel="source.url ? 'noopener noreferrer' : undefined"
                >
                  <span class="source-type" :class="source.type">
                    <GlobeHemisphereWest v-if="source.type === 'web'" :size="16" />
                    <BookOpenText v-else :size="16" />
                    {{ source.type === 'web' ? '网页来源' : '本地知识' }}
                  </span>
                  <h4>{{ source.title }}</h4>
                  <p v-if="source.excerpt">{{ source.excerpt }}</p>
                  <footer>
                    <span v-if="source.score !== null">距离 {{ formatDistance(source.score) }}</span>
                    <span v-else>{{ source.url ? '打开原网页' : '未提供分值' }}</span>
                    <LinkSimple v-if="source.url" :size="15" />
                  </footer>
                </component>
              </div>
            </section>
          </article>
        </template>
        <template v-else>
          <div v-if="!results.length" class="empty-state">
            <MagnifyingGlass :size="42" weight="thin" aria-hidden="true" />
            <h3>{{ hasSearched ? '暂时没有匹配结果' : '等待你的第一个问题' }}</h3>
            <p>{{ hasSearched ? '换一种更具体的描述，或先上传相关营养资料。' : '搜索膳食、营养素、热量控制或运动补给建议。' }}</p>
          </div>
          <div v-else class="results-list">
            <article v-for="(item, index) in results" :key="`${item.source}-${index}`" class="result-item">
              <header>
                <span class="result-rank">{{ String(index + 1).padStart(2, '0') }}</span>
                <div class="source-name"><FileText :size="17" />{{ item.fileName || item.source || '未知来源' }}</div>
                <div class="relevance" :aria-label="`相关度 ${formatScore(item.score)}`">
                  <span><i :style="{ width: formatScore(item.score) }" /></span>
                  {{ formatScore(item.score) }}
                </div>
                <button v-if="item.source" class="delete-button" :aria-label="`删除来源 ${item.fileName || item.source}`" @click="remove(item)">
                  <Trash :size="17" />
                </button>
              </header>
              <p>{{ item.content }}</p>
            </article>
          </div>
        </template>
      </div>

      <aside class="upload-panel surface" aria-labelledby="upload-title">
        <div class="panel-heading">
          <div>
            <span class="panel-kicker">BUILD YOUR SOURCE</span>
            <h2 id="upload-title" class="section-title">添加可信资料</h2>
          </div>
          <span class="command-index small">02</span>
        </div>
        <p>上传膳食指南、课程资料、论文笔记或知识图片，系统会解析为可检索片段。</p>
        <el-upload
          ref="uploadRef"
          drag
          :auto-upload="false"
          :limit="1"
          :accept="accept"
          :on-change="onFileChange"
          :on-remove="onFileRemove"
          :on-exceed="onFileExceed"
        >
          <div class="drop-visual"><UploadSimple :size="29" weight="bold" /></div>
          <b>拖入文件，或点击选择</b>
          <span>PDF、Markdown、纯文本或常见图片</span>
        </el-upload>
        <div class="privacy-note"><ShieldCheck :size="17" /><span>请仅上传你信任且有权使用的资料。</span></div>
        <FuelButton class="upload-action" :loading="uploading" :disabled="!selectedFile" @click="upload">
          {{ selectedFile ? '解析这份资料' : '等待选择文件' }}
        </FuelButton>
      </aside>
    </section>
    </template>

    <NutritionKnowledgeGraph
      v-else
      :nodes="graph.nodes"
      :edges="graph.edges"
      :loading="graphLoading"
      :error="graphError"
      @retry="loadGraph"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  PhArrowsClockwise as ArrowsClockwise, PhBookOpenText as BookOpenText,
  PhCheckCircle as CheckCircle, PhDatabase as Database, PhFiles as Files,
  PhFileText as FileText, PhGlobeHemisphereWest as GlobeHemisphereWest,
  PhGraph as GraphIcon, PhLinkSimple as LinkSimple, PhMagnifyingGlass as MagnifyingGlass,
  PhShieldCheck as ShieldCheck, PhSparkle as Sparkle, PhStack as Stack,
  PhTrash as Trash, PhUploadSimple as UploadSimple, PhWarningCircle as WarningCircle,
} from '@phosphor-icons/vue'
import CountUp from '@/components/motion/CountUp.vue'
import SpotlightCard from '@/components/motion/SpotlightCard.vue'
import FuelButton from '@/components/ui/FuelButton.vue'
import NutritionKnowledgeGraph from '@/components/knowledge/NutritionKnowledgeGraph.vue'
import { askKnowledgeApi, deleteDocumentApi, getKnowledgeGraphApi, getKnowledgeStatsApi, searchKnowledgeApi, uploadDocumentApi } from '@/api/knowledge'
import { useUserStore } from '@/stores/user'
import { normalizeKnowledgeAnswer, normalizeKnowledgeGraph, normalizeKnowledgeSearch, normalizeKnowledgeStats } from '@/utils/knowledgeData'
import { renderMarkdown } from '@/utils/markdown'

const accept = '.pdf,.md,.txt,.png,.jpg,.jpeg,.gif,.bmp,.webp'
const quickQueries = ['减脂期怎么吃', '训练后补给', '膳食纤维摄入']
const activeView = ref('library')
const uploadRef = ref()
const selectedFile = ref(null)
const uploading = ref(false)
const searching = ref(false)
const statsLoading = ref(false)
const graphLoading = ref(false)
const graphLoaded = ref(false)
const graphError = ref('')
const query = ref('')
const limit = ref(5)
const mode = ref('ask')
const verifyWeb = ref(false)
const storeWeb = ref(true)
const answer = ref(null)
const hasAsked = ref(false)
const askError = ref('')
const results = ref([])
const hasSearched = ref(false)
const stats = reactive({ total_documents: 0, total_chunks: 0 })
const graph = reactive({ nodes: [], edges: [] })
const userStore = useUserStore()
const currentViewLoading = computed(() => activeView.value === 'graph' ? graphLoading.value : statsLoading.value)
const demoResults = [
  { source: '中国居民膳食指南（演示）.pdf', score: 0.94, content: '成年人应保持食物多样，合理搭配谷薯类、蔬菜水果、动物性食物以及奶豆坚果类食物，并结合自身活动水平控制总能量摄入。' },
  { source: '运动营养基础（演示）.md', score: 0.88, content: '处于减脂阶段时，应优先保证蛋白质摄入和力量训练，并设置适度、可持续的热量缺口，避免过度节食影响训练表现。' },
  { source: '常见食物营养数据（演示）.txt', score: 0.82, content: '鸡胸肉是常见的优质蛋白质来源。实际热量会受到食材重量、烹饪方式和调味用量影响，图片识别结果应作为估算参考。' },
]
const demoAnswer = {
  query: '减脂期怎么吃',
  answer: '减脂期的核心是保持**适度且可持续的热量缺口**，同时尽量保住肌肉和训练表现。\n\n- 每餐优先安排一掌心左右的优质蛋白质\n- 用全谷物、薯类和蔬菜提高饱腹感\n- 训练前后保留适量碳水，不必完全戒掉主食\n- 连续观察 2—3 周的体重趋势，再小幅调整总摄入\n\n如果有慢性疾病或明显不适，请让医生或注册营养师提供个体化建议。',
  sources: [
    { id: 'demo-local-1', type: 'knowledge', title: '中国居民膳食指南（演示）', score: 0.18, excerpt: '保持食物多样和平衡膳食，并结合身体活动控制总能量摄入。' },
    { id: 'demo-local-2', type: 'knowledge', title: '运动营养基础（演示）', score: 0.27, excerpt: '减脂阶段应优先保证蛋白质和力量训练，避免过度节食。' },
  ],
  localResults: [], webResults: [], usedWebFallback: false, crossVerified: false,
}
const demoGraph = {
  nodes: [
    { id: 'cat_meat', label: '肉蛋类', type: 'category', group: 'category' },
    { id: 'cat_fruit', label: '水果', type: 'category', group: 'category' },
    { id: 'cat_grain', label: '谷物', type: 'category', group: 'category' },
    { id: 'food_chicken', label: '鸡胸肉', name_en: 'Chicken breast', type: 'food', group: 'food', category: '肉蛋类', calories: 165, protein: 31, fat: 3.6, carbs: 0, fiber: 0 },
    { id: 'food_egg', label: '鸡蛋', name_en: 'Egg', type: 'food', group: 'food', category: '肉蛋类', calories: 143, protein: 12.6, fat: 9.5, carbs: 0.7, fiber: 0 },
    { id: 'food_apple', label: '苹果', name_en: 'Apple', type: 'food', group: 'food', category: '水果', calories: 52, protein: 0.3, fat: 0.2, carbs: 13.8, fiber: 2.4 },
    { id: 'food_oats', label: '燕麦', name_en: 'Oats', type: 'food', group: 'food', category: '谷物', calories: 389, protein: 16.9, fat: 6.9, carbs: 66.3, fiber: 10.6 },
    { id: 'nut_calories', label: '热量', type: 'nutrient', group: 'nutrient', unit: 'kcal' },
    { id: 'nut_protein', label: '蛋白质', type: 'nutrient', group: 'nutrient', unit: 'g' },
    { id: 'nut_fat', label: '脂肪', type: 'nutrient', group: 'nutrient', unit: 'g' },
    { id: 'nut_carbs', label: '碳水化合物', type: 'nutrient', group: 'nutrient', unit: 'g' },
    { id: 'nut_fiber', label: '膳食纤维', type: 'nutrient', group: 'nutrient', unit: 'g' },
  ],
  edges: [],
}

demoGraph.nodes.filter((node) => node.type === 'food').forEach((food) => {
  const categoryId = food.category === '肉蛋类' ? 'cat_meat' : food.category === '水果' ? 'cat_fruit' : 'cat_grain'
  demoGraph.edges.push({ source: food.id, target: categoryId, relation: 'BELONGS_TO' })
  ;[
    ['calories', 'nut_calories'], ['protein', 'nut_protein'], ['fat', 'nut_fat'],
    ['carbs', 'nut_carbs'], ['fiber', 'nut_fiber'],
  ].forEach(([field, target]) => {
    if (food[field] > 0) demoGraph.edges.push({ source: food.id, target, relation: 'HAS_NUTRIENT', value: food[field] })
  })
})

function payloadData(payload) { return payload?.data ?? payload }

function setActiveView(view) {
  activeView.value = view
  if (view === 'graph' && !graphLoaded.value) loadGraph()
}

function refreshCurrentView() {
  if (activeView.value === 'graph') loadGraph()
  else loadStats()
}

async function loadGraph() {
  if (graphLoading.value) return
  graphLoading.value = true
  graphError.value = ''
  try {
    const data = userStore.isDemo
      ? normalizeKnowledgeGraph(demoGraph)
      : normalizeKnowledgeGraph(await getKnowledgeGraphApi({ silent: true }))
    graph.nodes = data.nodes
    graph.edges = data.edges
    graphLoaded.value = true
  } catch {
    graph.nodes = []
    graph.edges = []
    graphError.value = '当前无法取得图谱数据，请稍后重新加载。'
  } finally {
    graphLoading.value = false
  }
}

async function loadStats() {
  if (userStore.isDemo) {
    stats.total_documents = 12
    stats.total_chunks = 286
    return
  }
  statsLoading.value = true
  try {
    const data = normalizeKnowledgeStats(await getKnowledgeStatsApi())
    stats.total_documents = data.total_documents
    stats.total_chunks = data.total_chunks
  } finally {
    statsLoading.value = false
  }
}

function onFileChange(file) { selectedFile.value = file.raw }
function onFileRemove() { selectedFile.value = null }
function onFileExceed() { ElMessage.warning('每次只能上传一个文件，请先移除当前文件') }

async function upload() {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    if (userStore.isDemo) {
      ElMessage.success('预览模式：已模拟完成文档解析')
    } else {
      const data = payloadData(await uploadDocumentApi(selectedFile.value))
      ElMessage.success(`上传成功，生成 ${data?.chunks_count ?? 0} 个知识片段`)
      await loadStats()
    }
    selectedFile.value = null
    uploadRef.value?.clearFiles()
  } finally {
    uploading.value = false
  }
}

function useQuickQuery(value) {
  query.value = value
  runQuery()
}

async function runQuery() {
  if (!query.value.trim()) {
    ElMessage.warning('请输入你的营养问题')
    return
  }
  if (mode.value === 'ask') await ask()
  else await search()
}

async function ask() {
  searching.value = true
  hasAsked.value = true
  askError.value = ''
  const submittedQuery = query.value.trim()
  try {
    if (userStore.isDemo) {
      await new Promise((resolve) => setTimeout(resolve, 520))
      answer.value = {
        ...demoAnswer,
        query: submittedQuery,
        usedWebFallback: verifyWeb.value,
        crossVerified: verifyWeb.value,
        sources: verifyWeb.value
          ? [...demoAnswer.sources, { id: 'demo-web-1', type: 'web', title: '权威健康资料（演示网页）', url: 'https://example.org', score: null, excerpt: '网页资料用于演示交叉核验状态。' }]
          : demoAnswer.sources,
      }
      return
    }
    answer.value = normalizeKnowledgeAnswer(await askKnowledgeApi({
      query: submittedQuery,
      k: limit.value,
      verify_web: verifyWeb.value,
      store_web: storeWeb.value,
    }))
  } catch {
    answer.value = null
    askError.value = '后端可能仍在处理资料，或当前网络不可用。请稍后重试。'
    ElMessage.error('知识回答生成失败')
  } finally {
    searching.value = false
  }
}

async function search() {
  searching.value = true
  hasSearched.value = true
  const submittedQuery = query.value.trim()
  try {
    if (userStore.isDemo) {
      await new Promise((resolve) => setTimeout(resolve, 520))
      results.value = demoResults.slice(0, limit.value)
      return
    }
    const data = normalizeKnowledgeSearch(await searchKnowledgeApi({ query: submittedQuery, k: limit.value }))
    results.value = data.results
  } finally {
    searching.value = false
  }
}

async function remove(item) {
  const source = item.source
  const displayName = item.fileName || source
  try {
    await ElMessageBox.confirm(`删除后将无法检索“${displayName}”中的内容，是否继续？`, '确认删除知识来源', {
      type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消',
    })
    if (!userStore.isDemo) await deleteDocumentApi(source)
    results.value = results.value.filter((item) => item.source !== source)
    ElMessage.success(userStore.isDemo ? '预览模式：已模拟删除知识来源' : '知识来源已删除')
    await loadStats()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') throw error
  }
}

function formatScore(score) {
  const number = Number(score)
  if (!Number.isFinite(number)) return '--'
  return `${Math.round(Math.min(Math.max(number, 0), 1) * 100)}%`
}

function formatDistance(score) {
  const number = Number(score)
  return Number.isFinite(number) ? number.toFixed(3) : '--'
}

onMounted(loadStats)
</script>

<style lang="scss" scoped>
.knowledge-page { display: grid; gap: 22px; }
.hero { min-height: 220px; padding: clamp(24px, 4vw, 54px) clamp(20px, 4vw, 58px); display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; overflow: hidden; background: linear-gradient(112deg, rgba(26, 32, 27, .98), rgba(17, 21, 18, .88)), radial-gradient(circle at 78% 10%, rgba(159, 226, 75, .18), transparent 38%); border: 1px solid var(--border); border-radius: var(--radius-lg); }
.hero em { color: var(--primary); font-style: normal; }
.eyebrow, .panel-kicker { color: var(--primary); font-size: .74rem; font-weight: 700; letter-spacing: .13em; }
.eyebrow { margin-bottom: 17px; display: flex; align-items: center; gap: 8px; }
.refresh-button { min-height: 42px; padding: 0 14px; display: inline-flex; align-items: center; gap: 8px; color: var(--text-secondary); background: rgba(255,255,255,.035); border: 1px solid var(--border); border-radius: 10px; }
.refresh-button:hover { color: var(--primary); border-color: rgba(159,226,75,.35); }
.spinning { animation: spin .8s linear infinite; }
.library-sections { padding: 5px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px; }
.library-sections button { min-height: 68px; padding: 10px 16px; display: flex; align-items: center; gap: 11px; color: var(--muted); background: transparent; border: 1px solid transparent; border-radius: 11px; text-align: left; transition: color 170ms var(--ease-out), background 170ms var(--ease-out), border-color 170ms var(--ease-out); }
.library-sections button:hover { color: var(--text-secondary); background: rgba(255,255,255,.018); }
.library-sections button.active { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.19); }
.library-sections button > span { min-width: 0; display: grid; gap: 2px; }
.library-sections b { color: currentColor; font-size: .8rem; }
.library-sections small { color: var(--muted); font-size: .65rem; }
.search-command { padding: 22px; display: grid; grid-template-columns: 58px 1fr; gap: 20px; }
.command-index { color: var(--primary); font-family: "Barlow Condensed"; font-size: 2rem; font-weight: 600; }
.command-index.small { font-size: 1.25rem; }
.command-content { min-width: 0; }
.command-heading { margin-bottom: 18px; display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; }
.command-heading > div > span { display: block; margin-bottom: 4px; color: var(--muted); font-size: .7rem; font-weight: 600; letter-spacing: .13em; }
.result-limit { display: flex; align-items: center; gap: 9px; color: var(--muted); font-size: .72rem; }
.result-limit select { height: 36px; padding: 0 28px 0 10px; color: var(--text); background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 8px; }
.query-modes { margin: 0 0 12px; padding: 4px; display: inline-flex; gap: 4px; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 11px; }
.query-modes button { min-height: 40px; padding: 0 13px; display: inline-flex; align-items: center; gap: 7px; color: var(--muted); background: transparent; border: 1px solid transparent; border-radius: 8px; font-size: .74rem; font-weight: 600; transition: color 160ms var(--ease-out), background 160ms var(--ease-out), border-color 160ms var(--ease-out); }
.query-modes button.active { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.18); }
.query-modes button:disabled { cursor: wait; opacity: .55; }
.ask-options { margin-bottom: 12px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.ask-options button { min-height: 58px; padding: 9px 12px; display: grid; grid-template-columns: 20px minmax(0, 1fr); align-items: center; gap: 9px; color: var(--muted); background: rgba(255,255,255,.018); border: 1px solid var(--border); border-radius: 10px; text-align: left; transition: color 160ms var(--ease-out), background 160ms var(--ease-out), border-color 160ms var(--ease-out); }
.ask-options button > span { min-width: 0; display: grid; gap: 3px; }
.ask-options b { color: var(--text-secondary); font-size: .72rem; }
.ask-options small { overflow: hidden; color: var(--muted); font-size: .62rem; text-overflow: ellipsis; white-space: nowrap; }
.ask-options button.active { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.22); }
.ask-options button.active b { color: var(--primary); }
.query-box { min-height: 90px; padding: 13px 13px 13px 17px; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 13px; background: var(--canvas-soft); border: 1px solid var(--border-strong); border-radius: 14px; transition: border-color 180ms var(--ease-out), box-shadow 180ms var(--ease-out); }
.query-box:focus-within { border-color: rgba(159,226,75,.65); box-shadow: 0 0 0 3px rgba(159,226,75,.08); }
.query-box > svg { color: var(--primary); }
.query-box textarea { width: 100%; min-height: 58px; padding: 7px 0; resize: none; color: var(--text); background: transparent; border: 0; outline: 0; line-height: 1.55; }
.query-box textarea::placeholder { color: var(--muted); }
.search-action { min-width: 132px; }
.quick-queries { margin-top: 13px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.quick-queries > span { color: var(--muted); font-size: .72rem; }
.quick-queries button { min-height: 32px; padding: 0 10px; color: var(--text-secondary); background: transparent; border: 1px solid var(--border); border-radius: 7px; font-size: .72rem; }
.quick-queries button:hover { color: var(--primary); border-color: rgba(159,226,75,.32); }
.quick-queries small { margin-left: auto; color: var(--muted); }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.stat-card { min-height: 126px; padding: 20px; display: grid; grid-template-columns: auto 1fr; align-content: center; column-gap: 15px; }
.stat-card > svg { color: var(--primary); }
.stat-card:nth-child(2) > svg { color: var(--accent); }
.stat-card div { display: flex; align-items: baseline; gap: 9px; }
.stat-card strong { font-size: 2rem; line-height: 1; }
.stat-card div span { color: var(--text-secondary); font-size: .82rem; }
.stat-card small { grid-column: 2; margin-top: 7px; color: var(--muted); }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(300px, .65fr); gap: 16px; align-items: start; }
.results-panel, .upload-panel { padding: clamp(18px, 2.5vw, 28px); }
.panel-heading { margin-bottom: 22px; padding-bottom: 18px; display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--border); }
.panel-kicker { display: block; margin-bottom: 5px; color: var(--muted); font-size: .7rem; }
.empty-state { min-height: 300px; display: grid; place-items: center; align-content: center; text-align: center; }
.empty-state svg { margin-bottom: 14px; color: var(--muted); }
.empty-state h3 { margin: 0 0 7px; font-size: 1rem; }
.empty-state p { max-width: 38ch; margin: 0; color: var(--muted); font-size: .84rem; }
.loading-results, .results-list { display: grid; gap: 11px; }
.result-skeleton, .result-item { padding: 18px; background: rgba(255,255,255,.022); border: 1px solid var(--border); border-radius: 12px; }
.result-skeleton { display: grid; gap: 10px; }
.result-skeleton i { height: 10px; background: linear-gradient(90deg, var(--surface-soft), rgba(255,255,255,.07), var(--surface-soft)); background-size: 200% 100%; border-radius: 6px; animation: shimmer 1.2s infinite linear; }
.result-skeleton i:nth-child(1) { width: 38%; }.result-skeleton i:nth-child(3) { width: 72%; }
.answer-error { min-height: 230px; padding: 30px; display: grid; grid-template-columns: auto minmax(0,1fr) auto; align-items: center; gap: 15px; color: #ffc8c8; background: rgba(240,103,95,.055); border: 1px solid rgba(240,103,95,.18); border-radius: 12px; }
.answer-error h3 { margin: 0 0 5px; color: var(--text); font-size: .9rem; }
.answer-error p { margin: 0; color: var(--text-secondary); font-size: .76rem; }
.answer-error button { min-height: 42px; padding: 0 14px; color: #ffc8c8; background: rgba(240,103,95,.08); border: 1px solid rgba(240,103,95,.22); border-radius: 9px; font-size: .72rem; }
.answer-output { overflow: hidden; background: rgba(255,255,255,.018); border: 1px solid var(--border); border-radius: 14px; }
.answer-meta { padding: 12px 16px; display: flex; align-items: center; flex-wrap: wrap; gap: 7px; background: var(--canvas-soft); border-bottom: 1px solid var(--border); }
.answer-meta span { min-height: 30px; padding: 0 9px; display: inline-flex; align-items: center; gap: 6px; color: var(--text-secondary); background: var(--surface); border: 1px solid var(--border); border-radius: 8px; font-size: .65rem; }
.answer-meta span:first-child { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.16); }
.answer-markdown { padding: clamp(20px, 3.5vw, 36px); color: var(--text-secondary); font-size: .91rem; line-height: 1.8; }
.answer-markdown :deep(h1), .answer-markdown :deep(h2), .answer-markdown :deep(h3) { margin: 1.3em 0 .55em; color: var(--text); line-height: 1.3; }
.answer-markdown :deep(h1:first-child), .answer-markdown :deep(h2:first-child), .answer-markdown :deep(h3:first-child), .answer-markdown :deep(p:first-child) { margin-top: 0; }
.answer-markdown :deep(p) { margin: 0 0 13px; }
.answer-markdown :deep(p:last-child) { margin-bottom: 0; }
.answer-markdown :deep(ul), .answer-markdown :deep(ol) { margin: 10px 0 15px; padding-left: 22px; }
.answer-markdown :deep(li) { margin: 5px 0; }
.answer-markdown :deep(strong) { color: var(--text); }
.answer-markdown :deep(a) { color: var(--primary); text-underline-offset: 3px; }
.answer-sources { padding: 20px; background: rgba(5,8,6,.2); border-top: 1px solid var(--border); }
.source-heading { margin-bottom: 13px; display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; }
.source-heading > div > span { color: var(--primary); font-size: .61rem; font-weight: 700; letter-spacing: .12em; }
.source-heading h3 { margin: 3px 0 0; font-size: .9rem; }
.source-heading small { color: var(--muted); font-size: .61rem; }
.source-cards { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 9px; }
.answer-source { min-width: 0; padding: 14px; display: flex; flex-direction: column; color: inherit; background: rgba(255,255,255,.022); border: 1px solid var(--border); border-radius: 10px; text-decoration: none; transition: transform 160ms var(--ease-out), border-color 160ms var(--ease-out); }
a.answer-source:hover { border-color: rgba(159,226,75,.3); transform: translateY(-2px); }
.source-type { display: inline-flex; align-items: center; gap: 5px; color: var(--primary); font-size: .61rem; font-weight: 650; }
.source-type.web { color: #7ec9ff; }
.answer-source h4 { margin: 9px 0 0; overflow: hidden; color: var(--text); font-size: .76rem; text-overflow: ellipsis; white-space: nowrap; }
.answer-source p { margin: 8px 0 12px; display: -webkit-box; overflow: hidden; color: var(--muted); font-size: .68rem; line-height: 1.55; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }
.answer-source footer { margin-top: auto; padding-top: 10px; display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--muted); border-top: 1px solid var(--border); font-size: .6rem; }
.result-item { transition: transform 180ms var(--ease-out), border-color 180ms var(--ease-out); }
.result-item:hover { border-color: var(--border-strong); transform: translateY(-2px); }
.result-item header { display: flex; align-items: center; gap: 10px; }
.result-rank { color: var(--primary); font-family: "Barlow Condensed"; font-size: 1.1rem; font-weight: 600; }
.source-name { min-width: 0; display: flex; align-items: center; gap: 7px; overflow: hidden; color: var(--text-secondary); font-size: .8rem; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.relevance { margin-left: auto; display: flex; align-items: center; gap: 7px; color: var(--muted); font-size: .72rem; }
.relevance > span { width: 44px; height: 4px; overflow: hidden; background: var(--surface-soft); border-radius: 4px; }
.relevance i { height: 100%; display: block; background: var(--primary); border-radius: inherit; }
.delete-button { width: 34px; height: 34px; display: grid; place-items: center; color: var(--muted); background: transparent; border: 0; border-radius: 7px; }
.delete-button:hover { color: var(--danger); background: rgba(240,103,95,.1); }
.result-item p { margin: 14px 0 0; padding-top: 14px; color: var(--text-secondary); border-top: 1px solid var(--border); font-size: .88rem; line-height: 1.75; white-space: pre-wrap; }
.upload-panel { position: sticky; top: 18px; }
.upload-panel > p { margin: -7px 0 18px; color: var(--text-secondary); font-size: .84rem; line-height: 1.65; }
.upload-panel :deep(.el-upload) { width: 100%; }
.upload-panel :deep(.el-upload-dragger) { width: 100%; min-height: 210px; padding: 28px 18px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px dashed var(--border-strong); border-radius: 13px; }
.upload-panel :deep(.el-upload-dragger:hover) { border-color: var(--primary); }
.drop-visual { width: 54px; height: 54px; margin-bottom: 15px; display: grid; place-items: center; color: #12170f; background: var(--primary); border-radius: 14px; transform: rotate(-4deg); }
.upload-panel :deep(.el-upload-dragger b) { color: var(--text); font-size: .86rem; }
.upload-panel :deep(.el-upload-dragger > span) { margin-top: 5px; color: var(--muted); font-size: .74rem; }
.privacy-note { margin: 13px 0; display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: .72rem; }
.privacy-note svg { color: var(--primary); flex: 0 0 auto; }
.upload-action { width: 100%; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes shimmer { to { background-position: -200% 0; } }
@media (max-width: 1050px) {
  .workspace-grid { grid-template-columns: 1fr; }
  .upload-panel { position: static; }
}
@media (max-width: 760px) {
  .hero { min-height: 190px; align-items: flex-start; }
  .refresh-button { padding: 0; width: 42px; justify-content: center; }
  .refresh-button:not(:focus) { font-size: 0; }
  .search-command { grid-template-columns: 1fr; }
  .command-index { display: none; }
  .query-box { grid-template-columns: auto 1fr; }
  .search-action { grid-column: 1 / -1; width: 100%; }
  .ask-options { grid-template-columns: 1fr; }
  .stats-grid { grid-template-columns: 1fr 1fr; }
  .formats { display: none; }
  .quick-queries small { display: none; }
}
@media (max-width: 520px) {
  .hero { padding: 26px 20px; }
  .library-sections { grid-template-columns: 1fr; }
  .command-heading { align-items: flex-start; }
  .result-limit { flex-direction: column; align-items: flex-end; gap: 4px; }
  .query-modes { width: 100%; }
  .query-modes button { min-width: 0; flex: 1; padding: 0 8px; justify-content: center; }
  .stats-grid { grid-template-columns: 1fr; }
  .formats { display: grid; }
  .result-item header { flex-wrap: wrap; }
  .source-name { flex: 1; }
  .relevance { order: 3; margin-left: 32px; }
  .delete-button { margin-left: auto; }
  .source-heading { align-items: flex-start; flex-direction: column; gap: 5px; }
  .source-cards { grid-template-columns: 1fr; }
  .answer-error { grid-template-columns: auto 1fr; padding: 22px 18px; }
  .answer-error button { grid-column: 1 / -1; }
}
@media (prefers-reduced-motion: reduce) {
  .library-sections button, .query-box, .query-modes button, .ask-options button, .result-item, .answer-source { transition: none; }
  .spinning, .result-skeleton i { animation: none; }
}
</style>
