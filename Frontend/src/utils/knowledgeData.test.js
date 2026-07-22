import { describe, expect, it } from 'vitest'
import { normalizeKnowledgeAnswer, normalizeKnowledgeSearch, normalizeKnowledgeStats } from './knowledgeData'

describe('API 2.0 knowledge data adapters', () => {
  it('reads source details from the new metadata object', () => {
    const normalized = normalizeKnowledgeSearch({
      code: 200,
      data: {
        results: [{
          content: '营养知识',
          metadata: { source: '/tmp/nutrition.txt', file_name: 'nutrition.txt', type: 'text' },
          score: 0.95,
        }],
      },
    })

    expect(normalized.results[0]).toMatchObject({
      source: '/tmp/nutrition.txt',
      fileName: 'nutrition.txt',
      type: 'text',
    })
  })

  it('keeps API 1.0 search results compatible', () => {
    const normalized = normalizeKnowledgeSearch({ data: { results: [{ source: 'guide.pdf' }] } })
    expect(normalized.results[0].source).toBe('guide.pdf')
    expect(normalized.results[0].fileName).toBe('guide.pdf')
  })

  it('derives document count from API 2.0 sources', () => {
    const normalized = normalizeKnowledgeStats({
      data: { total_chunks: 7, sources: [{ source: '/tmp/a.txt' }, { source: '/tmp/b.png' }] },
    })
    expect(normalized.total_documents).toBe(2)
    expect(normalized.total_chunks).toBe(7)
  })

  it('keeps the API 1.0 document count when present', () => {
    const normalized = normalizeKnowledgeStats({ data: { total_documents: 10, total_chunks: 100 } })
    expect(normalized.total_documents).toBe(10)
    expect(normalized.total_chunks).toBe(100)
  })

  it('normalizes RAG answers without treating distance as a percentage', () => {
    const normalized = normalizeKnowledgeAnswer({ code: 200, data: {
      query: '蛋白质', answer: '完整回答 [local-1]',
      sources: [
        { id: 'local-1', type: 'knowledge', title: '指南', score: 0.2, excerpt: '摘要' },
        { id: 'web-1', type: 'web', title: '网页', url: 'https://example.org', score: null },
      ],
      used_web_fallback: true, cross_verified: true,
    } })

    expect(normalized.answer).toContain('完整回答')
    expect(normalized.sources[0]).toMatchObject({ type: 'knowledge', score: 0.2 })
    expect(normalized.sources[1]).toMatchObject({ type: 'web', score: null, url: 'https://example.org' })
    expect(normalized.usedWebFallback).toBe(true)
    expect(normalized.crossVerified).toBe(true)
  })
})
