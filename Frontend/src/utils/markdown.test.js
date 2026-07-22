import { describe, expect, it } from 'vitest'
import { renderMarkdown } from './markdown'

describe('renderMarkdown', () => {
  it('renders common formatting used in coach replies', () => {
    const html = renderMarkdown('## 今日建议\n\n- 蛋白质 130g\n- 热量 1900kcal')
    expect(html).toContain('<h2>今日建议</h2>')
    expect(html).toContain('<li>蛋白质 130g</li>')
  })

  it('escapes raw HTML from a model response', () => {
    const html = renderMarkdown('<img src=x onerror=alert(1)>')
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img')
  })

  it('turns a plain web address into a safe link', () => {
    const html = renderMarkdown('参考 https://example.com/nutrition')
    expect(html).toContain('href="https://example.com/nutrition"')
  })
})
