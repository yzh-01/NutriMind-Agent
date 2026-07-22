import { describe, expect, it } from 'vitest'
import {
  normalizeDetectionResult, normalizeDetectionScenes,
  normalizeDetectionTaskDetail, normalizeDetectionTaskList,
} from './detectionTaskData'

describe('Detection task API data adapter', () => {
  it('normalizes a wrapped detection response and valid boxes', () => {
    const result = normalizeDetectionResult({
      data: {
        task_uuid: 'detect-1',
        detections: [{ class_name: 'rice', confidence: 0.96, bbox: [20, 80, 300, 400] }],
        inference_time: 0.32,
      },
    })

    expect(result.taskUuid).toBe('detect-1')
    expect(result.totalObjects).toBe(1)
    expect(result.inferenceTime).toBe(0.32)
    expect(result.detections[0]).toMatchObject({
      className: 'rice', confidence: 0.96, bbox: [20, 80, 300, 400], lowConfidence: false,
    })
  })

  it('keeps an invalid box out of the overlay while retaining the result row', () => {
    const result = normalizeDetectionResult({ detections: [{ class_name: 'unknown', bbox: [1, 'bad'] }] })
    expect(result.detections[0].bbox).toBeNull()
  })

  it('accepts common scene-list response shapes', () => {
    expect(normalizeDetectionScenes({ data: { scenes: [{ scene_id: 8, name: 'food' }] } })).toEqual([
      { id: 8, name: 'food', description: '' },
    ])
  })

  it('normalizes paginated detection history and common task aliases', () => {
    const result = normalizeDetectionTaskList({
      data: {
        tasks: [{
          uuid: 'detect-2', task_status: 'COMPLETED', scene_name: 'food',
          detection_count: 2, result: { detections: [{ class_name: 'rice', confidence: 0.9 }] },
        }],
        pagination: { total: 31, page: 2, page_size: 20 },
      },
    })

    expect(result).toMatchObject({ total: 31, page: 2, pageSize: 20 })
    expect(result.items[0]).toMatchObject({
      uuid: 'detect-2', status: 'completed', sceneName: 'food', totalObjects: 2,
    })
    expect(result.items[0].detections).toHaveLength(1)
  })

  it('normalizes a detail response with image, timing and error information', () => {
    expect(normalizeDetectionTaskDetail({ data: {
      task_uuid: 'detect-3', status: 'failed', image_url: '/image/3',
      inference_time: '0.42', error_message: 'model unavailable',
    } })).toMatchObject({
      uuid: 'detect-3', status: 'failed', imageUrl: '/image/3',
      inferenceTime: 0.42, errorMessage: 'model unavailable',
    })
  })
})
