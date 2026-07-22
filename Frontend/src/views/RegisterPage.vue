<template>
  <AuthShell>
    <div class="auth-heading">
      <span>建立 Performance Fuel 账户</span>
      <h2>从今天开始</h2>
      <p>创建账户，之后可以继续完善身体目标和饮食偏好。</p>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
      <el-form-item label="用户名" prop="username"><el-input v-model="form.username" size="large" placeholder="3-50 个字符" autocomplete="username" /></el-form-item>
      <el-form-item label="电子邮箱" prop="email"><el-input v-model="form.email" size="large" type="email" placeholder="name@example.com" autocomplete="email" /></el-form-item>
      <el-form-item label="登录密码" prop="password"><el-input v-model="form.password" size="large" type="password" show-password placeholder="至少 6 位" autocomplete="new-password" /></el-form-item>
      <FuelButton class="full-button" native-type="submit" :loading="loading">创建账户</FuelButton>
    </el-form>
    <p class="agreement">注册表示你同意平台使用规范和隐私政策。</p>
    <p class="switch-copy">已经有账户？<router-link to="/login">返回登录</router-link></p>
  </AuthShell>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AuthShell from '@/components/AuthShell.vue'
import FuelButton from '@/components/ui/FuelButton.vue'
import { registerApi } from '@/api/auth'

const formRef = ref()
const loading = ref(false)
const router = useRouter()
const form = reactive({ username: '', email: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名' }, { min: 3, max: 50, message: '长度为 3-50 个字符' }],
  email: [{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }],
  password: [{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少 6 位' }],
}

async function submit() {
  if (!await formRef.value.validate().catch(() => false)) return
  loading.value = true
  try {
    await registerApi(form)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } finally { loading.value = false }
}
</script>

<style lang="scss" scoped>
.auth-heading { margin-bottom: 26px; }
.auth-heading > span { color: var(--primary); font-size: .75rem; font-weight: 600; }
.auth-heading h2 { margin: 8px 0; font-family: "Barlow Condensed", MiSans, sans-serif; font-size: 3rem; line-height: 1; font-weight: 600; }
.auth-heading p { margin: 0; color: var(--text-secondary); line-height: 1.65; }
.full-button { width: 100%; }
.agreement { margin: 15px 0 0; color: var(--muted); font-size: .72rem; text-align: center; }
.switch-copy { margin: 22px 0 0; padding-top: 20px; color: var(--muted); border-top: 1px solid var(--border); text-align: center; font-size: .82rem; }
.switch-copy a { margin-left: 5px; color: var(--primary); font-weight: 600; }
</style>
