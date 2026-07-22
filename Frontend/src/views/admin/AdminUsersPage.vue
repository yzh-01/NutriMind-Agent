<template>
  <div class="page-shell admin-users">
    <section v-if="isPreviewMode" class="preview-notice surface" role="status">
      <Flask :size="22" weight="duotone" />
      <div>
        <b>管理员界面预览</b>
        <p>以下是本地演示数据，不会请求后端；修改操作已禁用。</p>
      </div>
    </section>

    <header class="page-head">
      <div>
        <span class="status-chip"><Users :size="16" weight="bold" /> User Management API</span>
        <h1 class="page-title">账户清晰，权限可控。</h1>
        <p class="page-description">检索用户、查看账户详情，并维护启用状态、管理员身份和角色。</p>
      </div>
      <button class="primary-action" type="button" :disabled="loading" @click="loadUsers">
        <CircleNotch v-if="loading" class="spin" :size="18" weight="bold" />
        <ArrowsClockwise v-else :size="18" weight="bold" />
        {{ loading ? '正在刷新' : '刷新列表' }}
      </button>
    </header>

    <form class="filter-panel surface" role="search" @submit.prevent="applyFilters">
      <label class="search-field">
        <span>搜索用户</span>
        <div>
          <MagnifyingGlass :size="18" aria-hidden="true" />
          <input v-model="filters.search" type="search" placeholder="用户名、邮箱或手机号" autocomplete="off">
        </div>
      </label>
      <label>
        <span>账户状态</span>
        <select v-model="filters.isActive">
          <option value="">全部状态</option>
          <option value="true">已启用</option>
          <option value="false">已停用</option>
        </select>
      </label>
      <label>
        <span>管理员身份</span>
        <select v-model="filters.isSuperuser">
          <option value="">全部身份</option>
          <option value="true">管理员</option>
          <option value="false">普通用户</option>
        </select>
      </label>
      <div class="filter-actions">
        <button class="secondary-action" type="button" @click="resetFilters">重置</button>
        <button class="primary-action" type="submit">查询</button>
      </div>
    </form>

    <section class="list-panel surface" aria-labelledby="user-list-title">
      <header class="list-heading">
        <div>
          <span>账户目录</span>
          <h2 id="user-list-title" class="section-title">用户列表</h2>
        </div>
        <p aria-live="polite">共 <strong>{{ total }}</strong> 个匹配账户</p>
      </header>

      <div v-if="loading && !users.length" class="loading-list" aria-label="正在加载用户列表">
        <div v-for="index in 5" :key="index" class="loading-row" aria-hidden="true">
          <span class="skeleton skeleton-avatar" />
          <span class="skeleton skeleton-main" />
          <span class="skeleton skeleton-short" />
          <span class="skeleton skeleton-short" />
        </div>
      </div>

      <div v-else-if="loadError" class="feedback-state error-state" role="alert">
        <WarningCircle :size="38" weight="duotone" />
        <h3>用户列表暂时无法加载</h3>
        <p>{{ loadError }}</p>
        <button class="primary-action" type="button" @click="loadUsers">重新加载</button>
      </div>

      <div v-else-if="!users.length" class="feedback-state" role="status">
        <UserMinus :size="38" weight="duotone" />
        <h3>没有找到匹配用户</h3>
        <p>可以更换关键词或清除筛选条件后重新查询。</p>
        <button class="secondary-action" type="button" @click="resetFilters">清除筛选</button>
      </div>

      <template v-else>
        <div class="desktop-table">
          <table>
            <thead>
              <tr>
                <th scope="col">用户</th>
                <th scope="col">联系方式</th>
                <th scope="col">角色</th>
                <th scope="col">状态</th>
                <th scope="col">最近登录</th>
                <th scope="col"><span class="sr-only">操作</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.id">
                <td>
                  <div class="identity-cell">
                    <span class="avatar">{{ userInitial(user) }}</span>
                    <span><b>{{ user.username || '未命名用户' }}</b><small>ID {{ user.id ?? '--' }}</small></span>
                  </div>
                </td>
                <td><span class="contact-cell"><b>{{ user.email || '--' }}</b><small>{{ user.phone || '未填写手机号' }}</small></span></td>
                <td><div class="role-list"><span v-if="user.isSuperuser" class="role-tag admin">管理员</span><span v-for="role in user.roles" :key="role" class="role-tag">{{ role }}</span><span v-if="!user.roles.length && !user.isSuperuser" class="muted">--</span></div></td>
                <td><span class="state-tag" :class="stateClass(user.isActive)"><i />{{ stateLabel(user.isActive) }}</span></td>
                <td><time :datetime="user.lastLoginAt || undefined">{{ formatDate(user.lastLoginAt) }}</time></td>
                <td>
                  <div class="row-actions">
                    <button type="button" @click="openDetail(user)"><Eye :size="17" />详情</button>
                    <button type="button" :disabled="isPreviewMode" :title="isPreviewMode ? '预览模式不执行修改' : ''" @click="openPermission(user)"><ShieldCheck :size="17" />权限</button>
                    <button type="button" :class="{ danger: user.isActive }" :disabled="!canChangeStatus(user)" :title="actionDisabledReason(user, 'status')" @click="changeStatus(user)">
                      <LockOpen v-if="user.isActive === false" :size="17" />
                      <Lock v-else :size="17" />
                      {{ user.isActive === false ? '启用' : '停用' }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mobile-cards">
          <article v-for="user in users" :key="user.id" class="user-card">
            <header>
              <div class="identity-cell"><span class="avatar">{{ userInitial(user) }}</span><span><b>{{ user.username || '未命名用户' }}</b><small>{{ user.email || `ID ${user.id ?? '--'}` }}</small></span></div>
              <span class="state-tag" :class="stateClass(user.isActive)"><i />{{ stateLabel(user.isActive) }}</span>
            </header>
            <div class="role-list"><span v-if="user.isSuperuser" class="role-tag admin">管理员</span><span v-for="role in user.roles" :key="role" class="role-tag">{{ role }}</span><span v-if="!user.roles.length && !user.isSuperuser" class="muted">暂无角色</span></div>
            <dl><div><dt>手机号</dt><dd>{{ user.phone || '--' }}</dd></div><div><dt>最近登录</dt><dd>{{ formatDate(user.lastLoginAt) }}</dd></div></dl>
            <footer class="row-actions">
              <button type="button" @click="openDetail(user)"><Eye :size="17" />详情</button>
              <button type="button" :disabled="isPreviewMode" @click="openPermission(user)"><ShieldCheck :size="17" />权限</button>
              <button type="button" :class="{ danger: user.isActive }" :disabled="!canChangeStatus(user)" @click="changeStatus(user)"><Lock :size="17" />{{ user.isActive === false ? '启用' : '停用' }}</button>
            </footer>
          </article>
        </div>

        <footer class="pagination-bar">
          <label>每页<select v-model.number="pageSize" @change="changePageSize"><option :value="20">20</option><option :value="50">50</option><option :value="100">100</option></select>条</label>
          <span>第 {{ page }} / {{ totalPages }} 页</span>
          <div>
            <button type="button" :disabled="page <= 1 || loading" aria-label="上一页" @click="changePage(page - 1)"><CaretLeft :size="18" /></button>
            <button type="button" :disabled="page >= totalPages || loading" aria-label="下一页" @click="changePage(page + 1)"><CaretRight :size="18" /></button>
          </div>
        </footer>
      </template>
    </section>

    <el-dialog v-model="detailVisible" class="admin-user-dialog" width="min(680px, calc(100vw - 32px))" destroy-on-close append-to-body>
      <template #header><div class="dialog-title"><span><Eye :size="18" weight="bold" /></span><div><b>用户详情</b><small>账户资料与任务统计</small></div></div></template>
      <div v-if="detailLoading" class="dialog-loading"><CircleNotch class="spin" :size="28" /><span>正在读取用户详情</span></div>
      <div v-else-if="detailError" class="dialog-error" role="alert"><WarningCircle :size="24" /><span>{{ detailError }}</span><button type="button" @click="loadDetail(selectedUser.id)">重试</button></div>
      <div v-else-if="selectedUser" class="detail-content">
        <div class="detail-identity"><span class="avatar large">{{ userInitial(selectedUser) }}</span><div><h3>{{ selectedUser.username || '未命名用户' }}</h3><p>ID {{ selectedUser.id ?? '--' }}</p></div><span class="state-tag" :class="stateClass(selectedUser.isActive)"><i />{{ stateLabel(selectedUser.isActive) }}</span></div>
        <dl class="detail-grid">
          <div><dt>邮箱</dt><dd>{{ selectedUser.email || '--' }}</dd></div><div><dt>手机号</dt><dd>{{ selectedUser.phone || '--' }}</dd></div>
          <div><dt>管理员身份</dt><dd>{{ selectedUser.isSuperuser === null ? '--' : selectedUser.isSuperuser ? '是' : '否' }}</dd></div><div><dt>角色</dt><dd>{{ selectedUser.roles.join('、') || '--' }}</dd></div>
          <div><dt>创建时间</dt><dd>{{ formatDate(selectedUser.createdAt) }}</dd></div><div><dt>更新时间</dt><dd>{{ formatDate(selectedUser.updatedAt) }}</dd></div>
        </dl>
        <div class="task-stats"><article><Scan :size="22" weight="duotone" /><span><small>检测任务</small><b>{{ formatNumber(selectedUser.totalDetectionTasks) }}</b></span></article><article><Cpu :size="22" weight="duotone" /><span><small>训练任务</small><b>{{ formatNumber(selectedUser.totalTrainingTasks) }}</b></span></article></div>
      </div>
      <template #footer><button class="secondary-action" type="button" @click="detailVisible = false">关闭</button></template>
    </el-dialog>

    <el-dialog v-model="permissionVisible" class="admin-user-dialog" width="min(560px, calc(100vw - 32px))" destroy-on-close append-to-body>
      <template #header><div class="dialog-title"><span><ShieldCheck :size="18" weight="bold" /></span><div><b>编辑账户权限</b><small>{{ editUser?.username || '用户' }}</small></div></div></template>
      <div v-if="editUser" class="permission-form">
        <section>
          <div><label for="superuser-switch">管理员身份</label><p>管理员可以进入管理控制台并调用管理员接口。</p></div>
          <el-switch id="superuser-switch" v-model="editSuperuser" :disabled="isCurrentUser(editUser)" style="--el-switch-on-color: var(--primary); --el-switch-off-color: #3a423d" />
        </section>
        <p v-if="isCurrentUser(editUser)" class="inline-note"><Info :size="17" />后端不允许修改当前管理员自己的管理员身份。</p>
        <label class="role-editor">
          <span>角色名称</span>
          <textarea v-model="editRoles" rows="4" placeholder="例如：admin, nutrition_editor" />
          <small>使用逗号分隔。保存后将完整替换该用户现有角色；当前接口没有提供可选角色字典。</small>
        </label>
        <p v-if="permissionError" class="inline-error" role="alert"><WarningCircle :size="17" />{{ permissionError }}</p>
      </div>
      <template #footer><div class="dialog-actions"><button class="secondary-action" type="button" :disabled="permissionSaving" @click="permissionVisible = false">取消</button><button class="primary-action" type="button" :disabled="!canSavePermission" @click="savePermission"><CircleNotch v-if="permissionSaving" class="spin" :size="17" />{{ permissionSaving ? '正在保存' : '保存权限' }}</button></div></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  PhArrowsClockwise as ArrowsClockwise, PhCaretLeft as CaretLeft,
  PhCaretRight as CaretRight, PhCircleNotch as CircleNotch, PhCpu as Cpu,
  PhEye as Eye, PhFlask as Flask, PhInfo as Info, PhLock as Lock,
  PhLockOpen as LockOpen, PhMagnifyingGlass as MagnifyingGlass,
  PhScan as Scan, PhShieldCheck as ShieldCheck, PhUserMinus as UserMinus,
  PhUsers as Users, PhWarningCircle as WarningCircle,
} from '@phosphor-icons/vue'
import {
  getAdminUserDetailApi, getAdminUsersApi, updateAdminUserRolesApi,
  updateAdminUserStatusApi, updateAdminUserSuperuserApi,
} from '@/api/adminUsers'
import { useUserStore } from '@/stores/user'
import {
  normalizeAdminUserDetail, normalizeAdminUserList, parseRoleNames,
} from '@/utils/adminUserData'

const userStore = useUserStore()
const users = ref([])
const previewUsers = ref([])
const loading = ref(false)
const loadError = ref('')
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = ref({ search: '', isActive: '', isSuperuser: '' })
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const selectedUser = ref(null)
const permissionVisible = ref(false)
const permissionSaving = ref(false)
const permissionError = ref('')
const editUser = ref(null)
const editRoles = ref('')
const editOriginalRoles = ref('')
const editSuperuser = ref(false)
const editOriginalSuperuser = ref(false)
const isPreviewMode = computed(() => userStore.isAdminPreview)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const canSavePermission = computed(() => {
  if (!editUser.value || permissionSaving.value || isPreviewMode.value) return false
  return editRoles.value !== editOriginalRoles.value
    || (!isCurrentUser(editUser.value) && editSuperuser.value !== editOriginalSuperuser.value)
})

function buildParams() {
  const params = { page: page.value, page_size: pageSize.value }
  const search = filters.value.search.trim()
  if (search) params.search = search
  if (filters.value.isActive !== '') params.is_active = filters.value.isActive === 'true'
  if (filters.value.isSuperuser !== '') params.is_superuser = filters.value.isSuperuser === 'true'
  return params
}

function applyPreviewFilters() {
  const search = filters.value.search.trim().toLocaleLowerCase('zh-CN')
  const result = previewUsers.value.filter((user) => {
    const matchesSearch = !search || [user.username, user.email, user.phone]
      .some((value) => String(value || '').toLocaleLowerCase('zh-CN').includes(search))
    const matchesActive = filters.value.isActive === '' || user.isActive === (filters.value.isActive === 'true')
    const matchesAdmin = filters.value.isSuperuser === '' || user.isSuperuser === (filters.value.isSuperuser === 'true')
    return matchesSearch && matchesActive && matchesAdmin
  })
  total.value = result.length
  users.value = result.slice((page.value - 1) * pageSize.value, page.value * pageSize.value)
}

async function loadPreviewUsers() {
  if (!import.meta.env.DEV) return []
  const { adminUsersPreview } = await import('@/mocks/adminUsersPreview')
  return normalizeAdminUserList(adminUsersPreview).items
}

async function loadUsers() {
  loading.value = true
  loadError.value = ''
  try {
    if (isPreviewMode.value) {
      if (!previewUsers.value.length) {
        previewUsers.value = await loadPreviewUsers()
      }
      applyPreviewFilters()
    } else {
      const result = normalizeAdminUserList(await getAdminUsersApi(buildParams()))
      users.value = result.items
      total.value = result.total
      page.value = result.page
      pageSize.value = result.pageSize
    }
  } catch {
    loadError.value = '没有读取到用户管理 API 数据，请稍后重试。'
  } finally {
    loading.value = false
  }
}

function applyFilters() { page.value = 1; loadUsers() }
function resetFilters() { filters.value = { search: '', isActive: '', isSuperuser: '' }; page.value = 1; loadUsers() }
function changePage(nextPage) { page.value = nextPage; loadUsers() }
function changePageSize() { page.value = 1; loadUsers() }
function isCurrentUser(user) { return user?.id !== null && String(user.id) === String(userStore.user?.id) }
function canChangeStatus(user) { return !isPreviewMode.value && user.isActive !== null && !isCurrentUser(user) }
function actionDisabledReason(user) {
  if (isPreviewMode.value) return '预览模式不执行修改'
  if (isCurrentUser(user)) return '不能修改当前管理员自己的状态'
  if (user.isActive === null) return '接口未返回明确状态'
  return ''
}
function userInitial(user) { return (user?.username || '?').trim().slice(0, 1).toUpperCase() || '?' }
function stateLabel(value) { return value === null ? '未知' : value ? '已启用' : '已停用' }
function stateClass(value) { return value === null ? 'unknown' : value ? 'active' : 'disabled' }
function formatNumber(value) { return Number.isFinite(value) ? new Intl.NumberFormat('zh-CN').format(value) : '--' }
function formatDate(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(date)
}

async function loadDetail(userId) {
  detailLoading.value = true
  detailError.value = ''
  try {
    if (isPreviewMode.value) selectedUser.value = previewUsers.value.find((user) => String(user.id) === String(userId)) || selectedUser.value
    else selectedUser.value = normalizeAdminUserDetail(await getAdminUserDetailApi(userId))
  } catch {
    detailError.value = '用户详情接口暂时不可用，列表数据仍可继续查看。'
  } finally {
    detailLoading.value = false
  }
}

function openDetail(user) { selectedUser.value = user; detailVisible.value = true; loadDetail(user.id) }
function openPermission(user) {
  editUser.value = user
  editRoles.value = user.roles.join(', ')
  editOriginalRoles.value = editRoles.value
  editSuperuser.value = Boolean(user.isSuperuser)
  editOriginalSuperuser.value = editSuperuser.value
  permissionError.value = ''
  permissionVisible.value = true
}

async function changeStatus(user) {
  if (!canChangeStatus(user)) return
  const nextStatus = !user.isActive
  try {
    await ElMessageBox.confirm(
      `确定要${nextStatus ? '启用' : '停用'}用户“${user.username || user.id}”吗？`,
      `${nextStatus ? '启用' : '停用'}账户`,
      { confirmButtonText: '确认修改', cancelButtonText: '取消', type: nextStatus ? 'success' : 'warning' },
    )
    await updateAdminUserStatusApi(user.id, { is_active: nextStatus })
    ElMessage.success('账户状态已更新')
    await loadUsers()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('账户状态修改失败')
  }
}

async function savePermission() {
  if (!canSavePermission.value) return
  permissionSaving.value = true
  permissionError.value = ''
  const roles = parseRoleNames(editRoles.value)
  try {
    if (editRoles.value !== editOriginalRoles.value) {
      await updateAdminUserRolesApi(editUser.value.id, { role_names: roles })
    }
    if (!isCurrentUser(editUser.value) && editSuperuser.value !== editOriginalSuperuser.value) {
      await updateAdminUserSuperuserApi(editUser.value.id, { is_superuser: editSuperuser.value })
    }
    ElMessage.success('账户权限已更新')
    permissionVisible.value = false
    await loadUsers()
  } catch {
    permissionError.value = '权限保存失败。如果同时修改了角色和管理员身份，前一项可能已经生效，请刷新列表确认。'
  } finally {
    permissionSaving.value = false
  }
}

onMounted(loadUsers)
</script>

<style lang="scss" scoped>
.admin-users { padding-bottom: 36px; }
.preview-notice { margin-bottom: 18px; padding: 13px 15px; display: flex; align-items: center; gap: 11px; color: var(--primary); border-color: rgba(159, 226, 75, .24); }
.preview-notice div { display: grid; gap: 2px; }
.preview-notice b { color: var(--text); font-size: .8rem; }
.preview-notice p { margin: 0; color: var(--muted); font-size: .7rem; }
.page-head { margin-bottom: 22px; display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; }
.page-head .status-chip { margin-bottom: 15px; }
.primary-action, .secondary-action { min-height: 44px; padding: 0 15px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; border-radius: 9px; font-weight: 600; transition: transform 160ms var(--ease-out), background 160ms var(--ease-out), border-color 160ms var(--ease-out); }
.primary-action { color: #11160f; background: var(--primary); border: 1px solid var(--primary); }
.primary-action:hover:not(:disabled) { background: var(--primary-hover); }
.secondary-action { color: var(--text-secondary); background: var(--surface-soft); border: 1px solid var(--border); }
.secondary-action:hover:not(:disabled) { color: var(--text); border-color: rgba(159, 226, 75, .3); }
.primary-action:active:not(:disabled), .secondary-action:active:not(:disabled) { transform: scale(.98); }
.primary-action:disabled, .secondary-action:disabled { opacity: .5; }
.filter-panel { margin-bottom: 12px; padding: 16px; display: grid; grid-template-columns: minmax(240px, 1.6fr) repeat(2, minmax(150px, .7fr)) auto; align-items: end; gap: 10px; }
.filter-panel label, .role-editor { display: grid; gap: 7px; color: var(--muted); font-size: .7rem; font-weight: 600; }
.filter-panel input, .filter-panel select, .pagination-bar select, .role-editor textarea { min-height: 44px; width: 100%; padding: 0 12px; color: var(--text); background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 9px; outline: none; }
.filter-panel input:focus, .filter-panel select:focus, .pagination-bar select:focus, .role-editor textarea:focus { border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-soft); }
.filter-panel select, .pagination-bar select { color-scheme: dark; }
.search-field > div { position: relative; }
.search-field svg { position: absolute; top: 13px; left: 12px; color: var(--muted); pointer-events: none; }
.search-field input { padding-left: 39px; }
.filter-actions { display: flex; gap: 8px; }
.list-panel { min-height: 480px; padding: 20px; }
.list-heading { margin-bottom: 15px; display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; }
.list-heading > div > span { color: var(--primary); font-size: .7rem; font-weight: 600; }
.list-heading h2 { margin-top: 4px; }
.list-heading p { margin: 0; color: var(--muted); font-size: .72rem; }
.list-heading strong { color: var(--text); font-variant-numeric: tabular-nums; }
.desktop-table { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th { padding: 11px 12px; color: var(--muted); border-bottom: 1px solid var(--border); font-size: .68rem; font-weight: 600; letter-spacing: .02em; text-align: left; }
td { padding: 14px 12px; color: var(--text-secondary); border-bottom: 1px solid rgba(255,255,255,.055); font-size: .74rem; vertical-align: middle; }
tbody tr { transition: background 160ms var(--ease-out); }
tbody tr:hover { background: rgba(255,255,255,.018); }
tbody tr:last-child td { border-bottom: 0; }
.identity-cell { min-width: 170px; display: flex; align-items: center; gap: 10px; }
.avatar { width: 38px; height: 38px; flex: 0 0 auto; display: grid; place-items: center; color: #11160f; background: var(--primary); border-radius: 10px; font-weight: 700; }
.avatar.large { width: 52px; height: 52px; border-radius: 13px; font-size: 1.05rem; }
.identity-cell > span:last-child, .contact-cell { display: grid; gap: 3px; }
.identity-cell b, .contact-cell b { max-width: 210px; overflow: hidden; color: var(--text); font-size: .76rem; text-overflow: ellipsis; white-space: nowrap; }
.identity-cell small, .contact-cell small { color: var(--muted); font-size: .65rem; }
.role-list { max-width: 260px; display: flex; flex-wrap: wrap; gap: 5px; }
.role-tag { padding: 4px 7px; color: var(--text-secondary); background: var(--surface-soft); border: 1px solid var(--border); border-radius: 6px; font-size: .62rem; }
.role-tag.admin { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.18); }
.muted { color: var(--muted); }
.state-tag { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; font-size: .68rem; }
.state-tag i { width: 7px; height: 7px; background: currentColor; border-radius: 50%; box-shadow: 0 0 0 4px color-mix(in srgb, currentColor 12%, transparent); }
.state-tag.active { color: var(--primary); }
.state-tag.disabled { color: #ff938d; }
.state-tag.unknown { color: var(--muted); }
time { color: var(--muted); white-space: nowrap; font-variant-numeric: tabular-nums; }
.row-actions { display: flex; justify-content: flex-end; gap: 5px; }
.row-actions button { min-height: 38px; padding: 0 8px; display: inline-flex; align-items: center; gap: 5px; color: var(--text-secondary); background: transparent; border: 1px solid transparent; border-radius: 8px; font-size: .67rem; font-weight: 600; white-space: nowrap; }
.row-actions button:hover:not(:disabled) { color: var(--primary); background: var(--primary-soft); border-color: rgba(159,226,75,.16); }
.row-actions button.danger:hover:not(:disabled) { color: #ff938d; background: rgba(240,103,95,.08); border-color: rgba(240,103,95,.18); }
.row-actions button:disabled { opacity: .34; }
.mobile-cards { display: none; }
.pagination-bar { margin-top: 14px; padding-top: 14px; display: flex; align-items: center; justify-content: flex-end; gap: 18px; color: var(--muted); border-top: 1px solid var(--border); font-size: .68rem; }
.pagination-bar label { display: flex; align-items: center; gap: 6px; }
.pagination-bar select { min-height: 38px; width: 72px; }
.pagination-bar > div { display: flex; gap: 6px; }
.pagination-bar button { width: 40px; height: 40px; display: grid; place-items: center; color: var(--text-secondary); background: var(--surface-soft); border: 1px solid var(--border); border-radius: 8px; }
.pagination-bar button:hover:not(:disabled) { color: var(--primary); border-color: rgba(159,226,75,.28); }
.pagination-bar button:disabled { opacity: .35; }
.feedback-state { min-height: 350px; display: grid; place-content: center; justify-items: center; color: var(--muted); text-align: center; }
.feedback-state h3 { margin: 13px 0 5px; color: var(--text); font-family: "Barlow Condensed"; font-size: 1.6rem; }
.feedback-state p { max-width: 46ch; margin: 0 0 18px; color: var(--muted); line-height: 1.6; }
.error-state { color: var(--danger); }
.loading-list { display: grid; }
.loading-row { min-height: 72px; padding: 12px; display: grid; grid-template-columns: 40px 1.2fr .7fr .5fr; align-items: center; gap: 12px; border-bottom: 1px solid var(--border); }
.skeleton { height: 14px; background: linear-gradient(100deg, var(--surface-soft) 20%, var(--surface-raised) 36%, var(--surface-soft) 52%); background-size: 200% 100%; border-radius: 6px; animation: shimmer 1.35s linear infinite; }
.skeleton-avatar { width: 38px; height: 38px; border-radius: 10px; }
.skeleton-main { width: 70%; }
.skeleton-short { width: 58%; }
.spin { animation: spin 800ms linear infinite; }
@keyframes shimmer { to { background-position-x: -200%; } }
@keyframes spin { to { transform: rotate(360deg); } }

:global(.admin-user-dialog.el-dialog) { --el-dialog-bg-color: var(--surface); overflow: hidden; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); }
:global(.admin-user-dialog .el-dialog__header) { margin: 0; padding: 18px 20px; border-bottom: 1px solid var(--border); }
:global(.admin-user-dialog .el-dialog__headerbtn) { top: 15px; right: 14px; width: 44px; height: 44px; }
:global(.admin-user-dialog .el-dialog__close) { color: var(--muted); }
:global(.admin-user-dialog .el-dialog__body) { padding: 20px; color: var(--text-secondary); }
:global(.admin-user-dialog .el-dialog__footer) { padding: 0 20px 20px; }
.dialog-title { display: flex; align-items: center; gap: 10px; }
.dialog-title > span { width: 36px; height: 36px; display: grid; place-items: center; color: var(--primary); background: var(--primary-soft); border-radius: 9px; }
.dialog-title > div { display: grid; gap: 2px; }
.dialog-title b { color: var(--text); font-size: .82rem; }
.dialog-title small { color: var(--muted); font-size: .68rem; }
.dialog-loading { min-height: 240px; display: grid; place-content: center; justify-items: center; gap: 10px; color: var(--primary); }
.dialog-loading span { color: var(--muted); font-size: .72rem; }
.dialog-error { min-height: 180px; display: flex; align-items: center; justify-content: center; gap: 9px; color: var(--danger); }
.dialog-error button { color: var(--primary); background: transparent; border: 0; text-decoration: underline; }
.detail-identity { padding: 14px; display: flex; align-items: center; gap: 12px; background: var(--canvas-soft); border-radius: 12px; }
.detail-identity > div { min-width: 0; flex: 1; }
.detail-identity h3 { margin: 0; color: var(--text); font-family: "Barlow Condensed"; font-size: 1.45rem; }
.detail-identity p { margin: 3px 0 0; color: var(--muted); font-size: .68rem; }
.detail-grid { margin: 16px 0; display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 1px; overflow: hidden; background: var(--border); border: 1px solid var(--border); border-radius: 11px; }
.detail-grid > div { min-height: 72px; padding: 13px; display: grid; align-content: center; gap: 5px; background: var(--surface); }
.detail-grid dt, .task-stats small { color: var(--muted); font-size: .65rem; }
.detail-grid dd { margin: 0; overflow-wrap: anywhere; color: var(--text-secondary); font-size: .75rem; }
.task-stats { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px; }
.task-stats article { min-height: 84px; padding: 14px; display: flex; align-items: center; gap: 12px; color: var(--primary); background: var(--canvas-soft); border-radius: 11px; }
.task-stats span { display: grid; gap: 3px; }
.task-stats b { color: var(--text); font-family: "Barlow Condensed"; font-size: 1.55rem; line-height: 1; }
.permission-form { display: grid; gap: 16px; }
.permission-form > section { padding: 14px; display: flex; align-items: center; justify-content: space-between; gap: 20px; background: var(--canvas-soft); border-radius: 11px; }
.permission-form label { color: var(--text); font-size: .78rem; font-weight: 600; }
.permission-form section p { margin: 4px 0 0; color: var(--muted); font-size: .68rem; line-height: 1.5; }
.role-editor textarea { min-height: 102px; padding: 11px 12px; resize: vertical; line-height: 1.6; }
.role-editor small { color: var(--muted); font-size: .66rem; font-weight: 400; line-height: 1.55; }
.inline-note, .inline-error { margin: -6px 0 0; padding: 10px 12px; display: flex; align-items: flex-start; gap: 8px; border-radius: 8px; font-size: .68rem; line-height: 1.5; }
.inline-note { color: var(--text-secondary); background: var(--surface-soft); }
.inline-error { color: #ff938d; background: rgba(240,103,95,.08); }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }

@media (prefers-reduced-motion: reduce) { .skeleton, .spin { animation: none; } .primary-action, .secondary-action, tbody tr { transition: none; } }
@media (max-width: 1040px) { .filter-panel { grid-template-columns: 1.4fr repeat(2, minmax(135px,.7fr)); } .filter-actions { grid-column: 1 / -1; justify-content: flex-end; } }
@media (max-width: 760px) {
  .page-head { align-items: stretch; flex-direction: column; }
  .page-head > .primary-action { width: 100%; }
  .filter-panel { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .search-field { grid-column: 1 / -1; }
  .filter-actions { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); }
  .desktop-table { display: none; }
  .mobile-cards { display: grid; gap: 8px; }
  .user-card { padding: 14px; background: var(--canvas-soft); border: 1px solid var(--border); border-radius: 12px; }
  .user-card > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
  .user-card .role-list { margin: 13px 0; max-width: none; }
  .user-card dl { margin: 0; display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px; }
  .user-card dl div { display: grid; gap: 3px; }
  .user-card dt { color: var(--muted); font-size: .62rem; }
  .user-card dd { margin: 0; color: var(--text-secondary); font-size: .7rem; overflow-wrap: anywhere; }
  .user-card footer { margin-top: 13px; padding-top: 10px; display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); border-top: 1px solid var(--border); }
  .user-card footer button { min-height: 42px; justify-content: center; }
  .pagination-bar { justify-content: space-between; flex-wrap: wrap; gap: 10px; }
}
@media (max-width: 520px) {
  .preview-notice { align-items: flex-start; }
  .filter-panel, .list-panel { padding: 14px; }
  .filter-panel { grid-template-columns: 1fr; }
  .search-field, .filter-actions { grid-column: auto; }
  .list-heading { align-items: flex-start; flex-direction: column; }
  .detail-grid, .task-stats { grid-template-columns: 1fr; }
  .detail-identity { align-items: flex-start; flex-wrap: wrap; }
  .detail-identity .state-tag { margin-left: 64px; }
  .pagination-bar > span { order: 3; width: 100%; text-align: center; }
}
</style>
