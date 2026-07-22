const ADMIN_ROLES = new Set(['admin', 'administrator', 'superuser', '管理员'])

export function isAdminUser(user) {
  if (user?.is_superuser) return true
  const roles = Array.isArray(user?.roles) ? user.roles : []
  return roles.some((role) => ADMIN_ROLES.has(String(role).toLowerCase()))
}

export function isUserRoleResolved(user) {
  return Boolean(user?.is_demo) || typeof user?.is_superuser === 'boolean'
}

export function getDefaultRouteForUser(user) {
  return isAdminUser(user) ? '/admin/dashboard' : '/app/coach'
}
