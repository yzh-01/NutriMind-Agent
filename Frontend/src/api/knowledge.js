import request from '@/utils/request'

const KNOWLEDGE_ASK_TIMEOUT = 120000

export function uploadDocumentApi(file) {
  const data = new FormData()
  data.append('file', file)
  return request.post('/knowledge/upload', data)
}

export const searchKnowledgeApi = (params) => request.get('/knowledge/search', { params })
export const askKnowledgeApi = (params, config = {}) => request.get('/knowledge/ask', {
  params,
  timeout: KNOWLEDGE_ASK_TIMEOUT,
  silent: true,
  ...config,
})
export const deleteDocumentApi = (source) => request.delete('/knowledge/', { params: { source } })
export const getKnowledgeStatsApi = () => request.get('/knowledge/stats')
export const getKnowledgeGraphApi = (config = {}) => request.get('/knowledge/graph', config)
