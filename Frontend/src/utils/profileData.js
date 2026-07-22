function unwrapApiData(payload) {
  const firstLayer = payload?.data ?? payload
  return firstLayer?.data ?? firstLayer
}

function textOrEmpty(value) {
  return typeof value === 'string' ? value : ''
}

function inputNumber(value) {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  return Number.isFinite(number) ? number : ''
}

function nullableText(value) {
  const text = typeof value === 'string' ? value.trim() : ''
  return text || null
}

function nullableNumber(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

export function emptyProfileForm() {
  return {
    phone: '',
    currentWeight: '',
    height: '',
    birthDate: '',
    sexForCalculation: '',
    activityLevel: '',
    mode: '',
    targetWeight: '',
    dailyCalories: '',
    proteinTarget: '',
    trainingDays: '',
  }
}

export function normalizeUserProfile(payload) {
  const data = unwrapApiData(payload) || {}
  const account = data.account && typeof data.account === 'object' ? data.account : {}
  const body = data.body_profile && typeof data.body_profile === 'object' ? data.body_profile : {}
  const goal = data.goal && typeof data.goal === 'object' ? data.goal : {}

  return {
    account: {
      ...account,
      roles: Array.isArray(account.roles) ? account.roles : [],
      avatar: textOrEmpty(account.avatar),
    },
    hasBodyProfile: Boolean(data.body_profile),
    hasGoal: Boolean(data.goal),
    form: {
      phone: textOrEmpty(account.phone),
      currentWeight: inputNumber(body.current_weight_kg),
      height: inputNumber(body.height_cm),
      birthDate: textOrEmpty(body.birth_date),
      sexForCalculation: textOrEmpty(body.sex_for_calculation),
      activityLevel: textOrEmpty(body.activity_level),
      mode: textOrEmpty(goal.mode),
      targetWeight: inputNumber(goal.target_weight_kg),
      dailyCalories: inputNumber(goal.daily_calories_kcal),
      proteinTarget: inputNumber(goal.protein_target_g),
      trainingDays: inputNumber(goal.training_days_per_week),
    },
  }
}

export function profileFormToPatch(form) {
  return {
    account: {
      phone: nullableText(form.phone),
    },
    body_profile: {
      current_weight_kg: nullableNumber(form.currentWeight),
      height_cm: nullableNumber(form.height),
      birth_date: nullableText(form.birthDate),
      sex_for_calculation: nullableText(form.sexForCalculation),
      activity_level: nullableText(form.activityLevel),
    },
    goal: {
      mode: nullableText(form.mode),
      target_weight_kg: nullableNumber(form.targetWeight),
      daily_calories_kcal: nullableNumber(form.dailyCalories),
      protein_target_g: nullableNumber(form.proteinTarget),
      training_days_per_week: nullableNumber(form.trainingDays),
    },
  }
}

export function legacyProfileToPatch(legacy = {}) {
  return {
    body_profile: {
      current_weight_kg: nullableNumber(legacy.currentWeight),
    },
    goal: {
      mode: nullableText(legacy.mode),
      target_weight_kg: nullableNumber(legacy.targetWeight),
      daily_calories_kcal: nullableNumber(legacy.dailyCalories),
      protein_target_g: nullableNumber(legacy.proteinTarget),
      training_days_per_week: nullableNumber(legacy.trainingDays),
    },
  }
}

export function normalizeAvatarResponse(payload) {
  const data = unwrapApiData(payload) || {}
  return {
    avatar: textOrEmpty(data.avatar),
    updatedAt: data.updated_at || null,
  }
}
