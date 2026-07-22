import request from '@/utils/request'

const taskPath = (taskUuid, action = '') => {
  const suffix = action ? `/${action}` : ''
  return `/training/tasks/${encodeURIComponent(taskUuid)}${suffix}`
}

export const getTrainingTasksApi = (params, config = {}) => request.get('/training/tasks', {
  ...config,
  params,
})

export const getTrainingTaskApi = (taskUuid, config = {}) => request.get(taskPath(taskUuid), config)
export const getTrainingMetricsApi = (taskUuid, config = {}) => request.get(taskPath(taskUuid, 'metrics'), config)
export const createTrainingTaskApi = (data) => request.post('/training/tasks', data, { silent: true })
export const startTrainingTaskApi = (taskUuid) => request.post(taskPath(taskUuid, 'start'), undefined, { silent: true })
export const pauseTrainingTaskApi = (taskUuid) => request.post(taskPath(taskUuid, 'pause'), undefined, { silent: true })
export const getTrainingModelsApi = (config = {}) => request.get('/training/models', config)
export const deleteTrainingModelApi = (name) => request.delete(
  `/training/models/${encodeURIComponent(name)}`,
  { silent: true },
)
