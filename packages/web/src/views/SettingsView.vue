<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listUsers,
  createUser,
  getUserSettings,
  updateUserSetting,
  getPresets,
} from '@/api/client'
import type { UserResponse, UserSettingResponse, PresetInfo } from '@/api/types'

const users = ref<UserResponse[]>([])
const selectedUserId = ref('default')
const settings = ref<UserSettingResponse[]>([])
const presets = ref<PresetInfo[]>([])
const loading = ref(false)

const showCreateDialog = ref(false)
const newUserName = ref('')
const newUserEmail = ref('')

const defaultPreset = ref('landscape')
const defaultLanguage = ref('zh')

async function fetchUsers() {
  loading.value = true
  try {
    users.value = await listUsers()
  } finally {
    loading.value = false
  }
}

async function fetchSettings() {
  try {
    settings.value = await getUserSettings(selectedUserId.value)
    const presetSetting = settings.value.find((s) => s.key === 'default_preset')
    if (presetSetting) defaultPreset.value = presetSetting.value
    const langSetting = settings.value.find((s) => s.key === 'default_language')
    if (langSetting) defaultLanguage.value = langSetting.value
  } catch {
    settings.value = []
  }
}

async function onUserChange(userId: string) {
  selectedUserId.value = userId
  await fetchSettings()
}

async function handleCreateUser() {
  if (!newUserName.value.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  try {
    const user = await createUser(newUserName.value.trim(), newUserEmail.value.trim() || undefined)
    ElMessage.success('用户已创建')
    showCreateDialog.value = false
    newUserName.value = ''
    newUserEmail.value = ''
    await fetchUsers()
    selectedUserId.value = user.id
    await fetchSettings()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  }
}

async function savePreset() {
  try {
    await updateUserSetting(selectedUserId.value, 'default_preset', defaultPreset.value)
    ElMessage.success('默认尺寸已保存')
  } catch {
    ElMessage.error('保存失败')
  }
}

async function saveLanguage() {
  try {
    await updateUserSetting(selectedUserId.value, 'default_language', defaultLanguage.value)
    ElMessage.success('默认语言已保存')
  } catch {
    ElMessage.error('保存失败')
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(async () => {
  await Promise.all([fetchUsers(), getPresets().then((p) => (presets.value = p))])
  await fetchSettings()
})
</script>

<template>
  <div class="settings-view">
    <h2>系统设置</h2>

    <!-- 用户管理 -->
    <div class="card">
      <div class="card-header">
        <h3>用户管理</h3>
        <el-button type="primary" size="small" @click="showCreateDialog = true">新建用户</el-button>
      </div>

      <el-form label-position="top">
        <el-form-item label="当前用户">
          <el-select v-model="selectedUserId" style="width: 100%" @change="onUserChange">
            <el-option
              v-for="u in users"
              :key="u.id"
              :label="u.name"
              :value="u.id"
            >
              <span>{{ u.name }}</span>
              <span v-if="u.email" style="color: #999; margin-left: 8px; font-size: 12px;">{{ u.email }}</span>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>

      <el-table :data="users" v-loading="loading" stripe size="small" style="width: 100%">
        <el-table-column prop="name" label="用户名" />
        <el-table-column prop="email" label="邮箱">
          <template #default="{ row }">
            {{ row.email || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            <span style="font-size: 12px; color: #9ca3af;">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 默认配置 -->
    <div class="card">
      <h3>默认配置</h3>
      <p class="card-desc">为用户 "{{ users.find(u => u.id === selectedUserId)?.name || selectedUserId }}" 设置默认参数</p>

      <el-form label-position="top" style="max-width: 400px; margin-top: 16px;">
        <el-form-item label="默认视频尺寸">
          <div style="display: flex; gap: 8px; width: 100%;">
            <el-select v-model="defaultPreset" style="flex: 1;">
              <el-option
                v-for="p in presets"
                :key="p.key"
                :label="p.label"
                :value="p.key"
              />
            </el-select>
            <el-button type="primary" @click="savePreset">保存</el-button>
          </div>
        </el-form-item>

        <el-form-item label="默认旁白语言">
          <div style="display: flex; gap: 8px; width: 100%;">
            <el-select v-model="defaultLanguage" style="flex: 1;">
              <el-option label="中文" value="zh" />
              <el-option label="English" value="en" />
              <el-option label="自动检测" value="auto" />
            </el-select>
            <el-button type="primary" @click="saveLanguage">保存</el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <!-- 新建用户对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建用户" width="420px">
      <el-form label-position="top">
        <el-form-item label="用户名" required>
          <el-input v-model="newUserName" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱（可选）">
          <el-input v-model="newUserEmail" placeholder="请输入邮箱" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateUser">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 720px;
  margin: 0 auto;
}

.settings-view > h2 {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 24px;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card h3 {
  font-size: 16px;
  font-weight: 600;
}

.card-desc {
  font-size: 13px;
  color: #9ca3af;
  margin-top: 4px;
}
</style>
