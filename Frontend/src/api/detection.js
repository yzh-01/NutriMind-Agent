import request from '@/utils/request'

export function detectImageApi(file, options = {}) {
  const data = new FormData()
  data.append('file', file)
  if (options.sceneId !== null && options.sceneId !== undefined && options.sceneId !== '') {
    data.append('scene_id', String(options.sceneId))
  }
  if (options.confThreshold !== null && options.confThreshold !== undefined) {
    data.append('conf_threshold', String(options.confThreshold))
  }
  if (options.iouThreshold !== null && options.iouThreshold !== undefined) {
    data.append('iou_threshold', String(options.iouThreshold))
  }
  return request.post('/detection/detect', data, { silent: true })
}

export const getDetectionScenesApi = (config = {}) => request.get('/detection/scenes', config)

export const getDetectionTasksApi = (params, config = {}) => request.get('/detection/tasks', {
  ...config,
  params,
})

export const getDetectionTaskDetailApi = (taskUuid, config = {}) => request.get(
  `/detection/tasks/${encodeURIComponent(taskUuid)}`,
  config,
)
