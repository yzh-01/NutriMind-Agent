export function unwrapApiData(payload) {
  return payload?.data ?? payload
}

export function normalizeKnowledgeResult(item = {}) {
  const metadata = item.metadata && typeof item.metadata === 'object' ? item.metadata : {}
  const source = metadata.source || item.source || ''

  return {
    ...item,
    metadata,
    source,
    fileName: metadata.file_name || item.fileName || source,
    type: metadata.type || item.type || '',
  }
}

export function normalizeKnowledgeSearch(payload) {
  const data = unwrapApiData(payload) || {}
  const results = Array.isArray(data.results) ? data.results.map(normalizeKnowledgeResult) : []
  return { ...data, results }
}

export function normalizeKnowledgeStats(payload) {
  const data = unwrapApiData(payload) || {}
  const sources = Array.isArray(data.sources) ? data.sources : []
  const legacyTotal = Number(data.total_documents)
  const chunks = Number(data.total_chunks)

  return {
    ...data,
    sources,
    total_documents: Number.isFinite(legacyTotal) ? legacyTotal : sources.length,
    total_chunks: Number.isFinite(chunks) ? chunks : 0,
  }
}

const graphNodeTypes = new Set(['food', 'category', 'nutrient'])

function finiteNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function normalizeGraphNode(item = {}, index = 0) {
  const type = graphNodeTypes.has(item.type) ? item.type : 'food'
  return {
    ...item,
    id: String(item.id || `${type}-${index}`),
    label: String(item.label || item.food_name_cn || item.name_en || '未命名节点'),
    type,
    group: graphNodeTypes.has(item.group) ? item.group : type,
    name_en: typeof item.name_en === 'string' ? item.name_en : '',
    category: typeof item.category === 'string' ? item.category : '',
    unit: typeof item.unit === 'string' ? item.unit : '',
    calories: finiteNumber(item.calories),
    protein: finiteNumber(item.protein),
    fat: finiteNumber(item.fat),
    carbs: finiteNumber(item.carbs),
    fiber: finiteNumber(item.fiber),
  }
}

function normalizeGraphEdge(item = {}, index = 0) {
  const source = String(item.source || '')
  const target = String(item.target || '')
  const value = finiteNumber(item.value)
  return {
    ...item,
    id: String(item.id || `${source}-${target}-${index}`),
    source,
    target,
    relation: item.relation === 'HAS_NUTRIENT' ? 'HAS_NUTRIENT' : 'BELONGS_TO',
    value,
  }
}

export function normalizeKnowledgeGraph(payload) {
  const data = unwrapApiData(payload) || {}
  const nodes = Array.isArray(data.nodes) ? data.nodes.map(normalizeGraphNode) : []
  const nodeIds = new Set(nodes.map((node) => node.id))
  const edges = Array.isArray(data.edges)
    ? data.edges
      .map(normalizeGraphEdge)
      .filter((edge) => edge.source && edge.target && nodeIds.has(edge.source) && nodeIds.has(edge.target))
    : []

  return { nodes, edges }
}

function normalizeAnswerSource(item = {}, index = 0) {
  const score = item.score === null || item.score === undefined ? null : Number(item.score)
  return {
    id: item.id || `source-${index}`,
    type: item.type === 'web' ? 'web' : 'knowledge',
    title: item.title || item.url || '未命名来源',
    url: typeof item.url === 'string' ? item.url : '',
    score: Number.isFinite(score) ? score : null,
    excerpt: typeof item.excerpt === 'string' ? item.excerpt : '',
  }
}

export function normalizeKnowledgeAnswer(payload) {
  const data = unwrapApiData(payload) || {}
  return {
    query: typeof data.query === 'string' ? data.query : '',
    answer: typeof data.answer === 'string' ? data.answer : '',
    sources: Array.isArray(data.sources) ? data.sources.map(normalizeAnswerSource) : [],
    localResults: Array.isArray(data.local_results) ? data.local_results : [],
    webResults: Array.isArray(data.web_results) ? data.web_results : [],
    usedWebFallback: Boolean(data.used_web_fallback),
    crossVerified: Boolean(data.cross_verified),
  }
}
