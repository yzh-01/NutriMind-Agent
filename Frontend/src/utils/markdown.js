import MarkdownIt from 'markdown-it'

const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })

export function renderMarkdown(text) {
  return markdown.render(text || '')
}
