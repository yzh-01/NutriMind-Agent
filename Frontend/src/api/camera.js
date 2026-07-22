import request from '@/utils/request'

export function captureImageApi(file) {
  const data = new FormData()
  data.append('file', file)
  return request.post('/camera/capture', data, { silent: true })
}

export const getCameraHistoryApi = (params) => request.get('/camera/list', { params, silent: true })

export const getCameraImageApi = (imageId) => request.get(
  `/camera/view/${encodeURIComponent(imageId)}`,
  { responseType: 'blob', silent: true },
)

export const deleteCameraImageApi = (imageId) => request.delete(
  `/camera/${encodeURIComponent(imageId)}`,
)
