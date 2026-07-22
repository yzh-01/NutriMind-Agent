import { describe, expect, it } from 'vitest'
import {
  deriveTrainingStats, deriveTrainingStatusDistribution, normalizeTrainingMetrics,
  normalizeTrainingModels, normalizeTrainingStatusDistribution, normalizeTrainingTaskList,
} from './trainingData'

describe('Training API data adapters', () => {
  it('normalizes a wrapped paginated task list with nested config', () => {
    const result = normalizeTrainingTaskList({ data: {
      tasks: [{ task_uuid: 't-1', status: 'RUNNING', progress: 42, config: { model_name: 'yolo11s', epochs: 100 } }],
      total: 8, page: 2, page_size: 20,
    } })

    expect(result.total).toBe(8)
    expect(result.items[0]).toMatchObject({ uuid: 't-1', status: 'running', progress: 42, modelName: 'yolo11s', epochs: 100 })
  })

  it('accepts both documented mAP50-95 field spellings', () => {
    const result = normalizeTrainingMetrics({ data: {
      epochs: [{ epoch: 1, mAP50_95: 0.24 }],
      final_metrics: { 'mAP50-95': 0.559, mAP50: 0.727 },
    } })
    expect(result.epochs[0].map50_95).toBe(0.24)
    expect(result.finalMetrics.map50_95).toBe(0.559)
  })

  it('accepts string model lists and derives visible task counts', () => {
    expect(normalizeTrainingModels({ data: ['best.pt'] })[0].name).toBe('best.pt')
    expect(deriveTrainingStats([{ status: 'running' }, { status: 'failed' }], 9)).toEqual({
      total: 9, completed: 0, failed: 1, running: 1, pending: 0, paused: 0,
    })
  })

  it('normalizes and derives training status distributions', () => {
    expect(normalizeTrainingStatusDistribution({ data: [
      { status: 'COMPLETED', count: '5' }, { status: 'failed', count: 1 },
    ] })).toEqual([
      { status: 'completed', count: 5 }, { status: 'failed', count: 1 },
    ])
    expect(deriveTrainingStatusDistribution({ running: 2, completed: 4 }))
      .toContainEqual({ status: 'running', count: 2 })
  })
})
