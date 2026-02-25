<script setup lang="ts">
import { ref } from 'vue'
import { Check, Edit, RefreshRight } from '@element-plus/icons-vue'

defineProps<{
  step: string
  loading?: boolean
}>()

const emit = defineEmits<{
  approve: []
  edit: []
  retry: []
}>()

const actionLoading = ref('')

function handleApprove() {
  actionLoading.value = 'approve'
  emit('approve')
  setTimeout(() => { actionLoading.value = '' }, 300)
}
function handleEdit() {
  actionLoading.value = 'edit'
  emit('edit')
  setTimeout(() => { actionLoading.value = '' }, 300)
}
function handleRetry() {
  actionLoading.value = 'retry'
  emit('retry')
  setTimeout(() => { actionLoading.value = '' }, 300)
}
</script>

<template>
  <div class="step-actions">
    <div class="step-actions-hint">
      当前步骤 <strong>{{ step }}</strong> 已完成，请选择操作：
    </div>
    <div class="step-actions-buttons">
      <el-button
        type="primary"
        :icon="Check"
        :loading="loading || actionLoading === 'approve'"
        @click="handleApprove"
      >
        继续下一步
      </el-button>
      <el-button
        :icon="Edit"
        :loading="actionLoading === 'edit'"
        @click="handleEdit"
      >
        编辑后继续
      </el-button>
      <el-button
        :icon="RefreshRight"
        :loading="actionLoading === 'retry'"
        @click="handleRetry"
      >
        重新执行
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.step-actions {
  padding: 16px;
  border: 1px solid var(--el-color-primary-light-7, #a0cfff);
  border-radius: 8px;
  background: var(--el-color-primary-light-9, #ecf5ff);
}
.step-actions-hint {
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--el-text-color-regular, #606266);
}
.step-actions-buttons {
  display: flex;
  gap: 8px;
}
</style>
