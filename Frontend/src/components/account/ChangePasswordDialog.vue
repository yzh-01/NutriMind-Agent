<template>
  <el-dialog
    v-model="visible"
    class="password-dialog"
    width="min(520px, calc(100vw - 32px))"
    append-to-body
    destroy-on-close
    :close-on-click-modal="!passwordSaving"
    :close-on-press-escape="!passwordSaving"
    :show-close="!passwordSaving"
    :before-close="beforeClose"
    @opened="focusCurrentPassword"
    @closed="resetForm"
  >
    <template #header="{ titleId, titleClass }">
      <div class="dialog-heading">
        <span class="dialog-icon" aria-hidden="true"><LockKey :size="22" weight="bold" /></span>
        <div>
          <small>ACCOUNT SECURITY</small>
          <h2 :id="titleId" :class="titleClass">修改登录密码</h2>
        </div>
      </div>
    </template>

    <p class="dialog-copy">验证当前密码后设置新密码，新密码至少需要 6 位。</p>
    <el-form
      id="change-password-form"
      ref="passwordFormRef"
      :model="passwordForm"
      :rules="passwordRules"
      label-position="top"
      @submit.prevent="changePassword"
    >
      <el-form-item label="当前密码" prop="old_password">
        <el-input
          ref="currentPasswordInput"
          v-model="passwordForm.old_password"
          type="password"
          size="large"
          show-password
          autocomplete="current-password"
          placeholder="输入当前密码"
        />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input
          v-model="passwordForm.new_password"
          type="password"
          size="large"
          show-password
          autocomplete="new-password"
          placeholder="至少 6 位"
        />
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirm_password">
        <el-input
          v-model="passwordForm.confirm_password"
          type="password"
          size="large"
          show-password
          autocomplete="new-password"
          placeholder="再次输入新密码"
        />
      </el-form-item>

      <p v-if="submitError" class="submit-error" role="alert">
        <WarningCircle :size="18" weight="fill" />{{ submitError }}
      </p>
      <p class="privacy-note">
        <ShieldCheck :size="18" weight="duotone" />
        {{ isDemo ? '体验模式没有真实账户，不能修改密码。' : '密码仅用于本次验证，不会保存在浏览器本地。' }}
      </p>
    </el-form>

    <template #footer>
      <div class="dialog-actions">
        <FuelButton variant="secondary" :arrow="false" :disabled="passwordSaving" @click="closeDialog">取消</FuelButton>
        <FuelButton native-type="submit" form="change-password-form" :arrow="false" :loading="passwordSaving" :disabled="isDemo">确认修改</FuelButton>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  PhLockKey as LockKey, PhShieldCheck as ShieldCheck, PhWarningCircle as WarningCircle,
} from '@phosphor-icons/vue'
import FuelButton from '@/components/ui/FuelButton.vue'
import { changePasswordApi } from '@/api/auth'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  isDemo: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const passwordSaving = ref(false)
const passwordFormRef = ref()
const currentPasswordInput = ref()
const submitError = ref('')
const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const passwordRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value === passwordForm.new_password) callback()
        else callback(new Error('两次输入的新密码不一致'))
      },
      trigger: 'blur',
    },
  ],
}

const visible = computed({
  get: () => props.modelValue,
  set: (value) => {
    if (!value && passwordSaving.value) return
    emit('update:modelValue', value)
  },
})

function focusCurrentPassword() {
  nextTick(() => currentPasswordInput.value?.focus())
}

function resetForm() {
  Object.assign(passwordForm, { old_password: '', new_password: '', confirm_password: '' })
  submitError.value = ''
  nextTick(() => passwordFormRef.value?.clearValidate())
}

function closeDialog() {
  if (!passwordSaving.value) visible.value = false
}

function beforeClose(done) {
  if (!passwordSaving.value) done()
}

async function changePassword() {
  if (props.isDemo) {
    ElMessage.warning('体验模式不能修改密码')
    return
  }
  if (!await passwordFormRef.value?.validate().catch(() => false)) return

  passwordSaving.value = true
  submitError.value = ''
  try {
    await changePasswordApi({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    }, { silent: true })
    ElMessage.success('密码修改成功')
    emit('update:modelValue', false)
  } catch (error) {
    const detail = error.response?.data?.detail
    submitError.value = typeof detail === 'string' ? detail : '密码修改失败，请确认当前密码后重试。'
  } finally {
    passwordSaving.value = false
  }
}
</script>

<style lang="scss" scoped>
.dialog-heading { display: flex; align-items: center; gap: 13px; }
.dialog-icon { width: 44px; height: 44px; flex: 0 0 auto; display: grid; place-items: center; color: #11160f; background: var(--primary); border-radius: 11px; }
.dialog-heading small { display: block; margin-bottom: 3px; color: var(--primary); font-size: .68rem; font-weight: 700; letter-spacing: .13em; }
.dialog-heading h2 { margin: 0; color: var(--text); font-family: "Barlow Condensed", MiSans, sans-serif; font-size: 1.65rem; font-weight: 600; line-height: 1; }
.dialog-copy { margin: 0 0 20px; color: var(--muted); font-size: .8rem; line-height: 1.65; }
.privacy-note, .submit-error { margin: 2px 0 0; display: flex; align-items: flex-start; gap: 8px; font-size: .75rem; line-height: 1.55; }
.privacy-note { color: var(--muted); }
.privacy-note svg { flex: 0 0 auto; color: var(--primary); }
.submit-error { margin-bottom: 12px; color: #ff938d; }
.submit-error svg { flex: 0 0 auto; margin-top: 1px; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 9px; }

:global(.password-dialog.el-dialog) { --el-dialog-bg-color: var(--surface); overflow: hidden; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow-lg); }
:global(.password-dialog .el-dialog__header) { margin: 0; padding: 20px 22px 17px; border-bottom: 1px solid var(--border); }
:global(.password-dialog .el-dialog__headerbtn) { top: 17px; right: 16px; width: 44px; height: 44px; }
:global(.password-dialog .el-dialog__close) { color: var(--muted); }
:global(.password-dialog .el-dialog__body) { padding: 22px; color: var(--text-secondary); }
:global(.password-dialog .el-dialog__footer) { padding: 0 22px 22px; }
:global(.password-dialog .el-form-item) { margin-bottom: 17px; }
:global(.password-dialog .el-form-item__label) { color: var(--text-secondary); font-weight: 500; }
:global(.password-dialog .el-input__wrapper) { min-height: 48px; background: var(--canvas-soft); box-shadow: 0 0 0 1px var(--border) inset; }
:global(.password-dialog .el-input__wrapper:hover) { box-shadow: 0 0 0 1px var(--border-strong) inset; }
:global(.password-dialog .el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px var(--primary) inset, 0 0 0 3px var(--primary-soft); }
:global(.password-dialog .el-input__inner) { color: var(--text); }

@media (max-width: 520px) {
  .dialog-actions { align-items: stretch; flex-direction: column-reverse; }
  .dialog-actions .fuel-button { width: 100%; }
  :global(.password-dialog .el-dialog__header) { padding-inline: 18px; }
  :global(.password-dialog .el-dialog__body) { padding: 20px 18px; }
  :global(.password-dialog .el-dialog__footer) { padding: 0 18px 18px; }
}
</style>
