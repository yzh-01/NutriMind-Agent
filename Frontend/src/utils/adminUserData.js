function unwrapApiData(payload) {
  return payload?.data ?? payload
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

function normalizeRoles(roles) {
  if (!Array.isArray(roles)) return []
  return [...new Set(roles.filter((role) => typeof role === 'string').map((role) => role.trim()).filter(Boolean))]
}

export function normalizeAdminUser(source = {}) {
  return {
    id: source.id ?? null,
    username: typeof source.username === 'string' ? source.username : '',
    email: typeof source.email === 'string' ? source.email : '',
    phone: typeof source.phone === 'string' ? source.phone : '',
    avatar: typeof source.avatar === 'string' ? source.avatar : '',
    isActive: typeof source.is_active === 'boolean' ? source.is_active : null,
    isSuperuser: typeof source.is_superuser === 'boolean' ? source.is_superuser : null,
    roles: normalizeRoles(source.roles),
    lastLoginAt: source.last_login_at || null,
    createdAt: source.created_at || null,
    updatedAt: source.updated_at || null,
    totalDetectionTasks: numberOrNull(source.total_detection_tasks),
    totalTrainingTasks: numberOrNull(source.total_training_tasks),
  }
}

export function normalizeAdminUserList(payload) {
  const data = unwrapApiData(payload) || {}
  const items = Array.isArray(data.items) ? data.items.map(normalizeAdminUser) : []
  const total = numberOrNull(data.total)

  return {
    items,
    total: total !== null && total >= 0 ? total : items.length,
    page: positiveInteger(data.page, 1),
    pageSize: positiveInteger(data.page_size, 20),
  }
}

export function normalizeAdminUserDetail(payload) {
  return normalizeAdminUser(unwrapApiData(payload) || {})
}

export function parseRoleNames(value) {
  if (typeof value !== 'string') return []
  return [...new Set(value.split(/[,，\n]+/).map((role) => role.trim()).filter(Boolean))]
}
