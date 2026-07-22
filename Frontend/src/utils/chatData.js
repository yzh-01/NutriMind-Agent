function unwrapChatData(payload) {
  const firstLayer = payload?.data ?? payload
  if (firstLayer?.response !== undefined || firstLayer?.session_id !== undefined) return firstLayer
  return firstLayer?.data ?? firstLayer
}

function text(value) {
  return typeof value === 'string' ? value : ''
}

function normalizeToolCalls(value) {
  if (!Array.isArray(value)) return []
  return value.map((item, index) => ({
    id: `${text(item?.name || item?.tool) || 'tool'}-${index}`,
    name: text(item?.name || item?.tool) || 'unknown_tool',
    args: item?.args && typeof item.args === 'object' ? item.args : {},
  }))
}

function normalizeChatMessage(item = {}, index = 0) {
  const role = item?.role === 'user' ? 'user' : 'assistant'
  return {
    id: item?.id ?? `message-${index}`,
    role,
    content: text(item?.content || item?.message),
    toolCalls: normalizeToolCalls(item?.tool_calls || item?.toolCalls),
    createdAt: text(item?.created_at || item?.createdAt),
  }
}

function normalizeDetections(value) {
  if (!Array.isArray(value)) return []
  return value.map((item, index) => ({
    id: `${text(item?.class_name) || 'object'}-${index}`,
    className: text(item?.class_name) || 'unknown',
    classNameCn: text(item?.class_name_cn),
    confidence: Number.isFinite(Number(item?.confidence)) ? Number(item.confidence) : null,
    bbox: Array.isArray(item?.bbox) ? item.bbox.slice(0, 4) : null,
  }))
}

export function normalizeChatResponse(payload, fallbackSessionId = '') {
  const data = unwrapChatData(payload) || {}
  return {
    sessionId: text(data.session_id) || fallbackSessionId,
    response: text(data.response || data.answer || data.content || data.message)
      || '智能体已完成处理，但没有返回可显示的文字。',
    imageId: text(data.image_id),
    detectionMode: text(data.detection_mode),
    detections: normalizeDetections(data.detections),
    toolCalls: normalizeToolCalls(data.tool_calls),
    analysisResult: data.analysis_result ?? null,
  }
}

export function normalizeChatSession(payload = {}) {
  const data = payload?.data ?? payload
  const messages = Array.isArray(data?.messages)
    ? data.messages.map(normalizeChatMessage)
    : []
  return {
    sessionId: text(data?.session_id || data?.sessionId),
    title: text(data?.title) || '新对话',
    createdAt: text(data?.created_at || data?.createdAt),
    updatedAt: text(data?.updated_at || data?.updatedAt),
    messages,
  }
}

export function normalizeChatSessions(payload) {
  const data = payload?.data ?? payload
  const items = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
  return items.map(normalizeChatSession).filter((item) => item.sessionId)
}
