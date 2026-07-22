<template>
  <section class="graph-shell surface" aria-labelledby="nutrition-graph-title">
    <header class="graph-heading">
      <div>
        <span class="panel-kicker">NUTRITION RELATION MAP</span>
        <h2 id="nutrition-graph-title" class="section-title">营养知识图谱</h2>
        <p>探索食物、类别与核心营养素之间的关系。选择任意节点即可查看它的关联信息。</p>
      </div>
      <div class="graph-totals" aria-label="图谱数据概览">
        <span><b>{{ typeCounts.food }}</b> 种食物</span>
        <span><b>{{ typeCounts.category }}</b> 个分类</span>
        <span><b>{{ typeCounts.nutrient }}</b> 项营养素</span>
      </div>
    </header>

    <div class="graph-controls">
      <label class="graph-search">
        <span class="sr-only">搜索图谱节点</span>
        <MagnifyingGlass :size="18" aria-hidden="true" />
        <input v-model.trim="searchQuery" type="search" placeholder="搜索食物、分类或营养素" />
      </label>

      <div class="type-filters" aria-label="显示的节点类型">
        <button
          v-for="item in typeOptions"
          :key="item.id"
          type="button"
          :class="[item.id, { active: enabledTypes.includes(item.id) }]"
          :aria-pressed="enabledTypes.includes(item.id)"
          @click="toggleType(item.id)"
        >
          <i aria-hidden="true" />{{ item.label }}
        </button>
      </div>

      <div class="view-switch" role="group" aria-label="图谱展示方式">
        <button type="button" :class="{ active: displayMode === 'graph' }" :aria-pressed="displayMode === 'graph'" @click="displayMode = 'graph'">
          <GraphIcon :size="18" />关系图
        </button>
        <button type="button" :class="{ active: displayMode === 'list' }" :aria-pressed="displayMode === 'list'" @click="displayMode = 'list'">
          <ListBullets :size="18" />食物列表
        </button>
      </div>
    </div>

    <div v-if="loading" class="graph-loading" aria-live="polite" aria-label="正在加载营养知识图谱">
      <div class="graph-skeleton"><i v-for="number in 14" :key="number" /></div>
      <p>正在整理食物与营养素的关系…</p>
    </div>

    <div v-else-if="error" class="graph-state error-state" role="alert">
      <WarningCircle :size="42" weight="thin" />
      <h3>图谱暂时无法加载</h3>
      <p>{{ error }}</p>
      <button type="button" @click="$emit('retry')"><ArrowClockwise :size="18" />重新加载</button>
    </div>

    <div v-else-if="!nodes.length" class="graph-state">
      <GraphIcon :size="44" weight="thin" />
      <h3>还没有可展示的营养关系</h3>
      <p>当知识库中存在食物营养数据后，关系图会显示在这里。</p>
    </div>

    <div v-else-if="!visibleNodes.length" class="graph-state">
      <MagnifyingGlass :size="42" weight="thin" />
      <h3>没有找到匹配节点</h3>
      <p>尝试更换关键词，或重新显示已隐藏的节点类型。</p>
      <button type="button" @click="resetFilters"><ArrowClockwise :size="18" />重置筛选</button>
    </div>

    <div v-else class="graph-workspace">
      <div class="visual-panel">
        <div v-if="displayMode === 'graph'" class="graph-stage">
          <div class="zoom-controls" role="group" aria-label="图谱缩放控制">
            <button type="button" aria-label="放大图谱" :disabled="scale >= maxScale" @click="zoomBy(1.2)"><Plus :size="18" /></button>
            <button type="button" aria-label="缩小图谱" :disabled="scale <= minScale" @click="zoomBy(0.84)"><Minus :size="18" /></button>
            <button type="button" aria-label="重置图谱视图" @click="resetViewport"><ArrowsOut :size="18" /></button>
          </div>

          <svg
            class="network-canvas"
            :class="{ panning: dragState.active }"
            :viewBox="viewBox"
            role="group"
            aria-label="食物、分类和营养素关系图。可拖动平移，滚轮缩放，Tab 键选择节点。"
            @wheel.prevent="handleWheel"
            @pointerdown="startPan"
            @pointermove="movePan"
            @pointerup="endPan"
            @pointercancel="endPan"
          >
            <defs>
              <filter id="selected-glow" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            <g class="graph-edges" aria-hidden="true">
              <line
                v-for="edge in layout.edges"
                :key="edge.id"
                :x1="edge.x1"
                :y1="edge.y1"
                :x2="edge.x2"
                :y2="edge.y2"
                :class="['graph-edge', edge.relation.toLowerCase(), { muted: isEdgeMuted(edge) }]"
                :style="{ '--edge-width': `${edge.width}px` }"
              />
            </g>

            <g
              v-for="node in layout.nodes"
              :key="node.id"
              :transform="`translate(${node.x} ${node.y})`"
              :class="['graph-node', node.type, { selected: selectedId === node.id, muted: isNodeMuted(node.id) }]"
              role="button"
              tabindex="0"
              :aria-label="nodeAriaLabel(node)"
              @click.stop="selectNode(node.id)"
              @keydown.enter.prevent="selectNode(node.id)"
              @keydown.space.prevent="selectNode(node.id)"
            >
              <title>{{ nodeAriaLabel(node) }}</title>
              <rect :x="-node.width / 2" :y="-node.height / 2" :width="node.width" :height="node.height" rx="13" />
              <circle :cx="-node.width / 2 + 17" cy="0" r="4.5" />
              <text :x="-node.width / 2 + 29" y="1" dominant-baseline="middle">{{ truncateLabel(node.label) }}</text>
            </g>
          </svg>

          <div class="stage-hint"><CursorClick :size="16" /><span>拖动空白处平移 · 滚轮缩放 · 点击节点查看详情</span></div>
        </div>

        <div v-else class="food-list" aria-label="食物营养数据列表">
          <button v-for="food in visibleFoods" :key="food.id" type="button" :class="{ selected: selectedId === food.id }" @click="selectNode(food.id)">
            <header><span>{{ food.label }}</span><small>{{ food.category || '未分类' }}</small></header>
            <p v-if="food.name_en">{{ food.name_en }}</p>
            <dl>
              <div><dt>热量</dt><dd>{{ formatMetric(food.calories, 'kcal') }}</dd></div>
              <div><dt>蛋白质</dt><dd>{{ formatMetric(food.protein, 'g') }}</dd></div>
              <div><dt>碳水</dt><dd>{{ formatMetric(food.carbs, 'g') }}</dd></div>
              <div><dt>脂肪</dt><dd>{{ formatMetric(food.fat, 'g') }}</dd></div>
            </dl>
          </button>
          <div v-if="!visibleFoods.length" class="list-empty">当前筛选条件下没有食物节点。</div>
        </div>
      </div>

      <aside class="node-detail" aria-live="polite" aria-label="选中节点详情">
        <template v-if="selectedNode">
          <header>
            <span :class="['node-type', selectedNode.type]">{{ typeLabel(selectedNode.type) }}</span>
            <h3>{{ selectedNode.label }}</h3>
            <p v-if="selectedNode.name_en">{{ selectedNode.name_en }}</p>
          </header>

          <template v-if="selectedNode.type === 'food'">
            <div class="food-category"><Tag :size="17" />{{ selectedNode.category || categoryConnection || '未分类' }}</div>
            <dl class="nutrition-grid">
              <div><dt>热量</dt><dd>{{ formatMetric(selectedNode.calories, 'kcal') }}</dd></div>
              <div><dt>蛋白质</dt><dd>{{ formatMetric(selectedNode.protein, 'g') }}</dd></div>
              <div><dt>碳水化合物</dt><dd>{{ formatMetric(selectedNode.carbs, 'g') }}</dd></div>
              <div><dt>脂肪</dt><dd>{{ formatMetric(selectedNode.fat, 'g') }}</dd></div>
              <div><dt>膳食纤维</dt><dd>{{ formatMetric(selectedNode.fiber, 'g') }}</dd></div>
            </dl>
            <small class="unit-note">营养数据均按每 100g 食物计算</small>
          </template>

          <template v-else>
            <div class="connection-heading">
              <span>{{ selectedNode.type === 'category' ? '包含的食物' : '相关食物' }}</span>
              <b>{{ connectedFoods.length }}</b>
            </div>
            <div class="connection-list">
              <button v-for="item in connectedFoods.slice(0, 12)" :key="item.node.id" type="button" @click="selectNode(item.node.id)">
                <span>{{ item.node.label }}</span>
                <small v-if="item.value !== null">{{ formatMetric(item.value, selectedNode.unit || 'g') }}</small>
                <small v-else>{{ item.node.category || '查看食物' }}</small>
              </button>
              <p v-if="!connectedFoods.length">当前节点暂时没有关联食物。</p>
            </div>
          </template>
        </template>

        <div v-else class="detail-placeholder">
          <CursorClick :size="34" weight="thin" />
          <h3>选择一个节点</h3>
          <p>节点的营养数据和关联食物会显示在这里。</p>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import {
  PhArrowClockwise as ArrowClockwise, PhArrowsOut as ArrowsOut,
  PhCursorClick as CursorClick, PhGraph as GraphIcon, PhListBullets as ListBullets,
  PhMagnifyingGlass as MagnifyingGlass, PhMinus as Minus, PhPlus as Plus,
  PhTag as Tag, PhWarningCircle as WarningCircle,
} from '@phosphor-icons/vue'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

defineEmits(['retry'])

const graphWidth = 1080
const minScale = 0.65
const maxScale = 2.1
const typeOptions = [
  { id: 'food', label: '食物' },
  { id: 'category', label: '分类' },
  { id: 'nutrient', label: '营养素' },
]

const searchQuery = ref('')
const enabledTypes = ref(typeOptions.map((item) => item.id))
const displayMode = ref('graph')
const selectedId = ref('')
const scale = ref(1)
const pan = reactive({ x: 0, y: 0 })
const dragState = reactive({ active: false, pointerId: null, startX: 0, startY: 0, panX: 0, panY: 0 })

const nodeMap = computed(() => new Map(props.nodes.map((node) => [node.id, node])))
const typeCounts = computed(() => props.nodes.reduce((counts, node) => {
  if (Object.hasOwn(counts, node.type)) counts[node.type] += 1
  return counts
}, { food: 0, category: 0, nutrient: 0 }))

const matchedNodeIds = computed(() => {
  const allowed = new Set(enabledTypes.value)
  const candidates = props.nodes.filter((node) => allowed.has(node.type))
  const query = searchQuery.value.toLocaleLowerCase('zh-CN')
  if (!query) return new Set(candidates.map((node) => node.id))

  const directMatches = candidates.filter((node) => `${node.label} ${node.name_en || ''} ${node.category || ''}`.toLocaleLowerCase('zh-CN').includes(query))
  const ids = new Set(directMatches.map((node) => node.id))
  props.edges.forEach((edge) => {
    if (ids.has(edge.source) && allowed.has(nodeMap.value.get(edge.target)?.type)) ids.add(edge.target)
    if (ids.has(edge.target) && allowed.has(nodeMap.value.get(edge.source)?.type)) ids.add(edge.source)
  })
  return ids
})

const visibleNodes = computed(() => props.nodes.filter((node) => matchedNodeIds.value.has(node.id)))
const visibleNodeIds = computed(() => new Set(visibleNodes.value.map((node) => node.id)))
const visibleEdges = computed(() => props.edges.filter((edge) => visibleNodeIds.value.has(edge.source) && visibleNodeIds.value.has(edge.target)))
const visibleFoods = computed(() => visibleNodes.value.filter((node) => node.type === 'food'))

function distribute(items, x, height) {
  const gap = height / (items.length + 1)
  return items.map((node, index) => ({ ...node, x, y: gap * (index + 1) }))
}

const layout = computed(() => {
  const categories = visibleNodes.value.filter((node) => node.type === 'category').sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'))
  const foods = visibleNodes.value.filter((node) => node.type === 'food').sort((a, b) => `${a.category}${a.label}`.localeCompare(`${b.category}${b.label}`, 'zh-CN'))
  const nutrients = visibleNodes.value.filter((node) => node.type === 'nutrient')
  const foodColumns = foods.length > 22 ? 3 : foods.length > 10 ? 2 : 1
  const foodRows = Math.ceil(foods.length / foodColumns)
  const height = Math.max(620, categories.length * 76 + 120, nutrients.length * 86 + 120, foodRows * 72 + 130)
  const foodX = foodColumns === 1 ? [540] : foodColumns === 2 ? [455, 625] : [380, 540, 700]
  const positionedFoods = foods.map((node, index) => {
    const column = index % foodColumns
    const row = Math.floor(index / foodColumns)
    const rowGap = (height - 100) / Math.max(foodRows, 1)
    return { ...node, x: foodX[column], y: 50 + rowGap * (row + 0.5) }
  })
  const positioned = [
    ...distribute(categories, 130, height),
    ...positionedFoods,
    ...distribute(nutrients, 950, height),
  ].map((node) => ({
    ...node,
    width: node.type === 'food' ? 154 : node.type === 'category' ? 150 : 142,
    height: node.type === 'food' ? 50 : 44,
  }))
  const positions = new Map(positioned.map((node) => [node.id, node]))
  const edges = visibleEdges.value.map((edge) => {
    const source = positions.get(edge.source)
    const target = positions.get(edge.target)
    const nutrientWidth = edge.relation === 'HAS_NUTRIENT' && edge.value !== null
      ? Math.min(3.2, 1 + Math.abs(edge.value) / 55)
      : 1.35
    return { ...edge, x1: source.x, y1: source.y, x2: target.x, y2: target.y, width: nutrientWidth }
  })
  return { width: graphWidth, height, nodes: positioned, edges }
})

const viewBox = computed(() => {
  const width = graphWidth / scale.value
  const height = layout.value.height / scale.value
  const x = (graphWidth - width) / 2 + pan.x
  const y = (layout.value.height - height) / 2 + pan.y
  return `${x} ${y} ${width} ${height}`
})

const selectedNode = computed(() => nodeMap.value.get(selectedId.value) || null)
const selectedEdgeIds = computed(() => new Set(props.edges
  .filter((edge) => edge.source === selectedId.value || edge.target === selectedId.value)
  .map((edge) => edge.id)))
const categoryConnection = computed(() => {
  if (selectedNode.value?.type !== 'food') return ''
  const edge = props.edges.find((item) => item.source === selectedNode.value.id && item.relation === 'BELONGS_TO')
  return nodeMap.value.get(edge?.target)?.label || ''
})
const connectedFoods = computed(() => {
  if (!selectedNode.value || selectedNode.value.type === 'food') return []
  return props.edges
    .filter((edge) => edge.source === selectedNode.value.id || edge.target === selectedNode.value.id)
    .map((edge) => {
      const otherId = edge.source === selectedNode.value.id ? edge.target : edge.source
      return { node: nodeMap.value.get(otherId), value: edge.value }
    })
    .filter((item) => item.node?.type === 'food')
    .sort((a, b) => (b.value ?? -1) - (a.value ?? -1) || a.node.label.localeCompare(b.node.label, 'zh-CN'))
})

watch(visibleNodes, (nodes) => {
  if (nodes.some((node) => node.id === selectedId.value)) return
  selectedId.value = nodes.find((node) => node.type === 'food')?.id || nodes[0]?.id || ''
}, { immediate: true })

watch([searchQuery, enabledTypes], resetViewport, { deep: true })

function toggleType(type) {
  enabledTypes.value = enabledTypes.value.includes(type)
    ? enabledTypes.value.filter((item) => item !== type)
    : [...enabledTypes.value, type]
}

function resetFilters() {
  searchQuery.value = ''
  enabledTypes.value = typeOptions.map((item) => item.id)
}

function selectNode(id) {
  selectedId.value = id
}

function zoomBy(factor) {
  scale.value = Math.min(maxScale, Math.max(minScale, scale.value * factor))
}

function resetViewport() {
  scale.value = 1
  pan.x = 0
  pan.y = 0
}

function handleWheel(event) {
  zoomBy(event.deltaY > 0 ? 0.9 : 1.1)
}

function startPan(event) {
  if (event.button !== 0 || event.target.closest?.('.graph-node')) return
  dragState.active = true
  dragState.pointerId = event.pointerId
  dragState.startX = event.clientX
  dragState.startY = event.clientY
  dragState.panX = pan.x
  dragState.panY = pan.y
  event.currentTarget.setPointerCapture(event.pointerId)
}

function movePan(event) {
  if (!dragState.active || dragState.pointerId !== event.pointerId) return
  const rect = event.currentTarget.getBoundingClientRect()
  const width = graphWidth / scale.value
  const height = layout.value.height / scale.value
  pan.x = dragState.panX - (event.clientX - dragState.startX) * (width / rect.width)
  pan.y = dragState.panY - (event.clientY - dragState.startY) * (height / rect.height)
}

function endPan(event) {
  if (dragState.pointerId !== event.pointerId) return
  dragState.active = false
  dragState.pointerId = null
  if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
}

function isEdgeMuted(edge) {
  return Boolean(selectedId.value && !selectedEdgeIds.value.has(edge.id))
}

function isNodeMuted(id) {
  if (!selectedId.value || selectedId.value === id) return false
  return !props.edges.some((edge) => (
    (edge.source === selectedId.value && edge.target === id)
    || (edge.target === selectedId.value && edge.source === id)
  ))
}

function typeLabel(type) {
  return typeOptions.find((item) => item.id === type)?.label || '节点'
}

function truncateLabel(value) {
  const text = String(value || '')
  return text.length > 12 ? `${text.slice(0, 11)}…` : text
}

function formatMetric(value, unit) {
  const number = Number(value)
  return Number.isFinite(number) ? `${new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 }).format(number)} ${unit}` : '--'
}

function nodeAriaLabel(node) {
  if (node.type === 'food') return `食物：${node.label}，${node.category || '未分类'}，点击查看营养详情`
  return `${typeLabel(node.type)}：${node.label}，点击查看关联食物`
}
</script>

<style lang="scss" scoped>
.graph-shell {
  --graph-food: var(--primary);
  --graph-category: var(--accent);
  --graph-nutrient: #75b8ff;
  padding: clamp(18px, 3vw, 34px);
  overflow: hidden;
}
.graph-heading { padding-bottom: 22px; display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; border-bottom: 1px solid var(--border); }
.graph-heading p { max-width: 64ch; margin: 9px 0 0; color: var(--text-secondary); font-size: .86rem; line-height: 1.65; }
.panel-kicker { display: block; margin-bottom: 5px; color: var(--primary); font-size: .7rem; font-weight: 700; letter-spacing: .13em; }
.graph-totals { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 7px; }
.graph-totals span { min-height: 34px; padding: 0 10px; display: inline-flex; align-items: center; gap: 4px; color: var(--muted); background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 8px; font-size: .69rem; }
.graph-totals b { color: var(--text); font-size: .82rem; font-variant-numeric: tabular-nums; }
.graph-controls { padding: 16px 0; display: grid; grid-template-columns: minmax(220px, 1fr) auto auto; align-items: center; gap: 12px; }
.graph-search { min-height: 44px; padding: 0 13px; display: flex; align-items: center; gap: 9px; color: var(--muted); background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 10px; transition: border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out); }
.graph-search:focus-within { border-color: rgba(159,226,75,.58); box-shadow: 0 0 0 3px rgba(159,226,75,.08); }
.graph-search input { width: 100%; min-width: 0; color: var(--text); background: transparent; border: 0; outline: 0; font-size: .82rem; }
.graph-search input::placeholder { color: var(--muted); }
.type-filters, .view-switch { padding: 3px; display: flex; gap: 3px; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 10px; }
.type-filters button, .view-switch button { min-height: 44px; padding: 0 10px; display: inline-flex; align-items: center; justify-content: center; gap: 7px; color: var(--muted); background: transparent; border: 1px solid transparent; border-radius: 7px; font-size: .7rem; font-weight: 600; transition: color 160ms var(--ease-out), background 160ms var(--ease-out), border-color 160ms var(--ease-out); }
.type-filters button:hover, .view-switch button:hover { color: var(--text-secondary); }
.type-filters button.active, .view-switch button.active { color: var(--text); background: var(--surface); border-color: var(--border-strong); }
.type-filters i { width: 7px; height: 7px; background: currentColor; border-radius: 50%; }
.type-filters .food { color: var(--graph-food); }.type-filters .category { color: var(--graph-category); }.type-filters .nutrient { color: var(--graph-nutrient); }
.graph-workspace { display: grid; grid-template-columns: minmax(0, 1fr) 290px; gap: 14px; align-items: stretch; }
.visual-panel, .node-detail { min-width: 0; background: rgba(8,12,9,.36); border: 1px solid var(--border); border-radius: 14px; }
.graph-stage { min-height: 620px; position: relative; overflow: hidden; }
.network-canvas { width: 100%; height: 620px; display: block; cursor: grab; touch-action: none; user-select: none; background: radial-gradient(circle at center, rgba(159,226,75,.045), transparent 48%), linear-gradient(rgba(226,239,221,.025) 1px, transparent 1px), linear-gradient(90deg, rgba(226,239,221,.025) 1px, transparent 1px); background-size: auto, 38px 38px, 38px 38px; }
.network-canvas.panning { cursor: grabbing; }
.graph-edge { stroke: rgba(190,204,190,.28); stroke-width: var(--edge-width); transition: opacity 180ms var(--ease-out), stroke 180ms var(--ease-out); }
.graph-edge.has_nutrient { stroke: rgba(117,184,255,.34); }.graph-edge.belongs_to { stroke: rgba(242,117,63,.35); }
.graph-edge.muted { opacity: .11; }
.graph-node { cursor: pointer; outline: none; transition: opacity 180ms var(--ease-out); }
.graph-node rect { fill: #171d18; stroke-width: 1.4; transition: fill 160ms var(--ease-out), stroke-width 160ms var(--ease-out); }
.graph-node text { fill: var(--text); font-family: Barlow, MiSans, sans-serif; font-size: 13px; font-weight: 600; pointer-events: none; }
.graph-node.food rect { stroke: var(--graph-food); }.graph-node.food circle { fill: var(--graph-food); }
.graph-node.category rect { stroke: var(--graph-category); }.graph-node.category circle { fill: var(--graph-category); }
.graph-node.nutrient rect { stroke: var(--graph-nutrient); }.graph-node.nutrient circle { fill: var(--graph-nutrient); }
.graph-node:hover rect, .graph-node:focus-visible rect { fill: #222a23; stroke-width: 2.4; }
.graph-node:focus-visible rect { stroke-dasharray: 5 3; }
.graph-node.selected { filter: url(#selected-glow); }.graph-node.selected rect { fill: #283227; stroke-width: 2.8; }
.graph-node.muted { opacity: .28; }
.zoom-controls { position: absolute; z-index: 2; top: 12px; right: 12px; padding: 4px; display: grid; gap: 3px; background: rgba(13,16,15,.9); border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,.22); }
.zoom-controls button { width: 44px; height: 44px; display: grid; place-items: center; color: var(--text-secondary); background: transparent; border: 0; border-radius: 7px; }
.zoom-controls button:hover:not(:disabled) { color: var(--primary); background: var(--primary-soft); }.zoom-controls button:disabled { opacity: .35; }
.stage-hint { position: absolute; left: 12px; bottom: 12px; min-height: 34px; padding: 0 10px; display: flex; align-items: center; gap: 7px; color: var(--muted); background: rgba(13,16,15,.88); border: 1px solid var(--border); border-radius: 8px; font-size: .66rem; pointer-events: none; }
.node-detail { min-height: 620px; padding: 20px; }
.node-detail > header { padding-bottom: 18px; border-bottom: 1px solid var(--border); }
.node-detail h3 { margin: 9px 0 3px; font-family: "Barlow Condensed", MiSans, sans-serif; font-size: 1.75rem; line-height: 1.05; }
.node-detail header p { margin: 0; color: var(--muted); font-size: .72rem; }
.node-type { min-height: 27px; padding: 0 8px; display: inline-flex; align-items: center; color: var(--graph-food); background: rgba(159,226,75,.1); border: 1px solid rgba(159,226,75,.2); border-radius: 6px; font-size: .64rem; font-weight: 700; }
.node-type.category { color: var(--graph-category); background: rgba(242,117,63,.09); border-color: rgba(242,117,63,.2); }.node-type.nutrient { color: var(--graph-nutrient); background: rgba(117,184,255,.09); border-color: rgba(117,184,255,.2); }
.food-category { min-height: 42px; margin: 16px 0; padding: 0 11px; display: flex; align-items: center; gap: 8px; color: var(--text-secondary); background: var(--canvas-soft); border-radius: 9px; font-size: .75rem; }.food-category svg { color: var(--accent); }
.nutrition-grid { margin: 0; display: grid; gap: 7px; }
.nutrition-grid div { padding: 11px 0; display: flex; align-items: baseline; justify-content: space-between; gap: 10px; border-bottom: 1px solid var(--border); }
.nutrition-grid dt { color: var(--muted); font-size: .7rem; }.nutrition-grid dd { margin: 0; color: var(--text); font-size: .8rem; font-weight: 650; font-variant-numeric: tabular-nums; }
.unit-note { display: block; margin-top: 13px; color: var(--muted); font-size: .64rem; line-height: 1.5; }
.connection-heading { margin: 17px 0 9px; display: flex; align-items: center; justify-content: space-between; color: var(--text-secondary); font-size: .72rem; }.connection-heading b { color: var(--primary); font-size: .9rem; }
.connection-list { display: grid; gap: 6px; }.connection-list button { min-height: 44px; padding: 0 10px; display: flex; align-items: center; justify-content: space-between; gap: 9px; color: var(--text-secondary); background: var(--canvas-soft); border: 1px solid transparent; border-radius: 8px; font-size: .72rem; text-align: left; }.connection-list button:hover { color: var(--text); border-color: var(--border-strong); }.connection-list small { color: var(--muted); font-size: .62rem; white-space: nowrap; }.connection-list p { color: var(--muted); font-size: .72rem; line-height: 1.6; }
.detail-placeholder { min-height: 550px; display: grid; place-items: center; align-content: center; text-align: center; }.detail-placeholder svg { margin-bottom: 12px; color: var(--muted); }.detail-placeholder h3 { margin: 0 0 6px; font-size: 1rem; }.detail-placeholder p { max-width: 22ch; margin: 0; color: var(--muted); font-size: .72rem; }
.food-list { max-height: 620px; padding: 12px; overflow-y: auto; display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 9px; }
.food-list > button { min-width: 0; padding: 15px; color: inherit; background: rgba(255,255,255,.02); border: 1px solid var(--border); border-radius: 11px; text-align: left; transition: border-color 160ms var(--ease-out), background 160ms var(--ease-out); }
.food-list > button:hover, .food-list > button.selected { background: rgba(159,226,75,.045); border-color: rgba(159,226,75,.32); }
.food-list header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }.food-list header span { overflow: hidden; color: var(--text); font-size: .84rem; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }.food-list header small { color: var(--accent); font-size: .62rem; white-space: nowrap; }.food-list > button > p { margin: 3px 0 12px; color: var(--muted); font-size: .65rem; }
.food-list dl { margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }.food-list dl div { padding-top: 8px; border-top: 1px solid var(--border); }.food-list dt { color: var(--muted); font-size: .6rem; }.food-list dd { margin: 2px 0 0; color: var(--text-secondary); font-size: .7rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.list-empty { grid-column: 1 / -1; min-height: 260px; display: grid; place-items: center; color: var(--muted); font-size: .78rem; }
.graph-loading, .graph-state { min-height: 540px; display: grid; place-items: center; align-content: center; text-align: center; }
.graph-loading p, .graph-state p { max-width: 42ch; margin: 12px 0 0; color: var(--muted); font-size: .82rem; line-height: 1.6; }
.graph-state svg { color: var(--muted); }.graph-state h3 { margin: 14px 0 0; font-size: 1rem; }.error-state svg { color: var(--danger); }
.graph-state button { min-height: 44px; margin-top: 18px; padding: 0 14px; display: inline-flex; align-items: center; gap: 8px; color: var(--primary); background: var(--primary-soft); border: 1px solid rgba(159,226,75,.22); border-radius: 9px; }
.graph-skeleton { width: min(720px, 90%); height: 360px; position: relative; opacity: .78; }.graph-skeleton::before, .graph-skeleton::after { content: ""; position: absolute; inset: 50% 8%; height: 1px; background: var(--border-strong); transform: rotate(8deg); }.graph-skeleton::after { transform: rotate(-13deg); }
.graph-skeleton i { width: 86px; height: 36px; position: absolute; background: linear-gradient(90deg, var(--surface-soft), rgba(255,255,255,.08), var(--surface-soft)); background-size: 200% 100%; border-radius: 10px; animation: graph-shimmer 1.2s infinite linear; }.graph-skeleton i:nth-child(1) { left: 5%; top: 20%; }.graph-skeleton i:nth-child(2) { left: 8%; top: 62%; }.graph-skeleton i:nth-child(3) { left: 31%; top: 8%; }.graph-skeleton i:nth-child(4) { left: 38%; top: 32%; }.graph-skeleton i:nth-child(5) { left: 28%; top: 58%; }.graph-skeleton i:nth-child(6) { left: 43%; top: 80%; }.graph-skeleton i:nth-child(7) { right: 31%; top: 16%; }.graph-skeleton i:nth-child(8) { right: 34%; top: 48%; }.graph-skeleton i:nth-child(9) { right: 27%; top: 73%; }.graph-skeleton i:nth-child(10) { right: 5%; top: 9%; }.graph-skeleton i:nth-child(11) { right: 8%; top: 35%; }.graph-skeleton i:nth-child(12) { right: 4%; top: 64%; }.graph-skeleton i:nth-child(13) { left: 52%; top: 2%; }.graph-skeleton i:nth-child(14) { left: 54%; top: 88%; }
.sr-only { width: 1px; height: 1px; padding: 0; position: absolute; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@keyframes graph-shimmer { to { background-position: -200% 0; } }
@media (max-width: 1120px) {
  .graph-controls { grid-template-columns: 1fr auto; }.view-switch { grid-column: 1 / -1; justify-self: start; }
  .graph-workspace { grid-template-columns: 1fr; }.node-detail { min-height: auto; }.detail-placeholder { min-height: 220px; }
}
@media (max-width: 720px) {
  .graph-shell { padding: 16px; }.graph-heading { align-items: flex-start; flex-direction: column; }.graph-totals { justify-content: flex-start; }
  .graph-controls { grid-template-columns: 1fr; }.type-filters, .view-switch { width: 100%; }.type-filters button, .view-switch button { flex: 1; min-width: 0; padding: 0 6px; }
  .graph-stage, .network-canvas { min-height: 480px; height: 480px; }.node-detail { min-height: auto; }.food-list { max-height: none; grid-template-columns: 1fr; }
  .stage-hint span { display: none; }.stage-hint { width: 38px; padding: 0; justify-content: center; }
}
@media (prefers-reduced-motion: reduce) {
  .graph-search, .type-filters button, .view-switch button, .graph-edge, .graph-node, .food-list > button { transition: none; }
  .graph-skeleton i { animation: none; }
}
</style>
