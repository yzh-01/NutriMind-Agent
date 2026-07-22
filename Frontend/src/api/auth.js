import request from '@/utils/request'

export const registerApi = (data) => request.post('/auth/register', data)
export const loginApi = (data) => request.post('/auth/login', data)
export const getCurrentUserApi = (config = {}) => request.get('/auth/me', config)
export const changePasswordApi = (data, config = {}) => request.post('/auth/change-password', data, config)
export const logoutApi = () => request.post('/auth/logout')
