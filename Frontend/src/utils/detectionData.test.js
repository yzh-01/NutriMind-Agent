import { describe, expect, it } from 'vitest'
import {
  deriveDetectionDistribution,
  deriveDetectionStats,
  normalizeDetectionDistribution,
  normalizeDetectionStats,
} from './detectionData'

describe('Detection dashboard API data adapter', () => {
  it('normalizes wrapped detection metrics and keeps missing values distinct from zero', () => {
    const result = normalizeDetectionStats({
      code: 200,
      data: {
        total: 12,
        completed: 0,
        total_objects_detected: 85,
        avg_inference_time: null,
      },
    })

    expect(result.total).toBe(12)
    expect(result.completed).toBe(0)
    expect(result.totalObjectsDetected).toBe(85)
    expect(result.avgInferenceTime).toBeNull()
    expect(result.failed).toBeNull()
  })

  it('aggregates duplicate statuses, ignores invalid entries, and keeps unknown statuses', () => {
    const result = normalizeDetectionDistribution({
      data: [
        { status: 'failed', count: 2 },
        { status: 'completed', count: 9 },
        { status: 'FAILED', count: 1 },
        { status: 'cancelled', count: 3 },
        { status: '', count: 10 },
        { status: 'pending', count: -1 },
      ],
    })

    expect(result).toEqual([
      { status: 'completed', count: 9 },
      { status: 'failed', count: 3 },
      { status: 'cancelled', count: 3 },
    ])
  })

  it('derives a usable fallback in either direction', () => {
    const distribution = deriveDetectionDistribution({
      completed: 7,
      processing: 1,
      pending: 0,
      failed: 2,
    })
    expect(deriveDetectionStats(distribution)).toMatchObject({
      total: 10,
      completed: 7,
      processing: 1,
      pending: 0,
      failed: 2,
    })
  })
})
