const STATUS_ORDER = ['completed', 'processing', 'pending', 'failed']

function unwrapApiData(payload) {
  return payload?.data ?? payload
}

function metric(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

export function normalizeDetectionStats(payload) {
  const data = unwrapApiData(payload) || {}
  return {
    total: metric(data.total),
    completed: metric(data.completed),
    failed: metric(data.failed),
    pending: metric(data.pending),
    processing: metric(data.processing),
    totalObjectsDetected: metric(data.total_objects_detected),
    avgInferenceTime: metric(data.avg_inference_time),
  }
}

export function normalizeDetectionDistribution(payload) {
  const data = unwrapApiData(payload)
  if (!Array.isArray(data)) return []

  const counts = new Map()
  data.forEach((item) => {
    const status = typeof item?.status === 'string' ? item.status.trim().toLowerCase() : ''
    const count = metric(item?.count)
    if (!status || count === null || count < 0) return
    counts.set(status, (counts.get(status) || 0) + count)
  })

  return [...counts.entries()]
    .map(([status, count]) => ({ status, count }))
    .sort((a, b) => {
      const aIndex = STATUS_ORDER.indexOf(a.status)
      const bIndex = STATUS_ORDER.indexOf(b.status)
      if (aIndex === -1 && bIndex === -1) return a.status.localeCompare(b.status)
      if (aIndex === -1) return 1
      if (bIndex === -1) return -1
      return aIndex - bIndex
    })
}

export function deriveDetectionDistribution(stats = {}) {
  return STATUS_ORDER.map((status) => ({
    status,
    count: metric(stats[status]),
  })).filter((item) => item.count !== null)
}

export function deriveDetectionStats(distribution = []) {
  const byStatus = Object.fromEntries(distribution.map((item) => [item.status, metric(item.count)]))
  const counts = distribution.map((item) => metric(item.count)).filter((value) => value !== null)
  return {
    total: counts.length ? counts.reduce((sum, value) => sum + value, 0) : null,
    completed: byStatus.completed ?? null,
    failed: byStatus.failed ?? null,
    pending: byStatus.pending ?? null,
    processing: byStatus.processing ?? null,
    totalObjectsDetected: null,
    avgInferenceTime: null,
  }
}
