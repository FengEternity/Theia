<script setup lang="ts">
import { ref, computed } from 'vue'
import { Check, Edit, RefreshRight, Tools } from '@element-plus/icons-vue'

const props = defineProps<{
  step: string
  stepKey?: string
  loading?: boolean
}>()

const emit = defineEmits<{
  approve: []
  edit: []
  retry: []
  repair: []
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
function handleRepair() {
  actionLoading.value = 'repair'
  emit('repair')
  setTimeout(() => { actionLoading.value = '' }, 300)
}

const isExtractStep = computed(() => props.stepKey === 'extract' || props.step === '信息提取')
const isQualityGateStep = computed(() => props.stepKey === 'quality_gate' || props.step === '质量门控')
</script>

<template>
  <div class="step-actions">
    <div class="step-actions-hint">
      <template v-if="isQualityGateStep">
        质量检测已完成，请选择是否进行 AI 修复：
      </template>
      <template v-else>
        当前步骤 <strong>{{ step }}</strong> 已完成，请选择操作：
      </template>
    </div>
    <div class="step-actions-buttons">
      <template v-if="isQualityGateStep">
        <el-button
          type="primary"
          :icon="Tools"
          :loading="loading || actionLoading === 'repair'"
          @click="handleRepair"
        >
          开始 AI 修复
        </el-button>
        <el-button
          :icon="Check"
          :loading="actionLoading === 'approve'"
          @click="handleApprove"
        >
          跳过修复，继续
        </el-button>
      </template>
      <template v-else>
        <el-button
          type="primary"
          :icon="Check"
          :loading="loading || actionLoading === 'approve'"
          @click="handleApprove"
        >
          继续
        </el-button>
        <el-button
          :icon="Edit"
          :loading="actionLoading === 'edit'"
          @click="handleEdit"
        >
          {{ isExtractStep ? '查看并编辑数据' : '编辑后继续' }}
        </el-button>
        <el-button
          :icon="RefreshRight"
          :loading="actionLoading === 'retry'"
          @click="handleRetry"
        >
          重新执行
        </el-button>
      </template>
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
