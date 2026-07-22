export function unwrapCameraData(payload) {
  return payload?.data ?? payload
}

export function normalizeCameraItem(item = {}) {
  const id = String(item.id || item.image_id || item.filename || '')
  const storedName = item.filename || id

  return {
    ...item,
    id,
    storedName,
    displayName: item.original_name || item.file_name || storedName || '未命名图片',
    size: Number.isFinite(Number(item.size)) ? Number(item.size) : 0,
    createdAt: item.created_at || '',
    previewUrl: '',
    previewLoading: true,
    previewError: false,
  }
}

export function normalizeCameraHistory(payload) {
  const data = unwrapCameraData(payload) || {}
  const items = Array.isArray(data.items) ? data.items.map(normalizeCameraItem) : []
  const total = Number(data.total)
  const page = Number(data.page)
  const pageSize = Number(data.page_size)

  return {
    items,
    total: Number.isFinite(total) ? total : items.length,
    page: Number.isFinite(page) && page > 0 ? page : 1,
    pageSize: Number.isFinite(pageSize) && pageSize > 0 ? pageSize : 20,
  }
}
