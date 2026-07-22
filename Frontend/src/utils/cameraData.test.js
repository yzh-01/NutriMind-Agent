import { describe, expect, it } from 'vitest'
import { normalizeCameraHistory, normalizeCameraItem } from './cameraData'

describe('API 3.0 camera data adapters', () => {
  it('prefers the original file name when the upload response provides it', () => {
    expect(normalizeCameraItem({
      id: 'generated.png',
      original_name: '晚餐.png',
      filename: 'generated.png',
      size: 2048,
    })).toMatchObject({
      id: 'generated.png',
      storedName: 'generated.png',
      displayName: '晚餐.png',
      size: 2048,
    })
  })

  it('uses the stored file name for history items without an original name', () => {
    expect(normalizeCameraItem({ id: 'photo.webp', filename: 'photo.webp' }).displayName)
      .toBe('photo.webp')
  })

  it('normalizes the paginated history response', () => {
    expect(normalizeCameraHistory({
      code: 200,
      data: {
        items: [{ id: 'one.jpg', filename: 'one.jpg' }],
        total: 9,
        page: 2,
        page_size: 8,
      },
    })).toMatchObject({ total: 9, page: 2, pageSize: 8 })
  })
})
