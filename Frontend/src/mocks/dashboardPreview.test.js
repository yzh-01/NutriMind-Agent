import { describe, expect, it } from 'vitest'
import { dashboardPreviewStats, emptyDashboardPreviewStats } from './dashboardPreview'
import { normalizeDashboardStats } from '@/utils/dashboardData'

describe('administrator dashboard preview fixtures', () => {
  it('keeps preview status totals internally consistent', () => {
    const result = normalizeDashboardStats(dashboardPreviewStats)

    expect(result.detection.completed + result.detection.failed + result.detection.pending + result.detection.processing)
      .toBe(result.detection.total)
    expect(result.training.completed + result.training.failed + result.training.running + result.training.pending + result.training.paused)
      .toBe(result.training.total)
    expect(result.users.total).toBe(result.overview.total_users)
  })

  it('provides a complete zero-value empty state', () => {
    const result = normalizeDashboardStats(emptyDashboardPreviewStats)

    expect(Object.values(result.overview).every((value) => value === 0)).toBe(true)
    expect(result.detection.total).toBe(0)
    expect(result.detection.avg_inference_time).toBeNull()
  })
})
