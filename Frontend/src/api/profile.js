import request from '@/utils/request'

export const getProfileApi = (config = {}) => request.get('/users/me/profile', config)

export const updateProfileApi = (data, config = {}) => request.patch('/users/me/profile', data, config)

export function uploadAvatarApi(file, config = {}) {
  const data = new FormData()
  data.append('file', file)
  return request.post('/users/me/avatar', data, config)
}

export const deleteAvatarApi = (config = {}) => request.delete('/users/me/avatar', config)
