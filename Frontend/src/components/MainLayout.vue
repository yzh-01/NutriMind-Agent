<template>
  <div class="app-layout" :class="[{ 'rail-hidden': railHidden }, `mode-${mode}`]">
    <a class="skip-link" href="#main-content">跳到主要内容</a>

    <aside id="app-navigation" class="app-rail" aria-label="主导航">
      <router-link class="brand" :to="brandTarget" :aria-label="brandLabel">
        <Lightning :size="23" weight="fill" aria-hidden="true" />
        <span>NM</span>
      </router-link>

      <nav>
        <router-link v-for="item in navItems" :key="item.path" :to="item.path">
          <component :is="item.icon" :size="22" :weight="route.path === item.path ? 'fill' : 'regular'" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <button v-if="!isAdminLayout" class="rail-profile" aria-label="打开个人资料" @click="router.push('/app/profile')">
        <img v-if="visibleAvatarUrl" :src="visibleAvatarUrl" :alt="`${userStore.username || '用户'}的头像`" @error="handleAvatarError">
        <span v-else aria-hidden="true">{{ userInitial }}</span>
      </button>
      <span v-else class="rail-role" aria-label="管理员空间">AD</span>
    </aside>

    <button
      class="rail-toggle"
      type="button"
      aria-controls="app-navigation"
      :aria-expanded="!railHidden"
      :aria-label="railHidden ? '显示侧边栏' : '隐藏侧边栏'"
      :title="railHidden ? '显示侧边栏' : '隐藏侧边栏'"
      @click="toggleRail"
    >
      <SidebarSimple :size="20" :weight="railHidden ? 'regular' : 'fill'" aria-hidden="true" />
    </button>

    <section class="app-stage">
      <header class="topbar">
        <div class="wordmark">
          <b>NutriMind</b>
          <span>{{ route.meta.title }}</span>
        </div>
        <div class="top-actions">
          <span class="service-state" :class="serviceStatus">
            <component :is="serviceIcon" :size="17" weight="bold" />
            {{ serviceLabel }}
          </span>
          <el-dropdown trigger="click" @command="handleCommand" @visible-change="accountMenuOpen = $event">
            <button class="account-button" aria-label="打开账户菜单" aria-haspopup="menu" :aria-expanded="accountMenuOpen">
              <span class="account-avatar">
                <img v-if="visibleAvatarUrl" :src="visibleAvatarUrl" :alt="`${userStore.username || '用户'}的头像`" @error="handleAvatarError">
                <span v-else aria-hidden="true">{{ userInitial }}</span>
              </span>
              <div><b>{{ userStore.username }}</b><small>{{ isAdminLayout ? 'Admin Console' : 'Performance Fuel' }}</small></div>
              <CaretDown :size="15" weight="bold" />
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="!isAdminLayout" command="profile"><UserCircle :size="17" />身体与目标</el-dropdown-item>
                <el-dropdown-item command="password"><LockKey :size="17" />修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided><SignOut :size="17" />退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main id="main-content" tabindex="-1">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in"><component :is="Component" /></transition>
        </router-view>
      </main>
    </section>
    <ChangePasswordDialog v-model="passwordDialogVisible" :is-demo="userStore.isDemo" />
  </div>
</template>

<script setup>
import { computed, markRaw, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  PhBarbell as Barbell, PhBookOpenText as BookOpenText, PhCaretDown as CaretDown,
  PhCloudCheck as CloudCheck, PhCloudX as CloudX,
  PhCpu as Cpu, PhGauge as Gauge,
  PhLightning as Lightning, PhLockKey as LockKey,
  PhScan as Scan, PhScanSmiley as ScanSmiley, PhSignOut as SignOut, PhSparkle as Sparkle,
  PhSidebarSimple as SidebarSimple, PhUserCircle as UserCircle, PhUsers as Users,
} from '@phosphor-icons/vue'
import { useUserStore } from '@/stores/user'
import { getHealthApi } from '@/api/system'
import ChangePasswordDialog from '@/components/account/ChangePasswordDialog.vue'

const SIDEBAR_KEY = 'nutrimind_sidebar_hidden'

const props = defineProps({
  mode: { type: String, default: 'user', validator: (value) => ['user', 'admin'].includes(value) },
})

function readSidebarPreference() {
  try { return localStorage.getItem(SIDEBAR_KEY) === 'true' }
  catch { return false }
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const mode = computed(() => props.mode)
const isAdminLayout = computed(() => props.mode === 'admin')
const serviceStatus = ref(userStore.isDemo ? 'preview' : 'checking')
const railHidden = ref(readSidebarPreference())
const avatarLoadFailed = ref(false)
const accountMenuOpen = ref(false)
const passwordDialogVisible = ref(false)
const userNavItems = [
  { path: '/app/coach', label: '教练', icon: markRaw(Sparkle) },
  { path: '/app/scan', label: '照片', icon: markRaw(ScanSmiley) },
  { path: '/app/library', label: '营养库', icon: markRaw(BookOpenText) },
  { path: '/app/profile', label: '目标', icon: markRaw(Barbell) },
]
const adminNavItems = [
  { path: '/admin/dashboard', label: '总览', icon: markRaw(Gauge) },
  { path: '/admin/users', label: '用户', icon: markRaw(Users) },
  { path: '/admin/detections', label: '检测', icon: markRaw(Scan) },
  { path: '/admin/training', label: '训练', icon: markRaw(Cpu) },
]
const navItems = computed(() => isAdminLayout.value ? adminNavItems : userNavItems)
const brandTarget = computed(() => isAdminLayout.value ? '/admin/dashboard' : '/app/coach')
const brandLabel = computed(() => isAdminLayout.value ? 'NutriMind 管理控制台' : 'NutriMind 用户空间')
const userInitial = computed(() => userStore.username.slice(0, 1).toUpperCase() || 'N')
const visibleAvatarUrl = computed(() => avatarLoadFailed.value ? '' : userStore.avatarUrl)
const serviceLabel = computed(() => ({
  preview: '预览数据', checking: '检查服务', online: '服务在线', offline: '服务离线',
})[serviceStatus.value])
const serviceIcon = computed(() => serviceStatus.value === 'offline' ? CloudX : CloudCheck)

watch(() => userStore.avatarUrl, () => { avatarLoadFailed.value = false })

onMounted(() => {
  checkHealth()
})

async function checkHealth() {
  if (userStore.isDemo) {
    serviceStatus.value = 'preview'
    return
  }
  serviceStatus.value = 'checking'
  try {
    const health = await getHealthApi()
    serviceStatus.value = health?.status === 'ok' ? 'online' : 'offline'
  } catch {
    serviceStatus.value = 'offline'
  }
}

function handleAvatarError() {
  avatarLoadFailed.value = true
}

function toggleRail() {
  railHidden.value = !railHidden.value
  try { localStorage.setItem(SIDEBAR_KEY, String(railHidden.value)) }
  catch { /* The preference remains active for the current page. */ }
}

async function handleCommand(command) {
  if (command === 'profile') router.push('/app/profile')
  if (command === 'password') passwordDialogVisible.value = true
  if (command === 'logout') {
    await userStore.logout()
    router.push('/login')
  }
}
</script>

<style lang="scss" scoped>
.app-layout { min-height: 100dvh; display: flex; }
.app-rail {
  position: fixed;
  z-index: var(--z-nav);
  inset: 18px auto 18px 18px;
  width: 92px;
  padding: 12px 9px;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(20, 25, 21, .94);
  border: 1px solid var(--border);
  border-radius: 20px;
  box-shadow: $shadow;
  backdrop-filter: blur(18px);
  transition: opacity 220ms var(--ease-out), transform 260ms var(--ease-out);
}
.rail-toggle {
  position: fixed;
  z-index: calc(var(--z-nav) + 1);
  top: 25px;
  left: 120px;
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  color: var(--text-secondary);
  background: rgba(20, 25, 21, .94);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(14px);
  transition: left 260ms var(--ease-out), color 180ms var(--ease-out), border-color 180ms var(--ease-out);
}
.rail-toggle:hover { color: var(--primary); border-color: rgba(159, 226, 75, .35); }
.app-layout.rail-hidden .app-rail { opacity: 0; transform: translateX(-130%); pointer-events: none; }
.app-layout.rail-hidden .rail-toggle { left: 18px; }
.brand {
  width: 58px;
  height: 58px;
  display: grid;
  place-items: center;
  color: #11160f;
  background: var(--primary);
  border-radius: 15px;
}
.brand span { font-family: "Barlow Condensed"; font-size: .68rem; font-weight: 700; line-height: 1; }
.app-rail nav { width: 100%; margin: auto 0; display: grid; gap: 8px; }
.app-rail nav a {
  min-height: 58px;
  padding: 7px 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: var(--muted);
  border-radius: 13px;
  font-size: .7rem;
  transition: color 180ms var(--ease-out), background 180ms var(--ease-out), transform 180ms var(--ease-out);
}
.app-rail nav a:hover { color: var(--text); background: rgba(255,255,255,.04); transform: translateY(-1px); }
.app-rail nav a.router-link-active { color: var(--primary); background: var(--primary-soft); }
.rail-profile { width: 46px; height: 46px; padding: 0; overflow: hidden; display: grid; place-items: center; color: var(--text); background: var(--surface-soft); border: 1px solid var(--border); border-radius: 12px; font-weight: 600; }
.rail-profile img { width: 100%; height: 100%; object-fit: cover; }
.rail-role { width: 46px; height: 46px; display: grid; place-items: center; color: var(--primary); background: var(--primary-soft); border: 1px solid rgba(159, 226, 75, .18); border-radius: 12px; font-family: "Barlow Condensed"; font-size: .74rem; font-weight: 700; }
.app-stage { min-width: 0; flex: 1; margin-left: 128px; transition: margin-left 260ms var(--ease-out); }
.app-layout.rail-hidden .app-stage { margin-left: 18px; }
.topbar { height: 78px; padding: 0 30px 0 52px; display: flex; align-items: center; justify-content: space-between; }
.wordmark { display: flex; align-items: baseline; gap: 10px; }
.wordmark b { font-family: "Barlow Condensed"; font-size: 1.15rem; letter-spacing: .01em; }
.wordmark span { color: var(--muted); font-size: .78rem; }
.top-actions { display: flex; align-items: center; gap: 16px; }
.service-state { min-height: 36px; padding: 0 11px; display: inline-flex; align-items: center; gap: 7px; color: var(--primary); background: var(--primary-soft); border-radius: 8px; font-size: .75rem; }
.service-state.checking { color: var(--text-secondary); background: var(--surface); }
.service-state.offline { color: #ff938d; background: rgba(240, 103, 95, .1); }
.account-button { min-height: 48px; padding: 4px 7px; display: flex; align-items: center; gap: 9px; color: var(--text); background: transparent; border: 1px solid transparent; border-radius: 11px; }
.account-button:hover { background: var(--surface); border-color: var(--border); }
.account-avatar { width: 36px; height: 36px; overflow: hidden; display: grid; place-items: center; color: #12170f; background: var(--primary); border-radius: 9px; font-weight: 700; }
.account-avatar img { width: 100%; height: 100%; object-fit: cover; }
.account-button div { min-width: 106px; display: grid; gap: 1px; text-align: left; }
.account-button b { max-width: 130px; overflow: hidden; font-size: .8rem; text-overflow: ellipsis; white-space: nowrap; }
.account-button small { color: var(--muted); font-size: .7rem; }
main { min-height: calc(100dvh - 78px); padding: 8px 30px 34px 4px; outline: none; }
.page-enter-active, .page-leave-active { transition: opacity 180ms var(--ease-out), transform 220ms var(--ease-out); }
.page-enter-from { opacity: 0; transform: translateY(10px); }
.page-leave-to { opacity: 0; transform: translateY(-6px); }

@media (max-width: 900px) {
  .app-stage, .app-layout.rail-hidden .app-stage { margin-left: 0; }
  .app-rail { inset: auto 12px max(12px, env(safe-area-inset-bottom)) 12px; width: auto; height: 70px; padding: 7px 10px; flex-direction: row; }
  .app-layout.rail-hidden .app-rail { opacity: 1; transform: none; pointer-events: auto; }
  .rail-toggle { display: none; }
  .brand, .rail-profile, .rail-role { display: none; }
  .app-rail nav { margin: 0; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; }
  .app-rail nav a { min-height: 54px; min-width: 58px; padding: 5px 9px; font-size: .65rem; }
  .topbar { padding: 0 18px; }
  main { padding: 8px 16px 100px; }
  .mode-admin .app-rail nav { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .mode-admin main { padding-bottom: 100px; }
}
@media (max-width: 620px) {
  .service-state, .account-button div, .wordmark span { display: none; }
  .top-actions { gap: 4px; }
  .app-rail nav a { min-width: 0; padding-inline: 5px; }
}
</style>
