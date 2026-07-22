import { describe, expect, it } from 'vitest'
import {
  legacyProfileToPatch, normalizeAvatarResponse, normalizeUserProfile, profileFormToPatch,
} from './profileData'

describe('Profile API data adapter', () => {
  it('normalizes configured and nullable profile sections', () => {
    const result = normalizeUserProfile({
      data: {
        account: { id: 18, phone: null, avatar: '/avatar/file', roles: ['user'] },
        body_profile: { current_weight_kg: 72.5, height_cm: null },
        goal: { mode: 'cut', training_days_per_week: 4 },
      },
    })

    expect(result.account.avatar).toBe('/avatar/file')
    expect(result.hasBodyProfile).toBe(true)
    expect(result.form).toMatchObject({
      phone: '', currentWeight: 72.5, height: '', mode: 'cut', trainingDays: 4,
    })
  })

  it('builds the documented nested PATCH body and uses null for cleared fields', () => {
    expect(profileFormToPatch({
      phone: ' 13800138000 ', currentWeight: '72.5', height: '', birthDate: '',
      sexForCalculation: 'male', activityLevel: 'moderate', mode: 'cut',
      targetWeight: '66', dailyCalories: '1900', proteinTarget: '130', trainingDays: '4',
    })).toEqual({
      account: { phone: '13800138000' },
      body_profile: {
        current_weight_kg: 72.5, height_cm: null, birth_date: null,
        sex_for_calculation: 'male', activity_level: 'moderate',
      },
      goal: {
        mode: 'cut', target_weight_kg: 66, daily_calories_kcal: 1900,
        protein_target_g: 130, training_days_per_week: 4,
      },
    })
  })

  it('maps legacy local values and unwraps avatar responses', () => {
    expect(legacyProfileToPatch({ currentWeight: 70, mode: 'maintain', trainingDays: 3 })).toMatchObject({
      body_profile: { current_weight_kg: 70 },
      goal: { mode: 'maintain', training_days_per_week: 3 },
    })
    expect(normalizeAvatarResponse({ data: { avatar: '/new-avatar', updated_at: 'now' } }))
      .toEqual({ avatar: '/new-avatar', updatedAt: 'now' })
  })
})
