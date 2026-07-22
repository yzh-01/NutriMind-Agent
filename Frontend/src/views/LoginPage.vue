<template>
  <AuthShell>
    <div class="auth-heading">
      <span>继续你的计划</span>
      <h2>欢迎回来</h2>
      <p>登录后进入与你身份对应的用户空间或管理控制台。</p>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" size="large" placeholder="请输入用户名" autocomplete="username" />
      </el-form-item>
      <el-form-item label="登录密码" prop="password">
        <el-input v-model="form.password" size="large" type="password" show-password placeholder="请输入登录密码" autocomplete="current-password" />
      </el-form-item>
      <FuelButton class="full-button" native-type="submit" :loading="loading">登录系统</FuelButton>
    </el-form>
    <p class="switch-copy">第一次使用 NutriMind？<router-link to="/register">创建账户</router-link></p>
  </AuthShell>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AuthShell from '@/components/AuthShell.vue'
import FuelButton from '@/components/ui/FuelButton.vue'
import { useUserStore } from '@/stores/user'

const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名' }, { min: 3, max: 50, message: '长度为 3-50 个字符' }],
  password: [{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少 6 位' }],
}
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

async function submit() {
  if (!await formRef.value.validate().catch(() => false)) return
  loading.value = true
  try {
    await userStore.login(form)
    ElMessage.success('登录成功')
    router.push(String(route.query.redirect || userStore.defaultRoute))
  } finally { loading.value = false }
}
</script>

<style lang="scss" scoped>
.auth-heading { margin-bottom: 30px; }
.auth-heading > span { color: var(--primary); font-size: .75rem; font-weight: 600; }
.auth-heading h2 { margin: 8px 0 8px; font-family: "Barlow Condensed", MiSans, sans-serif; font-size: 3rem; line-height: 1; font-weight: 600; }
.auth-heading p { margin: 0; color: var(--text-secondary); line-height: 1.65; }
.full-button { width: 100%; }
.switch-copy { margin: 28px 0 0; padding-top: 22px; color: var(--muted); border-top: 1px solid var(--border); text-align: center; font-size: .82rem; }
.switch-copy a { margin-left: 5px; color: var(--primary); font-weight: 600; }
</style>
