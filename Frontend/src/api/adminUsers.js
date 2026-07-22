import request from '@/utils/request'

const userPath = (userId, action = '') => {
  const suffix = action ? `/${action}` : ''
  return `/dashboard/users/${encodeURIComponent(userId)}${suffix}`
}

export const getAdminUsersApi = (params) => request.get('/dashboard/users/list', {
  params,
  silent: true,
})

export const getAdminUserDetailApi = (userId) => request.get(userPath(userId), {
  silent: true,
})

export const updateAdminUserStatusApi = (userId, data) => request.put(
  userPath(userId, 'status'),
  data,
  { silent: true },
)

export const updateAdminUserRolesApi = (userId, data) => request.put(
  userPath(userId, 'roles'),
  data,
  { silent: true },
)

export const updateAdminUserSuperuserApi = (userId, data) => request.put(
  userPath(userId, 'superuser'),
  data,
  { silent: true },
)
