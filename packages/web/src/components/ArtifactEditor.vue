<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  data: Record<string, unknown>
  artifactType: string
  readonly?: boolean
}>()

const emit = defineEmits<{
  save: [data: Record<string, unknown>]
}>()

const jsonText = ref('')
const isValid = ref(true)

const title = computed(() => {
  const map: Record<string, string> = {
    paper_summary: '论文摘要',
    video_script: '视频脚本',
    audio: '音频文件',
  }
  return map[props.artifactType] || props.artifactType
})

watch(
  () => props.data,
  (val) => {
    jsonText.value = JSON.stringify(val, null, 2)
    isValid.value = true
  },
  { immediate: true },
)

function onInput() {
  try {
    JSON.parse(jsonText.value)
    isValid.value = true
  } catch {
    isValid.value = false
  }
}

function save() {
  try {
    const parsed = JSON.parse(jsonText.value)
    emit('save', parsed)
  } catch {
    ElMessage.error('JSON 格式错误，请修正后再保存')
  }
}
</script>

<template>
  <div class="artifact-editor">
    <div class="editor-header">
      <span class="editor-title">{{ title }}</span>
      <el-tag v-if="!isValid" type="danger" size="small">JSON 格式错误</el-tag>
      <el-tag v-else type="success" size="small">格式正确</el-tag>
    </div>
    <el-input
      v-model="jsonText"
      type="textarea"
      :autosize="{ minRows: 10, maxRows: 30 }"
      :readonly="readonly"
      class="editor-textarea"
      @input="onInput"
    />
    <div v-if="!readonly" class="editor-actions">
      <el-button type="primary" :disabled="!isValid" @click="save">
        保存修改
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.artifact-editor {
  border: 1px solid var(--el-border-color-lighter, #e4e7ed);
  border-radius: 8px;
  padding: 16px;
  background: var(--el-bg-color, #fff);
}
.editor-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.editor-title {
  font-weight: 600;
  font-size: 14px;
}
.editor-textarea :deep(.el-textarea__inner) {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.6;
}
.editor-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
