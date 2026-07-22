import { describe, expect, it } from 'vitest'
import { getDefaultRouteForUser, isAdminUser, isUserRoleResolved } from './userAccess'

describe('role-based frontend access', () => {
  it('routes superusers to the administrator dashboard', () => {
    const user = { is_superuser: true, roles: [] }
    expect(isAdminUser(user)).toBe(true)
    expect(getDefaultRouteForUser(user)).toBe('/admin/dashboard')
  })

  it('routes regular users to the AI coach workspace', () => {
    const user = { is_superuser: false, roles: [] }
    expect(isAdminUser(user)).toBe(false)
    expect(isUserRoleResolved(user)).toBe(true)
    expect(getDefaultRouteForUser(user)).toBe('/app/coach')
  })

  it('treats cached login payloads without is_superuser as unresolved', () => {
    expect(isUserRoleResolved({ roles: [] })).toBe(false)
  })
})
