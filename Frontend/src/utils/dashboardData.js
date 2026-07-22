function unwrapApiData(payload) {
  return payload?.data ?? payload
}

function metric(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function pickMetrics(source = {}, fields = []) {
  return Object.fromEntries(fields.map((field) => [field, metric(source[field])]))
}

export function normalizeDashboardStats(payload) {
  const data = unwrapApiData(payload) || {}

  return {
    overview: pickMetrics(data.overview, [
      'total_users', 'active_users', 'total_detection_scenes',
      'total_detection_tasks', 'total_training_tasks', 'total_food_items',
    ]),
    detection: pickMetrics(data.detection, [
      'total', 'completed', 'failed', 'pending', 'processing',
      'total_objects_detected', 'avg_inference_time',
    ]),
    training: pickMetrics(data.training, [
      'total', 'completed', 'failed', 'running', 'pending', 'paused',
    ]),
    users: pickMetrics(data.users, ['total', 'active', 'superusers', 'new_today']),
  }
}
