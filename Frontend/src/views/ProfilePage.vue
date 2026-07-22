<template>
  <div class="profile-page page-shell">
    <header class="page-header">
      <div>
        <span class="eyebrow"><Target :size="16" weight="bold" /> BODY & GOALS</span>
        <h1 class="page-title">目标不是数字，<br><em>是下一次选择。</em></h1>
        <p class="page-description">把身体目标和训练节奏交给 NutriMind，后续建议会围绕这套基准展开。</p>
      </div>
      <span class="status-chip" :class="{ warning: profileError }" aria-live="polite">
        <CircleNotch v-if="profileLoading" class="spin" :size="16" weight="bold" />
        <WarningCircle v-else-if="profileError" :size="16" weight="fill" />
        <CheckCircle v-else :size="16" weight="fill" />
        {{ syncStatusText }}
      </span>
    </header>

    <section class="profile-grid">
      <aside class="identity-card surface">
        <div class="identity-top">
          <div class="avatar-editor">
            <div class="avatar">
              <img v-if="avatarUrl" :src="avatarUrl" :alt="`${displayUsername} 的头像`">
              <span v-else aria-hidden="true">{{ userInitial }}</span>
            </div>
            <input ref="avatarInput" class="sr-only" type="file" accept="image/jpeg,image/png,image/webp" @change="uploadAvatar">
            <div class="avatar-actions">
              <button type="button" :disabled="avatarSaving || userStore.isDemo" @click="avatarInput?.click()">
                <CircleNotch v-if="avatarSaving" class="spin" :size="16" />
                <Camera v-else :size="16" />{{ avatarUrl ? '更换' : '上传' }}
              </button>
              <button v-if="avatarUrl" class="danger" type="button" :disabled="avatarSaving || userStore.isDemo" @click="removeAvatar">
                <Trash :size="16" />移除
              </button>
            </div>
          </div>
          <span class="account-state"><span /> ACTIVE</span>
        </div>
        <span class="identity-kicker">ATHLETE PROFILE</span>
        <h2>{{ displayUsername }}</h2>
        <p>{{ accountInfo.email || '未设置邮箱' }}</p>
        <span class="role">{{ roleText }}</span>

        <div class="goal-readout">
          <div>
            <small>当前计划</small>
            <strong>{{ modeLabel }}</strong>
          </div>
          <TrendDown v-if="profile.mode === 'cut'" :size="34" weight="duotone" />
          <Barbell v-else-if="profile.mode === 'muscle'" :size="34" weight="duotone" />
          <Heartbeat v-else :size="34" weight="duotone" />
        </div>

        <div class="weight-progress">
          <div><span>{{ profile.currentWeight || '--' }} kg</span><span>目标 {{ profile.targetWeight || '--' }} kg</span></div>
          <div class="progress-track"><i :style="{ width: `${goalProgress}%` }" /></div>
          <small>计划配置完整度 {{ goalProgress }}%</small>
        </div>

        <dl>
          <div><dt><IdentificationCard :size="17" /> 账户 ID</dt><dd>{{ accountInfo.id || '--' }}</dd></div>
          <div><dt><Phone :size="17" /> 手机</dt><dd>{{ accountInfo.phone || '未填写' }}</dd></div>
          <div><dt><ClockCounterClockwise :size="17" /> 最近登录</dt><dd>{{ formatDate(accountInfo.last_login_at) }}</dd></div>
        </dl>
      </aside>

      <section
        ref="goalPanel"
        id="goals-panel"
        class="goal-panel surface"
        aria-labelledby="goal-panel-title"
      >
        <div class="panel-heading">
          <div>
            <span>{{ activeGoalStepMeta.eyebrow }}</span>
            <h2 id="goal-panel-title" class="section-title">{{ activeGoalStepMeta.heading }}</h2>
          </div>
          <span class="step-mark" aria-live="polite">{{ String(activeGoalStep).padStart(2, '0') }} / 03</span>
        </div>

        <div v-if="profileLoading" class="profile-feedback" aria-label="正在加载个人资料">
          <CircleNotch class="spin" :size="30" weight="bold" />
          <p>正在同步个人资料与身体目标…</p>
        </div>
        <div v-else-if="profileError" class="profile-feedback error" role="alert">
          <WarningCircle :size="32" weight="duotone" />
          <p>{{ profileError }}</p>
          <button type="button" @click="loadProfile">重新加载</button>
        </div>
        <template v-else>
          <nav class="goal-stepper" aria-label="身体目标设置步骤">
            <button
              v-for="step in goalSteps"
              :key="step.id"
              type="button"
              :class="{ active: activeGoalStep === step.id, complete: isGoalStepComplete(step.id) }"
              :aria-current="activeGoalStep === step.id ? 'step' : undefined"
              @click="goToGoalStep(step.id)"
            >
              <span class="goal-step-index">
                <CheckCircle v-if="isGoalStepComplete(step.id) && activeGoalStep !== step.id" :size="18" weight="fill" />
                <template v-else>{{ String(step.id).padStart(2, '0') }}</template>
              </span>
              <span><b>{{ step.title }}</b><small>{{ step.caption }}</small></span>
            </button>
          </nav>

          <div class="goal-step-content" aria-live="polite">
            <section v-if="activeGoalStep === 1" class="form-section" aria-labelledby="goal-mode-title">
              <div class="section-label">
                <span>01</span>
                <div><h3 id="goal-mode-title">你当前最重要的目标</h3><p>它会决定热量和营养建议的侧重点。</p></div>
              </div>
              <div class="mode-grid">
                <button
                  v-for="mode in modes"
                  :key="mode.value"
                  type="button"
                  :class="{ active: profile.mode === mode.value }"
                  :aria-pressed="profile.mode === mode.value"
                  @click="profile.mode = mode.value"
                >
                  <component :is="mode.icon" :size="24" :weight="profile.mode === mode.value ? 'fill' : 'regular'" />
                  <b>{{ mode.label }}</b>
                  <span>{{ mode.description }}</span>
                </button>
              </div>
            </section>

            <section v-else-if="activeGoalStep === 2" class="form-section" aria-labelledby="body-data-title">
              <div class="section-label">
                <span>02</span>
                <div><h3 id="body-data-title">账户与身体基准</h3><p>补全联系方式和身体信息，为营养建议提供统一基准。</p></div>
              </div>
              <div class="field-grid">
                <FuelField v-model="profile.phone" label="手机号（可选）" type="tel" autocomplete="tel" placeholder="例如 13800138000" />
                <FuelField v-model="profile.currentWeight" label="当前体重（kg）" type="number" min="30" max="250" placeholder="例如 72" />
                <FuelField v-model="profile.height" label="身高（cm，可选）" type="number" min="100" max="250" placeholder="例如 175" />
                <FuelField v-model="profile.birthDate" label="出生日期（可选）" type="date" :max="today" />
                <label class="select-field"><span>计算性别（可选）</span><select v-model="profile.sexForCalculation"><option value="">未设置</option><option value="male">男</option><option value="female">女</option><option value="unspecified">不指定</option></select></label>
                <label class="select-field"><span>日常活动水平（可选）</span><select v-model="profile.activityLevel"><option value="">未设置</option><option value="sedentary">久坐</option><option value="light">轻度活动</option><option value="moderate">中等活动</option><option value="high">高活动量</option><option value="very_high">极高活动量</option></select></label>
              </div>
            </section>

            <section v-else class="form-section" aria-labelledby="nutrition-data-title">
              <div class="section-label">
                <span>03</span>
                <div><h3 id="nutrition-data-title">补给与训练目标</h3><p>设置一套可执行的热量、蛋白质和训练节奏。</p></div>
              </div>
              <div class="field-grid">
                <FuelField v-model="profile.targetWeight" label="目标体重（kg）" type="number" min="30" max="250" placeholder="例如 66" />
                <FuelField v-model="profile.dailyCalories" label="每日热量目标（kcal）" type="number" min="1000" max="6000" placeholder="例如 1900" />
                <FuelField v-model="profile.proteinTarget" label="每日蛋白质（g）" type="number" min="30" max="400" placeholder="例如 130" />
              </div>
              <label class="training-days">
                <span><CalendarDots :size="18" /> 每周训练频率</span>
                <div>
                  <button
                    v-for="day in 7"
                    :key="day"
                    type="button"
                    :class="{ active: Number(profile.trainingDays) === day }"
                    :aria-label="`每周训练 ${day} 天`"
                    :aria-pressed="Number(profile.trainingDays) === day"
                    @click="profile.trainingDays = day"
                  >{{ day }}</button>
                </div>
                <small>{{ trainingCopy }}</small>
              </label>
            </section>
          </div>

          <footer class="form-footer">
            <div class="local-note"><CloudCheck :size="18" /><span><b>{{ activeGoalStepMeta.noteTitle }}</b>{{ activeGoalStepMeta.note }}</span></div>
            <div class="step-actions">
              <button v-if="activeGoalStep > 1" class="step-back" type="button" @click="goToGoalStep(activeGoalStep - 1, false)">上一步</button>
              <FuelButton v-if="activeGoalStep < 3" @click="goToGoalStep(activeGoalStep + 1)">下一步</FuelButton>
              <FuelButton v-else :loading="saving" :disabled="userStore.isDemo" @click="saveProfile">保存全部资料</FuelButton>
            </div>
          </footer>
        </template>
      </section>

    </section>
  </div>
</template>

<script setup>
import { computed, markRaw, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  PhBarbell as Barbell, PhCalendarDots as CalendarDots, PhCamera as Camera,
  PhCheckCircle as CheckCircle, PhCircleNotch as CircleNotch,
  PhClockCounterClockwise as ClockCounterClockwise, PhCloudCheck as CloudCheck,
  PhHeartbeat as Heartbeat, PhIdentificationCard as IdentificationCard,
  PhPersonSimpleRun as PersonSimpleRun, PhPhone as Phone,
  PhTarget as Target, PhTrash as Trash, PhTrendDown as TrendDown,
  PhWarningCircle as WarningCircle,
} from '@phosphor-icons/vue'
import FuelButton from '@/components/ui/FuelButton.vue'
import FuelField from '@/components/ui/FuelField.vue'
import {
  deleteAvatarApi, getProfileApi, updateProfileApi, uploadAvatarApi,
} from '@/api/profile'
import { useUserStore } from '@/stores/user'
import {
  emptyProfileForm, legacyProfileToPatch, normalizeAvatarResponse,
  normalizeUserProfile, profileFormToPatch,
} from '@/utils/profileData'

const PROFILE_KEY = 'nutrimind_goal_profile'
const demoProfile = {
  ...emptyProfileForm(), mode: 'cut', currentWeight: 72, targetWeight: 66,
  dailyCalories: 1900, proteinTarget: 130, trainingDays: 4,
  height: 175, sexForCalculation: 'unspecified', activityLevel: 'moderate',
}

const userStore = useUserStore()
const profile = reactive(emptyProfileForm())
const serverAccount = ref(null)
const profileLoading = ref(true)
const profileError = ref('')
const activeGoalStep = ref(1)
const goalPanel = ref(null)
const saving = ref(false)
const avatarSaving = ref(false)
const avatarInput = ref()
const avatarVersion = ref(Date.now())
const modes = [
  { value: 'cut', label: '减脂', description: '控制热量，保住训练表现', icon: markRaw(TrendDown) },
  { value: 'muscle', label: '增肌', description: '稳定盈余，优先蛋白质', icon: markRaw(Barbell) },
  { value: 'maintain', label: '保持', description: '维持体态，提高饮食质量', icon: markRaw(PersonSimpleRun) },
]
const goalSteps = [
  {
    id: 1, title: '主要目标', caption: '确定建议方向', eyebrow: 'GOAL DIRECTION', heading: '选择你的主要目标',
    noteTitle: '先确定建议方向', note: '后续营养建议会围绕这个目标调整侧重点。',
  },
  {
    id: 2, title: '身体基准', caption: '补充基础数据', eyebrow: 'PERSONAL BASELINE', heading: '补充身体与活动基准',
    noteTitle: '填写必要的身体基准', note: '可选字段可以暂时留空，之后仍能回来补充。',
  },
  {
    id: 3, title: '营养训练', caption: '设置执行目标', eyebrow: 'NUTRITION & TRAINING', heading: '设置营养与训练目标',
    noteTitle: '资料会同步到你的账户', note: '保存后可在其他设备恢复；旧的本机目标配置会在首次同步后自动迁移。',
  },
]

const today = new Date().toISOString().slice(0, 10)
const accountInfo = computed(() => ({ ...(userStore.user || {}), ...(serverAccount.value || {}) }))
const displayUsername = computed(() => accountInfo.value.username || userStore.username || 'NutriMind 用户')
const roleText = computed(() => accountInfo.value.roles?.join('、') || '普通用户')
const userInitial = computed(() => displayUsername.value.slice(0, 1).toUpperCase() || 'N')
const avatarUrl = computed(() => {
  const source = accountInfo.value.avatar
  if (!source) return ''
  const separator = source.includes('?') ? '&' : '?'
  return `${source}${separator}v=${avatarVersion.value}`
})
const syncStatusText = computed(() => {
  if (profileLoading.value) return '正在同步账户资料'
  if (profileError.value) return '账户资料同步失败'
  if (userStore.isDemo) return '体验模式本地预览'
  return '配置已同步至账户'
})
const modeLabel = computed(() => modes.find((item) => item.value === profile.mode)?.label || '尚未设置')
const activeGoalStepMeta = computed(() => goalSteps.find((step) => step.id === activeGoalStep.value) || goalSteps[0])
const goalProgress = computed(() => {
  const fields = ['mode', 'currentWeight', 'targetWeight', 'dailyCalories', 'proteinTarget', 'trainingDays']
  return Math.round(fields.filter((key) => profile[key] !== '' && profile[key] !== null).length / fields.length * 100)
})
const trainingCopy = computed(() => {
  const days = Number(profile.trainingDays)
  if (!days) return '选择每周计划训练的天数。'
  if (days <= 2) return '轻量节奏，优先建立稳定习惯。'
  if (days <= 4) return '均衡节奏，训练与恢复都有空间。'
  return '高频节奏，请特别关注睡眠与恢复。'
})

function readLegacyProfile() {
  try {
    const value = JSON.parse(localStorage.getItem(PROFILE_KEY) || 'null')
    return value && typeof value === 'object' ? value : null
  } catch {
    return null
  }
}

function applyNormalizedProfile(normalized) {
  Object.assign(profile, emptyProfileForm(), normalized.form)
  serverAccount.value = { ...(userStore.user || {}), ...normalized.account }
  if (normalized.account?.id) userStore.mergeUser(normalized.account)
}

async function loadProfile() {
  profileLoading.value = true
  profileError.value = ''
  if (userStore.isDemo) {
    Object.assign(profile, demoProfile)
    serverAccount.value = userStore.user
    profileLoading.value = false
    return
  }

  try {
    let normalized = normalizeUserProfile(await getProfileApi({ silent: true }))
    const legacy = readLegacyProfile()
    if (!normalized.hasBodyProfile && !normalized.hasGoal && legacy) {
      const migrated = await updateProfileApi(legacyProfileToPatch(legacy), { silent: true })
      normalized = normalizeUserProfile(migrated)
      if (!normalized.account.id) normalized = normalizeUserProfile(await getProfileApi({ silent: true }))
      localStorage.removeItem(PROFILE_KEY)
      ElMessage.success('已将这台设备上的旧目标配置迁移到账户')
    }
    applyNormalizedProfile(normalized)
  } catch {
    profileError.value = '没有读取到个人资料，请确认后端个人资料服务已部署后重试。'
  } finally {
    profileLoading.value = false
  }
}

function formatDate(value) {
  if (!value) return '暂无记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '暂无记录'
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric' }).format(date)
}

function numberInRange(value, min, max, integer = false) {
  const number = Number(value)
  return Number.isFinite(number) && number >= min && number <= max && (!integer || Number.isInteger(number))
}

function validateGoalStep(step) {
  if (step === 1) {
    return modes.some((item) => item.value === profile.mode) ? '' : '请选择当前最重要的目标'
  }
  if (step === 2) {
    if (!numberInRange(profile.currentWeight, 30, 250)) return '当前体重需要在 30～250 kg 之间'
    if (profile.height !== '' && !numberInRange(profile.height, 100, 250)) return '身高需要在 100～250 cm 之间'
    if (profile.birthDate && profile.birthDate > today) return '出生日期不能晚于今天'
    return ''
  }
  if (!numberInRange(profile.targetWeight, 30, 250)) return '目标体重需要在 30～250 kg 之间'
  if (!numberInRange(profile.dailyCalories, 1000, 6000, true)) return '每日热量需要是 1000～6000 的整数'
  if (!numberInRange(profile.proteinTarget, 30, 400, true)) return '每日蛋白质需要是 30～400 的整数'
  if (!numberInRange(profile.trainingDays, 1, 7, true)) return '请选择每周 1～7 天的训练频率'
  return ''
}

function isGoalStepComplete(step) {
  return !validateGoalStep(step)
}

async function revealGoalStep() {
  await nextTick()
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  goalPanel.value?.scrollIntoView?.({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
}

async function goToGoalStep(targetStep, validateForward = true) {
  const target = Math.min(3, Math.max(1, Number(targetStep) || 1))
  if (target === activeGoalStep.value) return
  if (validateForward && target > activeGoalStep.value) {
    for (let step = activeGoalStep.value; step < target; step += 1) {
      const validationMessage = validateGoalStep(step)
      if (validationMessage) {
        ElMessage.warning(validationMessage)
        return
      }
    }
  }
  activeGoalStep.value = target
  await revealGoalStep()
}

function validateProfile() {
  for (const step of goalSteps) {
    const message = validateGoalStep(step.id)
    if (message) return { step: step.id, message }
  }
  return null
}

async function saveProfile() {
  const validation = validateProfile()
  if (validation) {
    activeGoalStep.value = validation.step
    ElMessage.warning(validation.message)
    await revealGoalStep()
    return
  }
  saving.value = true
  try {
    let normalized = normalizeUserProfile(await updateProfileApi(profileFormToPatch(profile), { silent: true }))
    if (!normalized.account.id) normalized = normalizeUserProfile(await getProfileApi({ silent: true }))
    applyNormalizedProfile(normalized)
    localStorage.removeItem(PROFILE_KEY)
    ElMessage.success('个人资料与身体目标已同步')
  } catch {
    ElMessage.error('个人资料保存失败，请检查填写内容后重试')
  } finally {
    saving.value = false
  }
}

async function uploadAvatar(event) {
  const input = event.target
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    ElMessage.warning('头像仅支持 JPG、PNG 或 WEBP 格式')
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('头像文件不能超过 5MB')
    return
  }

  avatarSaving.value = true
  try {
    const result = normalizeAvatarResponse(await uploadAvatarApi(file, { silent: true }))
    if (result.avatar) {
      serverAccount.value = { ...accountInfo.value, avatar: result.avatar }
      userStore.setAvatar(result.avatar)
      avatarVersion.value = Date.now()
    } else {
      await loadProfile()
    }
    ElMessage.success('头像已更新')
  } catch {
    ElMessage.error('头像上传失败，请检查文件后重试')
  } finally {
    avatarSaving.value = false
  }
}

async function removeAvatar() {
  try {
    await ElMessageBox.confirm('移除当前头像后将恢复为用户名首字母，是否继续？', '移除头像', {
      type: 'warning', confirmButtonText: '确认移除', cancelButtonText: '取消',
    })
    avatarSaving.value = true
    await deleteAvatarApi({ silent: true })
    serverAccount.value = { ...accountInfo.value, avatar: '' }
    userStore.setAvatar(null)
    avatarVersion.value = Date.now()
    ElMessage.success('头像已移除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('头像移除失败，请稍后重试')
  } finally {
    avatarSaving.value = false
  }
}

onMounted(loadProfile)
</script>

<style lang="scss" scoped>
.profile-page { display: grid; gap: 22px; }
.page-header { min-height: 235px; padding: clamp(26px, 4vw, 56px); display: flex; align-items: flex-end; justify-content: space-between; gap: 26px; background: linear-gradient(110deg, rgba(23,28,24,.98), rgba(15,18,16,.9)), radial-gradient(circle at 83% 18%, rgba(242,117,63,.17), transparent 34%); border: 1px solid var(--border); border-radius: var(--radius-lg); }
.page-header em { color: var(--accent); font-style: normal; }
.page-header .status-chip.warning { color: #ff938d; border-color: rgba(240, 103, 95, .28); }
.eyebrow { margin-bottom: 17px; display: flex; align-items: center; gap: 8px; color: var(--primary); font-size: .74rem; font-weight: 700; letter-spacing: .13em; }
.profile-grid { display: grid; grid-template-columns: minmax(280px, .72fr) minmax(0, 1.6fr); gap: 16px; align-items: start; }
.identity-card { grid-row: 1; padding: 24px; }
.identity-top { margin-bottom: 26px; display: flex; align-items: flex-start; justify-content: space-between; }
.avatar-editor { display: grid; gap: 11px; }
.avatar { width: 76px; height: 76px; overflow: hidden; display: grid; place-items: center; color: #12170f; background: var(--primary); border-radius: 19px 19px 19px 5px; box-shadow: 10px 10px 0 rgba(159,226,75,.1); font-family: "Barlow Condensed"; font-size: 2.15rem; font-weight: 700; }
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.avatar-actions { display: flex; gap: 6px; }
.avatar-actions button { min-height: 44px; padding: 0 9px; display: inline-flex; align-items: center; justify-content: center; gap: 5px; color: var(--text-secondary); background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 8px; font-size: .66rem; transition: color 180ms var(--ease-out), border-color 180ms var(--ease-out), background 180ms var(--ease-out); }
.avatar-actions button:hover:not(:disabled) { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.3); }
.avatar-actions button.danger:hover:not(:disabled) { color: #ff938d; background: rgba(240,103,95,.08); border-color: rgba(240,103,95,.25); }
.avatar-actions button:disabled { opacity: .42; }
.account-state { display: inline-flex; align-items: center; gap: 6px; color: var(--primary); font-size: .7rem; font-weight: 700; letter-spacing: .12em; }
.account-state span { width: 7px; height: 7px; background: var(--primary); border-radius: 50%; box-shadow: 0 0 0 4px rgba(159,226,75,.09); }
.identity-kicker { color: var(--muted); font-size: .7rem; font-weight: 700; letter-spacing: .13em; }
.identity-card h2 { margin: 5px 0 2px; overflow-wrap: anywhere; font-family: "Barlow Condensed"; font-size: 1.85rem; font-weight: 600; line-height: 1; }
.identity-card > p { margin: 7px 0 12px; overflow: hidden; color: var(--muted); font-size: .78rem; text-overflow: ellipsis; white-space: nowrap; }
.role { padding: 5px 8px; display: inline-flex; color: var(--text-secondary); background: var(--surface-soft); border-radius: 6px; font-size: .68rem; }
.goal-readout { margin: 28px 0 21px; padding: 17px; display: flex; align-items: center; justify-content: space-between; background: linear-gradient(130deg, rgba(159,226,75,.12), rgba(159,226,75,.025)); border: 1px solid rgba(159,226,75,.18); border-radius: 12px; }
.goal-readout div { display: grid; gap: 2px; }
.goal-readout small { color: var(--muted); }
.goal-readout strong { font-family: "Barlow Condensed"; font-size: 1.45rem; font-weight: 600; }
.goal-readout svg { color: var(--primary); }
.weight-progress > div:first-child { display: flex; justify-content: space-between; color: var(--text-secondary); font-size: .75rem; }
.progress-track { height: 6px; margin: 9px 0 8px; overflow: hidden; background: var(--surface-soft); border-radius: 6px; }
.progress-track i { height: 100%; display: block; background: linear-gradient(90deg, var(--primary), var(--accent)); border-radius: inherit; }
.weight-progress small { color: var(--muted); font-size: .67rem; }
.identity-card dl { margin: 25px 0 0; padding-top: 12px; border-top: 1px solid var(--border); }
.identity-card dl > div { min-height: 46px; display: flex; align-items: center; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--border); }
.identity-card dl > div:last-child { border-bottom: 0; }
.identity-card dt { display: flex; align-items: center; gap: 7px; color: var(--muted); font-size: .72rem; }
.identity-card dd { margin: 0; max-width: 48%; overflow: hidden; color: var(--text-secondary); font-size: .74rem; text-overflow: ellipsis; white-space: nowrap; }
.goal-panel { grid-column: 2; padding: clamp(20px, 3vw, 34px); }
.panel-heading { margin-bottom: 5px; padding-bottom: 24px; display: flex; align-items: flex-end; justify-content: space-between; border-bottom: 1px solid var(--border); }
.panel-heading > div > span { display: block; margin-bottom: 5px; color: var(--primary); font-size: .7rem; font-weight: 700; letter-spacing: .13em; }
.step-mark { color: var(--muted); font-family: "Barlow Condensed"; font-size: 1rem; }
.goal-stepper { margin-top: 18px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.goal-stepper button { min-width: 0; min-height: 72px; padding: 10px 12px; display: flex; align-items: center; gap: 10px; color: var(--muted); text-align: left; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 11px; transition: color 180ms var(--ease-out), background 180ms var(--ease-out), border-color 180ms var(--ease-out); }
.goal-stepper button:hover { color: var(--text-secondary); border-color: var(--border-strong); }
.goal-stepper button:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.goal-stepper button.active { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.4); }
.goal-stepper button.complete:not(.active) { color: var(--text-secondary); }
.goal-stepper button > span:last-child { min-width: 0; display: grid; gap: 3px; }
.goal-stepper b { overflow: hidden; color: var(--text); font-size: .76rem; text-overflow: ellipsis; white-space: nowrap; }
.goal-stepper small { overflow: hidden; color: var(--muted); font-size: .64rem; text-overflow: ellipsis; white-space: nowrap; }
.goal-step-index { width: 30px; height: 30px; flex: 0 0 auto; display: grid; place-items: center; color: var(--text-secondary); background: var(--surface-soft); border-radius: 8px; font-family: "Barlow Condensed"; font-size: .78rem; font-weight: 700; }
.goal-stepper button.active .goal-step-index { color: #11160f; background: var(--primary); }
.goal-stepper button.complete:not(.active) .goal-step-index { color: var(--primary); background: var(--primary-soft); }
.goal-step-content { min-height: 390px; }
.form-section { padding: 26px 0; border-bottom: 1px solid var(--border); }
.section-label { margin-bottom: 18px; display: flex; gap: 13px; }
.section-label > span { width: 29px; height: 29px; display: grid; place-items: center; color: #11160f; background: var(--primary); border-radius: 8px; font-family: "Barlow Condensed"; font-weight: 700; }
.section-label h3 { margin: 0; font-size: .96rem; }
.section-label p { margin: 4px 0 0; color: var(--muted); font-size: .76rem; }
.mode-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.mode-grid button { min-height: 125px; padding: 17px; display: flex; flex-direction: column; align-items: flex-start; gap: 7px; color: var(--text-secondary); text-align: left; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 12px; transition: transform 180ms var(--ease-out), border-color 180ms var(--ease-out), background 180ms var(--ease-out); }
.mode-grid button:hover { border-color: var(--border-strong); transform: translateY(-2px); }
.mode-grid button.active { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.42); box-shadow: inset 0 -3px 0 var(--primary); }
.mode-grid button b { color: var(--text); }
.mode-grid button span { color: var(--muted); font-size: .7rem; line-height: 1.45; }
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 17px 14px; }
.select-field { display: grid; gap: 8px; color: var(--text-secondary); font-size: .86rem; font-weight: 500; }
.select-field select { width: 100%; min-height: 48px; padding: 0 13px; color: var(--text); color-scheme: dark; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 10px; outline: none; transition: border-color 180ms var(--ease-out), box-shadow 180ms var(--ease-out); }
.select-field select:focus { border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-soft); }
.training-days { margin-top: 22px; display: grid; gap: 10px; }
.training-days > span { display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: .84rem; font-weight: 500; }
.training-days > span svg { color: var(--primary); }
.training-days > div { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; }
.training-days button { min-height: 44px; color: var(--text-secondary); background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 9px; }
.training-days button:hover { border-color: var(--border-strong); }
.training-days button.active { color: #11160f; background: var(--primary); border-color: var(--primary); font-weight: 700; }
.training-days small { color: var(--muted); font-size: .72rem; }
.form-footer { padding-top: 23px; display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.local-note { max-width: 440px; display: flex; align-items: flex-start; gap: 9px; color: var(--muted); font-size: .72rem; line-height: 1.5; }
.local-note svg { flex: 0 0 auto; color: var(--primary); }
.local-note b { display: block; color: var(--text-secondary); }
.step-actions { margin-left: auto; display: flex; align-items: center; gap: 9px; }
.step-back { min-height: 48px; padding: 0 17px; color: var(--text-secondary); background: transparent; border: 1px solid var(--border-strong); border-radius: 10px; font-size: .8rem; font-weight: 600; transition: color 180ms var(--ease-out), background 180ms var(--ease-out), border-color 180ms var(--ease-out); }
.step-back:hover { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.3); }
.step-back:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.profile-feedback { min-height: 390px; display: grid; place-content: center; justify-items: center; gap: 11px; color: var(--primary); text-align: center; }
.profile-feedback p { max-width: 52ch; margin: 0; color: var(--muted); font-size: .78rem; line-height: 1.6; }
.profile-feedback.error { color: #ff938d; }
.profile-feedback button { min-height: 44px; margin-top: 5px; padding: 0 15px; color: #11160f; background: var(--primary); border: 1px solid var(--primary); border-radius: 9px; font-weight: 600; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
.spin { animation: spin 800ms linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  .spin { animation: none; }
  .avatar-actions button, .select-field select, .goal-stepper button, .step-back { transition: none; }
}
@media (max-width: 1040px) {
  .profile-grid { grid-template-columns: 1fr; }
  .identity-card { grid-row: auto; }
  .goal-panel { grid-column: 1; }
  .identity-card { display: grid; grid-template-columns: auto 1fr; column-gap: 24px; }
  .identity-top { grid-row: 1 / 5; display: block; }
  .account-state { margin-top: 16px; display: flex; }
  .goal-readout, .weight-progress, .identity-card dl { grid-column: 1 / -1; }
}
@media (max-width: 700px) {
  .page-header { min-height: 210px; align-items: flex-start; }
  .page-header .status-chip { display: none; }
  .goal-stepper { gap: 6px; }
  .goal-stepper button { min-height: 64px; padding: 8px; justify-content: center; }
  .goal-stepper button > span:last-child { display: block; }
  .goal-stepper small { display: none; }
  .goal-step-index { width: 27px; height: 27px; }
  .goal-step-content { min-height: 0; }
  .mode-grid { grid-template-columns: 1fr; }
  .mode-grid button { min-height: 88px; display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; column-gap: 12px; }
  .mode-grid button svg { grid-row: 1 / 3; }
  .field-grid { grid-template-columns: 1fr; }
  .form-footer { align-items: stretch; flex-direction: column; }
  .step-actions { width: 100%; margin-left: 0; }
  .step-actions > * { flex: 1; }
  .step-actions .fuel-button { width: 100%; }
}
@media (max-width: 460px) {
  .identity-card { display: block; }
  .identity-top { display: flex; }
  .account-state { margin-top: 0; }
  .training-days > div { gap: 5px; }
}
</style>
