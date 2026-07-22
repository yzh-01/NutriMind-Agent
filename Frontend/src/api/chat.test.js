import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/utils/request', () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}))

import request from '@/utils/request'
import {
  createChatSessionApi, deleteChatSessionApi, getChatSessionApi, getChatSessionsApi,
  sendChatImageApi, sendChatMessageApi,
} from './chat'

describe('chat api', () => {
  beforeEach(() => {
    request.get.mockReset()
    request.post.mockReset()
    request.delete.mockReset()
  })

  it('sends the documented text chat payload', () => {
    const controller = new AbortController()
    sendChatMessageApi({ sessionId: 'meal-1', message: '分析这一餐' }, { signal: controller.signal })
    expect(request.post).toHaveBeenCalledWith('/chat/message', {
      session_id: 'meal-1',
      message: '分析这一餐',
    }, expect.objectContaining({ silent: true, timeout: 120000, signal: controller.signal }))
  })

  it('uses multipart fields for image chat without setting content-type manually', () => {
    const file = new Blob(['image'], { type: 'image/jpeg' })
    const controller = new AbortController()
    sendChatImageApi(file, { sessionId: 'meal-image', message: '估算热量' }, { signal: controller.signal })
    const [, formData, config] = request.post.mock.calls[0]
    expect(request.post.mock.calls[0][0]).toBe('/chat/image')
    expect(formData).toBeInstanceOf(FormData)
    expect(formData.get('file')).toBeInstanceOf(Blob)
    expect(formData.get('file').size).toBe(file.size)
    expect(formData.get('message')).toBe('估算热量')
    expect(formData.get('session_id')).toBe('meal-image')
    expect(config).toEqual(expect.objectContaining({ silent: true, timeout: 180000, signal: controller.signal }))
    expect(config.headers).toBeUndefined()
  })

  it('uses the documented persistent session routes', () => {
    createChatSessionApi('训练计划')
    getChatSessionsApi()
    getChatSessionApi('meal/a b')
    deleteChatSessionApi('meal/a b')

    expect(request.post).toHaveBeenCalledWith('/chat/sessions', { title: '训练计划' }, expect.objectContaining({ silent: true }))
    expect(request.get).toHaveBeenNthCalledWith(1, '/chat/sessions', expect.objectContaining({ silent: true }))
    expect(request.get).toHaveBeenNthCalledWith(2, '/chat/sessions/meal%2Fa%20b', expect.objectContaining({ silent: true }))
    expect(request.delete).toHaveBeenCalledWith('/chat/sessions/meal%2Fa%20b', expect.objectContaining({ silent: true }))
  })
})
