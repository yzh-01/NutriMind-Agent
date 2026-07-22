// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const authMocks = vi.hoisted(() => ({
  getCurrentUserApi: vi.fn(), loginApi: vi.fn(), logoutApi: vi.fn(),
}))

vi.mock('@/api/auth', () => ({
  getCurrentUserApi: authMocks.getCurrentUserApi,
  loginApi: authMocks.loginApi,
  logoutApi: authMocks.logoutApi,
}))

import { useUserStore } from './user'

describe('User session restoration', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('restores a cookie-backed session through auth/me', async () => {
    authMocks.getCurrentUserApi.mockResolvedValue({ id: 18, username: 'zhangsan', roles: [] })
    const store = useUserStore()

    await store.restoreSession()

    expect(store.isLoggedIn).toBe(true)
    expect(store.sessionResolved).toBe(true)
    expect(JSON.parse(localStorage.getItem('nutrimind_user'))).toMatchObject({ id: 18 })
  })

  it('clears stale local identity when auth/me rejects', async () => {
    localStorage.setItem('nutrimind_user', JSON.stringify({ id: 7, username: 'stale' }))
    setActivePinia(createPinia())
    authMocks.getCurrentUserApi.mockRejectedValue(new Error('401'))
    const store = useUserStore()

    await store.restoreSession()

    expect(store.isLoggedIn).toBe(false)
    expect(store.sessionResolved).toBe(true)
    expect(localStorage.getItem('nutrimind_user')).toBeNull()
  })

  it('updates the shared avatar URL and refreshes an unchanged backend path', () => {
    const store = useUserStore()
    store.saveUser({ id: 18, username: 'zhangsan', avatar: '/uploads/avatar.jpg' })

    const firstUrl = store.avatarUrl
    store.setAvatar('/uploads/avatar.jpg')

    expect(store.avatarUrl).toContain('/uploads/avatar.jpg?avatar_v=')
    expect(store.avatarUrl).not.toBe(firstUrl)
    expect(JSON.parse(localStorage.getItem('nutrimind_user')).avatar).toBe('/uploads/avatar.jpg')

    store.setAvatar(null)
    expect(store.avatarUrl).toBe('')
  })
})
