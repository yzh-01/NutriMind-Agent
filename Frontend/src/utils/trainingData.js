function unwrapApiData(payload) {
  const firstLayer = payload?.data ?? payload
  return firstLayer?.data ?? firstLayer
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function positiveInteger(value, fallback) {
  const number = Number(value)
  return Number.isInteger(number) && number > 0 ? number : fallback
}

function text(value) {
  return typeof value === 'string' ? value : ''
}

export function normalizeTrainingTask(source = {}) {
  const config = source.config || source.parameters || {}
  const progress = numberOrNull(source.progress ?? source.progress_percent)
  return {
    uuid: source.task_uuid ?? source.uuid ?? source.id ?? null,
    modelName: text(source.model_name ?? config.model_name),
    status: text(source.status).toLowerCase() || 'unknown',
    progress: progress === null ? null : Math.min(100, Math.max(0, progress)),
    dataYaml: text(source.data_yaml ?? config.data_yaml),
    epochs: numberOrNull(source.epochs ?? source.total_epochs ?? config.epochs),
    currentEpoch: numberOrNull(source.current_epoch ?? source.epoch),
    imgSize: numberOrNull(source.img_size ?? source.image_size ?? config.img_size),
    batchSize: numberOrNull(source.batch_size ?? source.batch ?? config.batch_size),
    errorMessage: text(source.error_message ?? source.error),
    createdAt: source.created_at || null,
    updatedAt: source.updated_at || null,
    startedAt: source.started_at || null,
    completedAt: source.completed_at || source.finished_at || null,
  }
}

export function normalizeTrainingTaskList(payload) {
  const data = unwrapApiData(payload)
  const source = Array.isArray(data) ? { items: data } : data || {}
  const itemsSource = source.items || source.tasks || []
  const items = Array.isArray(itemsSource) ? itemsSource.map(normalizeTrainingTask) : []
  const total = numberOrNull(source.total)
  return {
    items,
    total: total !== null && total >= 0 ? total : items.length,
    page: positiveInteger(source.page, 1),
    pageSize: positiveInteger(source.page_size, 20),
  }
}

export function normalizeTrainingTaskDetail(payload) {
  return normalizeTrainingTask(unwrapApiData(payload) || {})
}

function metric(source, ...keys) {
  for (const key of keys) {
    const value = numberOrNull(source?.[key])
    if (value !== null) return value
  }
  return null
}

export function normalizeTrainingMetrics(payload) {
  const data = unwrapApiData(payload) || {}
  const epochs = (Array.isArray(data.epochs) ? data.epochs : []).map((item, index) => ({
    epoch: numberOrNull(item?.epoch) ?? index + 1,
    trainBoxLoss: metric(item, 'train_box_loss'),
    trainClsLoss: metric(item, 'train_cls_loss'),
    valBoxLoss: metric(item, 'val_box_loss'),
    valClsLoss: metric(item, 'val_cls_loss'),
    map50: metric(item, 'mAP50', 'map50'),
    map50_95: metric(item, 'mAP50_95', 'mAP50-95', 'map50_95'),
    precision: metric(item, 'precision'),
    recall: metric(item, 'recall'),
  }))
  const final = data.final_metrics || {}
  return {
    taskUuid: data.task_uuid ?? null,
    modelName: text(data.model_name),
    epochs,
    finalMetrics: {
      map50: metric(final, 'mAP50', 'map50'),
      map50_95: metric(final, 'mAP50_95', 'mAP50-95', 'map50_95'),
      precision: metric(final, 'precision'),
      recall: metric(final, 'recall'),
    },
  }
}

export function normalizeTrainingModels(payload) {
  const data = unwrapApiData(payload)
  const items = Array.isArray(data) ? data : data?.items || data?.models || []
  if (!Array.isArray(items)) return []
  return items.map((item) => typeof item === 'string' ? {
    name: item, path: '', size: null, createdAt: null,
  } : {
    name: text(item?.name ?? item?.model_name ?? item?.filename),
    path: text(item?.path),
    size: numberOrNull(item?.size ?? item?.size_bytes),
    createdAt: item?.created_at || item?.updated_at || null,
  }).filter((item) => item.name)
}

export function normalizeTrainingStats(payload) {
  const data = unwrapApiData(payload) || {}
  return Object.fromEntries(['total', 'completed', 'failed', 'running', 'pending', 'paused']
    .map((key) => [key, numberOrNull(data[key])]))
}

export function deriveTrainingStats(tasks = [], total = null) {
  const counts = { completed: 0, failed: 0, running: 0, pending: 0, paused: 0 }
  tasks.forEach((task) => {
    if (Object.hasOwn(counts, task.status)) counts[task.status] += 1
  })
  return { total: numberOrNull(total) ?? tasks.length, ...counts }
}

export function normalizeTrainingStatusDistribution(payload) {
  const data = unwrapApiData(payload)
  const items = Array.isArray(data) ? data : data?.items || data?.distribution || []
  if (!Array.isArray(items)) return []
  return items.map((item) => ({
    status: text(item?.status).toLowerCase() || 'unknown',
    count: numberOrNull(item?.count) ?? 0,
  })).filter((item) => item.count >= 0)
}

export function deriveTrainingStatusDistribution(stats = {}) {
  return ['running', 'pending', 'paused', 'completed', 'failed'].map((status) => ({
    status,
    count: numberOrNull(stats[status]) ?? 0,
  }))
}
