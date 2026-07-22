function unwrapApiData(payload) {
  const firstLayer = payload?.data ?? payload
  return firstLayer?.data ?? firstLayer
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function normalizeBox(value) {
  if (!Array.isArray(value) || value.length < 4) return null
  const box = value.slice(0, 4).map(numberOrNull)
  return box.every((coordinate) => coordinate !== null) ? box : null
}

function text(value) {
  return typeof value === 'string' ? value : ''
}

function positiveInteger(value, fallback) {
  const number = Number(value)
  return Number.isInteger(number) && number > 0 ? number : fallback
}

export function normalizeDetectionResult(payload) {
  const data = unwrapApiData(payload) || {}
  const detections = (Array.isArray(data.detections) ? data.detections : []).map((item, index) => {
    const confidence = numberOrNull(item?.confidence)
    return {
      id: `${item?.class_name || 'object'}-${index}`,
      className: typeof item?.class_name === 'string' ? item.class_name : 'unknown',
      classNameCn: typeof item?.class_name_cn === 'string' ? item.class_name_cn : '',
      confidence,
      bbox: normalizeBox(item?.bbox),
      lowConfidence: typeof item?.low_confidence === 'boolean'
        ? item.low_confidence
        : confidence !== null && confidence < 0.25,
    }
  })

  const totalObjects = numberOrNull(data.total_objects)
  return {
    taskUuid: data.task_uuid ?? data.uuid ?? null,
    detections,
    totalObjects: totalObjects !== null ? totalObjects : detections.length,
    inferenceTime: numberOrNull(data.inference_time),
  }
}

export function normalizeDetectionScenes(payload) {
  const data = unwrapApiData(payload)
  const items = Array.isArray(data) ? data : data?.items || data?.scenes || []
  if (!Array.isArray(items)) return []
  return items.map((item, index) => ({
    id: item?.id ?? item?.scene_id ?? index + 1,
    name: item?.name_cn || item?.display_name || item?.name || `场景 ${index + 1}`,
    description: item?.description || '',
  }))
}

export function normalizeDetectionTask(source = {}) {
  const resultSource = source.result || source.result_data || source.output || source
  const normalizedResult = normalizeDetectionResult(resultSource)
  const scene = source.scene && typeof source.scene === 'object' ? source.scene : {}
  const status = text(source.status ?? source.task_status).toLowerCase() || 'unknown'

  return {
    uuid: source.task_uuid ?? source.uuid ?? source.id ?? normalizedResult.taskUuid ?? null,
    status,
    sceneName: text(source.scene_name_cn ?? source.scene_name ?? scene.name_cn ?? scene.name),
    sceneId: source.scene_id ?? scene.id ?? null,
    fileName: text(source.file_name ?? source.filename ?? source.original_filename),
    imageUrl: text(source.image_url ?? source.original_image_url ?? source.result_image_url),
    totalObjects: numberOrNull(source.total_objects ?? source.detection_count) ?? normalizedResult.totalObjects,
    inferenceTime: numberOrNull(source.inference_time) ?? normalizedResult.inferenceTime,
    detections: normalizedResult.detections,
    errorMessage: text(source.error_message ?? source.error ?? source.detail),
    createdAt: source.created_at || null,
    updatedAt: source.updated_at || null,
    completedAt: source.completed_at || source.finished_at || null,
  }
}

export function normalizeDetectionTaskList(payload) {
  const data = unwrapApiData(payload)
  const source = Array.isArray(data) ? { items: data } : data || {}
  const pagination = source.pagination && typeof source.pagination === 'object' ? source.pagination : {}
  const itemsSource = source.items || source.tasks || source.results || source.list || []
  const items = Array.isArray(itemsSource) ? itemsSource.map(normalizeDetectionTask) : []
  const total = numberOrNull(source.total ?? pagination.total)
  return {
    items,
    total: total !== null && total >= 0 ? total : items.length,
    page: positiveInteger(source.page ?? pagination.page, 1),
    pageSize: positiveInteger(source.page_size ?? pagination.page_size, 20),
  }
}

export function normalizeDetectionTaskDetail(payload) {
  return normalizeDetectionTask(unwrapApiData(payload) || {})
}
