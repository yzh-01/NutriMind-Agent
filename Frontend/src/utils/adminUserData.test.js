import { describe, expect, it } from 'vitest'
import {
  normalizeAdminUserDetail,
  normalizeAdminUserList,
  parseRoleNames,
} from './adminUserData'

describe('Admin user API data adapter', () => {
  it('normalizes a wrapped paginated user list', () => {
    const result = normalizeAdminUserList({
      code: 200,
      data: {
        items: [{
          id: 7,
          username: 'runner',
          is_active: true,
          is_superuser: false,
          roles: ['user', 'user', ' nutrition '],
        }],
        total: 35,
        page: 2,
        page_size: 20,
      },
    })

    expect(result.total).toBe(35)
    expect(result.page).toBe(2)
    expect(result.items[0]).toMatchObject({
      id: 7,
      username: 'runner',
      isActive: true,
      isSuperuser: false,
      roles: ['user', 'nutrition'],
    })
  })

  it('keeps missing task totals distinct from a real zero', () => {
    const detail = normalizeAdminUserDetail({
      data: { id: 8, total_detection_tasks: 0 },
    })

    expect(detail.totalDetectionTasks).toBe(0)
    expect(detail.totalTrainingTasks).toBeNull()
  })

  it('parses comma-separated role names without duplicates', () => {
    expect(parseRoleNames('admin, editor，admin\nreviewer')).toEqual([
      'admin', 'editor', 'reviewer',
    ])
  })
})
