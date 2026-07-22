import { describe, expect, it } from 'vitest'
import { normalizeChatResponse, normalizeChatSession, normalizeChatSessions } from './chatData'

describe('normalizeChatResponse', () => {
  it('normalizes the documented top-level text response', () => {
    const result = normalizeChatResponse({
      session_id: 'meal-001',
      response: '智能体回复',
      tool_calls: [{ name: 'calculate_total_nutrition', args: { count: 2 } }],
      analysis_result: null,
    })

    expect(result.sessionId).toBe('meal-001')
    expect(result.response).toBe('智能体回复')
    expect(result.toolCalls[0]).toMatchObject({ name: 'calculate_total_nutrition', args: { count: 2 } })
  })

  it('accepts a wrapped image response and missing optional arrays', () => {
    const result = normalizeChatResponse({ data: { data: {
      session_id: 'image-1',
      image_id: 'safe-image-id',
      detection_mode: 'yolo',
      response: '识别完成',
      detections: [{ class_name: 'rice', class_name_cn: '米饭', confidence: 0.96, bbox: [1, 2, 3, 4] }],
    } } })

    expect(result.imageId).toBe('safe-image-id')
    expect(result.detections[0]).toMatchObject({ className: 'rice', classNameCn: '米饭', confidence: 0.96 })
    expect(result.toolCalls).toEqual([])
  })

  it('uses safe fallbacks when optional response fields are absent', () => {
    const result = normalizeChatResponse({}, 'local-session')
    expect(result.sessionId).toBe('local-session')
    expect(result.response).toContain('没有返回可显示的文字')
    expect(result.detections).toEqual([])
  })
})

describe('persistent chat session adapters', () => {
  it('normalizes history messages and tool calls', () => {
    const result = normalizeChatSession({
      session_id: 'meal-1', title: '训练晚餐', created_at: '2026-07-20T10:00:00',
      updated_at: '2026-07-20T10:05:00',
      messages: [
        { id: 1, role: 'user', content: '怎么吃？', image_id: 'safe-image', image_url: '/api/chat/images/safe-image', tool_calls: [], created_at: '2026-07-20T10:01:00' },
        { id: 2, role: 'assistant', content: '优先蛋白质', tool_calls: [{ name: 'search_nutrition_knowledge', args: {} }] },
      ],
    })

    expect(result).toMatchObject({ sessionId: 'meal-1', title: '训练晚餐' })
    expect(result.messages[0]).toMatchObject({
      id: 1, role: 'user', content: '怎么吃？',
      imageId: 'safe-image', imageUrl: '/api/chat/images/safe-image',
    })
    expect(result.messages[1].toolCalls[0].name).toBe('search_nutrition_knowledge')
  })

  it('accepts raw arrays and filters invalid session rows', () => {
    expect(normalizeChatSessions([{ session_id: 'a' }, { title: 'missing id' }]))
      .toEqual([expect.objectContaining({ sessionId: 'a', title: '新对话' })])
  })
})
