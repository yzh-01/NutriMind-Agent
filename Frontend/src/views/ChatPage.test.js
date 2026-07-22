// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const chatMocks = vi.hoisted(() => ({
  getChatSessionsApi: vi.fn(),
  sendChatImageApi: vi.fn(),
  sendChatMessageApi: vi.fn(),
}))
const profileMocks = vi.hoisted(() => ({ getProfileApi: vi.fn() }))

vi.mock('@/api/chat', () => ({
  getChatSessionsApi: chatMocks.getChatSessionsApi,
  sendChatImageApi: chatMocks.sendChatImageApi,
  sendChatMessageApi: chatMocks.sendChatMessageApi,
}))
vi.mock('@/api/profile', () => ({ getProfileApi: profileMocks.getProfileApi }))

import ChatPage from './ChatPage.vue'
import { useUserStore } from '@/stores/user'

describe('ChatPage generation controls', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    setActivePinia(createPinia())
    useUserStore().saveUser({ id: 18, username: 'zhangsan', roles: [] })
    chatMocks.getChatSessionsApi.mockResolvedValue([])
    profileMocks.getProfileApi.mockResolvedValue({
      account: { id: 18, username: 'zhangsan', roles: [] },
      body_profile: { current_weight_kg: 72 },
      goal: {
        mode: 'cut', target_weight_kg: 66, daily_calories_kcal: 1900,
        protein_target_g: 130, training_days_per_week: 4,
      },
    })
  })

  it('shows the authenticated user profile instead of demo plan values', async () => {
    const wrapper = mount(ChatPage)
    await flushPromises()

    const context = wrapper.find('.context-panel').text()
    expect(context).toContain('减脂')
    expect(context).toContain('每日热量目标 1,900 kcal')
    expect(context).toContain('130 g / 天')
    expect(context).toContain('4 天 / 周')
    expect(context).toContain('66 kg')
    expect(context).not.toContain('2,140')
    expect(context).not.toContain('108 / 150g')
    expect(context).not.toContain('680 kcal')
    expect(context).not.toContain('上肢推拉')
    wrapper.unmount()
  })

  it('clearly marks plan fields that have not been configured', async () => {
    profileMocks.getProfileApi.mockResolvedValue({
      account: { id: 18, username: 'zhangsan', roles: [] },
      body_profile: null,
      goal: null,
    })

    const wrapper = mount(ChatPage)
    await flushPromises()

    const context = wrapper.find('.context-panel').text()
    expect(context).toContain('尚未设置')
    expect(context).toContain('未设置')
    expect(context).toContain('完善个人资料')
    expect(context).toContain('不代表今日实际摄入或训练记录')
    wrapper.unmount()
  })

  it('aborts the active request and replaces the pending reply', async () => {
    let requestSignal
    chatMocks.sendChatMessageApi.mockImplementation((_payload, config) => {
      requestSignal = config.signal
      return new Promise((_resolve, reject) => {
        requestSignal.addEventListener('abort', () => reject(Object.assign(new Error('cancelled'), { code: 'ERR_CANCELED' })), { once: true })
      })
    })

    const wrapper = mount(ChatPage)
    await wrapper.find('textarea').setValue('帮我安排训练后的晚餐')
    await wrapper.find('.send-button').trigger('click')

    expect(chatMocks.sendChatMessageApi).toHaveBeenCalledOnce()
    expect(wrapper.find('.stop-button').exists()).toBe(true)
    expect(requestSignal.aborted).toBe(false)

    await wrapper.find('.stop-button').trigger('click')
    await flushPromises()

    expect(requestSignal.aborted).toBe(true)
    expect(wrapper.text()).toContain('已停止生成')
    expect(wrapper.find('.send-button').exists()).toBe(true)
    wrapper.unmount()
  })
})
