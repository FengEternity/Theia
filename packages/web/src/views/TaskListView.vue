<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listTasks, deleteTask, retryTask, getThumbnailUrl } from '@/api/client'
import type { TaskResponse, TaskStage } from '@/api/types'

const router = useRouter()
const tasks = ref<TaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const initialLoad = ref(true)
let pollTimer: ReturnType<typeof setInterval> | null = null

const stageTagType: Record<TaskStage, string> = {
  pending: 'info',
  parsing: '',
  extracting: '',
  scripting: '',
  tts: '',
  rendering: 'warning',
  completed: 'success',
  failed: 'danger',
}

async function fetchTasks() {
  loading.value = true
  try {
    const res = await listTasks({ page: page.value, size: pageSize.value })
    tasks.value = res.items
    total.value = res.total
  } catch {
    // ignore
  } finally {
    loading.value = false
    initialLoad.value = false
  }
}

async function handleDelete(task: TaskResponse) {
  try {
    await ElMessageBox.confirm(`确认删除任务 "${task.filename}" 吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteTask(task.id)
    ElMessage.success('已删除')
    fetchTasks()
  } catch {
    // cancelled
  }
}

async function handleRetry(task: TaskResponse) {
  try {
    await retryTask(task.id)
    ElMessage.success('任务已重新开始')
    fetchTasks()
  } catch {
    ElMessage.error('重试失败')
  }
}

function goDetail(task: TaskResponse) {
  router.push(`/tasks/${task.id}`)
}

function formatDate(iso: string) {
  const s = iso.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + 'Z'
  return new Date(s).toLocaleString('zh-CN')
}

function onPageChange(p: number) {
  page.value = p
  fetchTasks()
}

function onSizeChange(s: number) {
  pageSize.value = s
  page.value = 1
  fetchTasks()
}

onMounted(() => {
  fetchTasks()
  pollTimer = setInterval(fetchTasks, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="task-list-view">
    <div class="list-header">
      <h2>任务列表</h2>
      <el-button type="primary" @click="router.push('/')">上传新论文</el-button>
    </div>

    <div class="list-card">
      <!-- 骨架屏 -->
      <div v-if="initialLoad" class="skeleton-list">
        <div v-for="n in 4" :key="n" class="skeleton-row">
          <div class="skeleton-cell wide"><div class="skeleton-bar" /></div>
          <div class="skeleton-cell"><div class="skeleton-bar short" /></div>
          <div class="skeleton-cell"><div class="skeleton-bar" /></div>
          <div class="skeleton-cell"><div class="skeleton-bar short" /></div>
        </div>
      </div>

      <el-table v-else :data="tasks" v-loading="loading" empty-text="暂无任务" stripe style="width: 100%">
        <el-table-column label="" width="72">
          <template #default="{ row }">
            <div class="thumb-cell" @click="goDetail(row)">
              <img
                v-if="row.thumbnail_path"
                :src="getThumbnailUrl(row.id)"
                class="thumb-img"
                loading="lazy"
                alt="缩略图"
              />
              <div v-else class="thumb-placeholder">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#cbd5e1" stroke-width="1.5">
                  <rect x="2" y="4" width="20" height="16" rx="2" />
                  <polygon points="10,9 16,12 10,15" fill="#cbd5e1" stroke="none" />
                </svg>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="文件名" min-width="200">
          <template #default="{ row }">
            <div>
              <span class="clickable" @click="goDetail(row)">{{ row.filename }}</span>
              <p v-if="row.paper_title" class="paper-title">{{ row.paper_title }}</p>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="stageTagType[row.stage as TaskStage] as any" size="small" effect="light">
              {{ row.stage_label }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="进度" width="120">
          <template #default="{ row }">
            <el-progress
              v-if="row.progress >= 0"
              :percentage="row.progress"
              :stroke-width="6"
              :show-text="true"
              :status="row.stage === 'completed' ? 'success' : row.stage === 'failed' ? 'exception' : undefined"
            />
            <span v-else style="color: #ef4444; font-size: 13px;">失败</span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            <span style="font-size: 13px; color: #6b7280;">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button text type="primary" size="small" @click="goDetail(row)">详情</el-button>
              <el-button v-if="row.stage === 'failed' || row.stage === 'completed'" text type="warning" size="small" @click="handleRetry(row)">重试</el-button>
              <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="onPageChange"
          @size-change="onSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.task-list-view {
  max-width: 960px;
  margin: 0 auto;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.list-header h2 {
  font-size: 22px;
  font-weight: 700;
}

.list-card {
  background: #fff;
  border-radius: 12px;
  padding: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.clickable {
  cursor: pointer;
  color: #6366f1;
  font-weight: 500;
}

.clickable:hover {
  text-decoration: underline;
}

.thumb-cell {
  cursor: pointer;
  width: 48px;
  height: 36px;
  border-radius: 4px;
  overflow: hidden;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.6;
}

.paper-title {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 0;
  flex-wrap: nowrap;
}

.action-buttons .el-button + .el-button {
  margin-left: 0;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 16px 0 12px;
}

/* Skeleton */
.skeleton-list {
  padding: 16px;
}

.skeleton-row {
  display: flex;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid #f3f4f6;
}

.skeleton-row:last-child {
  border-bottom: none;
}

.skeleton-cell {
  flex: 1;
}

.skeleton-cell.wide {
  flex: 2.5;
}

.skeleton-bar {
  height: 14px;
  background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
  width: 80%;
}

.skeleton-bar.short {
  width: 50%;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
