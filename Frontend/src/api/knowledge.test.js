import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/utils/request', () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}))

import request from '@/utils/request'
import { askKnowledgeApi, searchKnowledgeApi } from './knowledge'

describe('knowledge api', () => {
  beforeEach(() => {
    request.get.mockReset()
    request.post.mockReset()
    request.delete.mockReset()
  })

  it('sends the documented RAG answer parameters with a long timeout', () => {
    const controller = new AbortController()
    const params = {
      query: '减脂期怎么安排晚餐',
      k: 5,
      verify_web: true,
      store_web: false,
    }

    askKnowledgeApi(params, { signal: controller.signal })

    expect(request.get).toHaveBeenCalledWith('/knowledge/ask', {
      params,
      timeout: 120000,
      silent: true,
      signal: controller.signal,
    })
  })

  it('keeps fragment search on its original route', () => {
    const params = { query: '膳食纤维', k: 3 }
    searchKnowledgeApi(params)
    expect(request.get).toHaveBeenCalledWith('/knowledge/search', { params })
  })
})
