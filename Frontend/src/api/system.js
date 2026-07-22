import request from '@/utils/request'

export const getHealthApi = () => request.get('/health', { silent: true })
