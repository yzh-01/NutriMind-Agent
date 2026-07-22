import { nextTick } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginPage.vue'), meta: { public: true, title: '登录' } },
    { path: '/register', name: 'register', component: () => import('@/views/RegisterPage.vue'), meta: { public: true, title: '注册' } },
    {
      path: '/app',
      component: () => import('@/layouts/UserLayout.vue'),
      redirect: '/app/coach',
      meta: { userOnly: true },
      children: [
        { path: 'coach', name: 'coach', component: () => import('@/views/ChatPage.vue'), meta: { title: 'AI 教练' } },
        { path: 'scan', name: 'scan', component: () => import('@/views/FoodScanPage.vue'), meta: { title: '食物照片' } },
        { path: 'library', name: 'library', component: () => import('@/views/KnowledgePage.vue'), meta: { title: '运动营养库' } },
        { path: 'profile', name: 'profile', component: () => import('@/views/ProfilePage.vue'), meta: { title: '身体与目标' } },
      ],
    },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      redirect: '/admin/dashboard',
      meta: { requiresAdmin: true },
      children: [
        { path: 'dashboard', name: 'admin-dashboard', component: () => import('@/views/admin/AdminDashboardPage.vue'), meta: { title: '系统看板' } },
        { path: 'users', name: 'admin-users', component: () => import('@/views/admin/AdminUsersPage.vue'), meta: { title: '用户管理' } },
        { path: 'detections', name: 'admin-detections', component: () => import('@/views/admin/AdminDetectionPage.vue'), meta: { title: '目标检测监控' } },
        { path: 'training', name: 'admin-training', component: () => import('@/views/admin/AdminTrainingPage.vue'), meta: { title: '模型训练' } },
      ],
    },
    { path: '/', redirect: '/app/coach' },
    { path: '/today', redirect: '/app/coach' },
    { path: '/coach', redirect: '/app/coach' },
    { path: '/scan', redirect: '/app/scan' },
    { path: '/library', redirect: '/app/library' },
    { path: '/profile', redirect: '/app/profile' },
    { path: '/chat', redirect: '/app/coach' },
    { path: '/knowledge', redirect: '/app/library' },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  document.title = `${to.meta.title || '首页'} - NutriMind`
  const userStore = useUserStore()

  await userStore.restoreSession()

  if (!to.meta.public && !userStore.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (userStore.isLoggedIn && !userStore.roleResolved) {
    try { await userStore.refreshUser() }
    catch {
      if (to.meta.requiresAdmin) return '/app/coach'
    }
  }

  if (to.meta.public && userStore.isLoggedIn) return userStore.defaultRoute
  if (to.meta.requiresAdmin && !userStore.isAdmin) return '/app/coach'
  if (to.meta.userOnly && userStore.isAdmin) return '/admin/dashboard'
})

router.afterEach(() => {
  nextTick(() => document.querySelector('#main-content')?.focus({ preventScroll: true }))
})

export default router
