import { describe, expect, it } from 'vitest'
import { normalizeDashboardStats } from './dashboardData'

describe('Dashboard API data adapter', () => {
  it('unwraps and normalizes the complete dashboard response', () => {
    const result = normalizeDashboardStats({
      code: 200,
      data: {
        overview: { total_users: 15, total_detection_tasks: 120 },
        detection: { total: 120, avg_inference_time: 0.3245 },
        training: { total: 8, running: 1 },
        users: { total: 15, new_today: 1 },
      },
    })

    expect(result.overview.total_users).toBe(15)
    expect(result.overview.total_detection_tasks).toBe(120)
    expect(result.detection.avg_inference_time).toBe(0.3245)
    expect(result.training.running).toBe(1)
    expect(result.users.new_today).toBe(1)
  })

  it('keeps missing or invalid metrics distinguishable from a real zero', () => {
    const result = normalizeDashboardStats({ data: { detection: { total: 0, failed: 'invalid' } } })

    expect(result.detection.total).toBe(0)
    expect(result.detection.failed).toBeNull()
    expect(result.overview.total_users).toBeNull()
  })
})
