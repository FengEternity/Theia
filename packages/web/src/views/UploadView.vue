<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled, Link, VideoPlay, VideoPause, ArrowRight } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import { createTask, createTaskFromUrl, getPresets, getVoices, getVoicePreviewUrl, getUserSettings } from '@/api/client'
import type { PresetInfo, TaskConfig, VoiceInfo } from '@/api/types'

const router = useRouter()

const presets = ref<PresetInfo[]>([])
const voices = ref<VoiceInfo[]>([])
const selectedFile = ref<File | null>(null)
const fileName = ref('')
const submitting = ref(false)
const isDragOver = ref(false)

const uploadMode = ref<'file' | 'url'>('file')
const pdfUrl = ref('')

const config = ref<TaskConfig>({
  preset: 'landscape',
  language: 'zh',
  fps: 30,
  skip_tts: false,
  voice: null,
  speech_rate: 0,
  narration_style: 'academic',
  theme: 'academic',
  extract_mode: 'multi_pass',
})

const THEME_NARRATION_MAP: Record<string, string> = {
  academic: 'academic',
  popsci: 'popsci',
}
watch(() => config.value.theme, (newTheme) => {
  const mapped = THEME_NARRATION_MAP[newTheme]
  if (mapped) {
    config.value.narration_style = mapped
  }
})

const playingVoice = ref<string | null>(null)
let previewAudio: HTMLAudioElement | null = null

const LANG_LABELS: Record<string, string> = {
  zh: '中文',
  en: 'English',
  ja: '日本語',
}

const voiceGroups = computed(() => {
  const lang = config.value.language === 'auto' ? null : config.value.language
  const groups: { label: string; lang: string; voices: VoiceInfo[] }[] = []
  const langSet = new Set<string>()

  for (const v of voices.value) {
    langSet.add(v.language)
  }

  const sortedLangs = [...langSet].sort((a, b) => {
    if (a === lang) return -1
    if (b === lang) return 1
    return 0
  })

  for (const l of sortedLangs) {
    const langVoices = voices.value.filter(v => v.language === l)
    if (langVoices.length > 0) {
      const suffix = l === lang ? '（推荐）' : ''
      groups.push({
        label: (LANG_LABELS[l] || l) + suffix,
        lang: l,
        voices: langVoices,
      })
    }
  }
  return groups
})

const hasVoices = computed(() => voices.value.length > 0)

function playPreview(voiceId: string) {
  if (previewAudio) {
    previewAudio.pause()
    previewAudio = null
  }

  if (playingVoice.value === voiceId) {
    playingVoice.value = null
    return
  }

  playingVoice.value = voiceId
  previewAudio = new Audio(getVoicePreviewUrl(voiceId, config.value.speech_rate))
  previewAudio.play()
  previewAudio.addEventListener('ended', () => {
    playingVoice.value = null
    previewAudio = null
  })
  previewAudio.addEventListener('error', () => {
    ElMessage.warning('预览音频加载失败')
    playingVoice.value = null
    previewAudio = null
  })
}

onBeforeUnmount(() => {
  if (previewAudio) {
    previewAudio.pause()
    previewAudio = null
  }
})

onMounted(async () => {
  try {
    presets.value = await getPresets()
  } catch {
    presets.value = [
      { key: 'landscape', label: '横屏 16:9', width: 1920, height: 1080 },
      { key: 'portrait', label: '竖屏 9:16', width: 1080, height: 1920 },
      { key: 'square', label: '正方形 1:1', width: 1080, height: 1080 },
    ]
  }
  try {
    voices.value = await getVoices()
  } catch {
    voices.value = []
  }
  try {
    const settings = await getUserSettings('default')
    const presetSetting = settings.find((s: any) => s.key === 'default_preset')
    if (presetSetting) config.value.preset = presetSetting.value
    const langSetting = settings.find((s: any) => s.key === 'default_language')
    if (langSetting) config.value.language = langSetting.value
  } catch {
    // use built-in defaults
  }
})

const MAX_FILE_SIZE = 100 * 1024 * 1024

function onFileChange(uploadFile: UploadFile) {
  if (uploadFile.raw) {
    if (uploadFile.raw.size > MAX_FILE_SIZE) {
      ElMessage.warning(`文件过大（${(uploadFile.raw.size / 1024 / 1024).toFixed(1)} MB），最大支持 100 MB`)
      return
    }
    selectedFile.value = uploadFile.raw
    fileName.value = uploadFile.name
  }
}

function onDrop(e: DragEvent) {
  isDragOver.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    const f = files[0]
    if (f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')) {
      if (f.size > MAX_FILE_SIZE) {
        ElMessage.warning(`文件过大（${(f.size / 1024 / 1024).toFixed(1)} MB），最大支持 100 MB`)
        return
      }
      selectedFile.value = f
      fileName.value = f.name
    } else {
      ElMessage.warning('请上传 PDF 文件')
    }
  }
}

function clearFile() {
  selectedFile.value = null
  fileName.value = ''
}

async function submit() {
  if (uploadMode.value === 'file' && !selectedFile.value) {
    ElMessage.warning('请先选择 PDF 文件')
    return
  }
  if (uploadMode.value === 'url' && !pdfUrl.value.trim()) {
    ElMessage.warning('请输入链接（支持 PDF、微信公众号、知乎文章）')
    return
  }

  submitting.value = true
  try {
    let task
    if (uploadMode.value === 'url') {
      task = await createTaskFromUrl(pdfUrl.value.trim(), config.value)
    } else {
      task = await createTask(selectedFile.value!, config.value)
    }
    ElMessage.success('任务已创建')
    router.push(`/tasks/${task.id}`)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建任务失败')
  } finally {
    submitting.value = false
  }
}

function hasInput() {
  return uploadMode.value === 'file' ? !!selectedFile.value : !!pdfUrl.value.trim()
}

function selectedPresetInfo() {
  return presets.value.find(p => p.key === config.value.preset)
}
</script>

<template>
  <div class="upload-view">
    <!-- Hero -->
    <div class="hero">
      <h1>内容视频生成</h1>
      <p class="subtitle">上传 PDF 或粘贴文章链接，AI 自动提取内容并生成讲解视频</p>
    </div>

    <!-- 流程步骤指示 -->
    <div class="steps-bar">
      <div class="step active">
        <span class="step-num">1</span>
        <span class="step-label">上传内容</span>
      </div>
      <span class="step-arrow"><el-icon><ArrowRight /></el-icon></span>
      <div class="step">
        <span class="step-num">2</span>
        <span class="step-label">配置参数</span>
      </div>
      <span class="step-arrow"><el-icon><ArrowRight /></el-icon></span>
      <div class="step">
        <span class="step-num">3</span>
        <span class="step-label">生成视频</span>
      </div>
    </div>

    <div class="main-grid">
      <!-- 左侧：上传区域 -->
      <div class="panel upload-panel">
        <div class="panel-header">
          <h2>上传内容</h2>
          <div class="mode-tabs">
            <button
              class="mode-tab"
              :class="{ active: uploadMode === 'file' }"
              @click="uploadMode = 'file'"
            >
              <el-icon :size="14"><UploadFilled /></el-icon>
              文件
            </button>
            <button
              class="mode-tab"
              :class="{ active: uploadMode === 'url' }"
              @click="uploadMode = 'url'"
            >
              <el-icon :size="14"><Link /></el-icon>
              链接
            </button>
          </div>
        </div>

        <!-- 文件上传模式 -->
        <template v-if="uploadMode === 'file'">
          <div
            v-if="!selectedFile"
            class="drop-zone"
            :class="{ 'drag-over': isDragOver }"
            @dragover.prevent="isDragOver = true"
            @dragleave="isDragOver = false"
            @drop.prevent="onDrop"
          >
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              accept=".pdf"
              @change="onFileChange"
            >
              <div class="drop-content">
                <div class="drop-icon-wrap">
                  <el-icon :size="32" color="#6366f1"><UploadFilled /></el-icon>
                </div>
                <p class="drop-title">点击或拖拽上传 PDF</p>
                <p class="drop-hint">支持学术论文、技术报告等 PDF 文件，或切换到「链接」模式粘贴文章 URL</p>
              </div>
            </el-upload>
          </div>

          <div v-else class="file-selected">
            <div class="file-info">
              <div class="file-icon-wrap">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="14 2 14 8 20 8" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><line x1="9" y1="15" x2="15" y2="15" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round"/></svg>
              </div>
              <div>
                <p class="file-name">{{ fileName }}</p>
                <p class="file-size">{{ (selectedFile.size / 1024 / 1024).toFixed(2) }} MB</p>
              </div>
            </div>
            <button class="remove-btn" @click="clearFile">移除</button>
          </div>
        </template>

        <!-- 链接解析模式 -->
        <div v-else class="url-zone">
          <div class="drop-icon-wrap" style="margin-bottom: 12px;">
            <el-icon :size="32" color="#6366f1"><Link /></el-icon>
          </div>
          <el-input
            v-model="pdfUrl"
            placeholder="粘贴链接，支持 PDF、微信公众号、知乎文章"
            size="large"
            clearable
            class="url-input"
          />
          <p class="drop-hint">支持 arXiv PDF 直链、微信公众号文章、知乎专栏文章</p>
        </div>
      </div>

      <!-- 右侧：配置面板 -->
      <div class="panel config-panel">
        <div class="panel-header">
          <h2>生成配置</h2>
        </div>

        <el-form label-position="top" class="config-form">
          <el-form-item label="视频尺寸">
            <el-select v-model="config.preset" style="width: 100%">
              <el-option
                v-for="p in presets"
                :key="p.key"
                :label="p.label"
                :value="p.key"
              >
                <span>{{ p.label }}</span>
                <span style="color: #999; float: right; font-size: 12px;">{{ p.width }}x{{ p.height }}</span>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="旁白语言">
            <el-select v-model="config.language" style="width: 100%">
              <el-option label="中文" value="zh" />
              <el-option label="English" value="en" />
              <el-option label="日本語" value="ja" />
              <el-option label="自动检测" value="auto" />
            </el-select>
          </el-form-item>

          <el-form-item label="视频风格">
            <el-radio-group v-model="config.theme" style="width: 100%">
              <el-radio-button value="academic">学术严谨</el-radio-button>
              <el-radio-button value="popsci">科普卡通</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="旁白风格">
            <el-select v-model="config.narration_style" style="width: 100%">
              <el-option label="默认口语化" value="default" />
              <el-option label="学术严谨" value="academic" />
              <el-option label="故事叙述" value="story" />
              <el-option label="科普趣味" value="popsci" />
            </el-select>
          </el-form-item>


          <el-form-item label="提取模式">
            <el-radio-group v-model="config.extract_mode">
              <el-radio-button value="multi_pass">多轮提取（质量高）</el-radio-button>
              <el-radio-button value="single">单轮提取（速度快）</el-radio-button>
            </el-radio-group>
            <span class="form-hint">单轮提取约快 3-5 倍，但提取质量略低</span>
          </el-form-item>

          <el-form-item label="逐步模式">
            <el-switch
              v-model="config.interactive_mode"
              active-text="开启"
              inactive-text="关闭"
              :active-value="true"
              :inactive-value="false"
            />
            <span class="form-hint">开启后每步完成会暂停，可审核编辑中间结果</span>
          </el-form-item>

          <el-form-item label="语音合成">
            <el-switch
              v-model="config.skip_tts"
              active-text="跳过"
              inactive-text="生成"
              :active-value="true"
              :inactive-value="false"
            />
          </el-form-item>

          <el-form-item v-show="!config.skip_tts" label="语速调节">
            <div class="speech-rate-row">
              <el-slider
                v-model="config.speech_rate"
                :min="-50"
                :max="100"
                :step="5"
                :marks="{ '-50': '慢', 0: '默认', 50: '快', 100: '极快' }"
                style="flex: 1"
              />
              <span class="speech-rate-label">{{ config.speech_rate >= 0 ? '+' : '' }}{{ config.speech_rate }}%</span>
            </div>
          </el-form-item>

          <el-form-item v-show="!config.skip_tts && hasVoices" label="旁白声音">
              <div class="voice-row">
                <el-select
                  v-model="config.voice"
                  placeholder="自动匹配"
                  clearable
                  style="flex: 1"
                >
                  <el-option-group
                    v-for="group in voiceGroups"
                    :key="group.lang"
                    :label="group.label"
                  >
                    <el-option
                      v-for="v in group.voices"
                      :key="v.id"
                      :label="`${v.name}（${v.gender === 'male' ? '男' : '女'}）`"
                      :value="v.id"
                    >
                      <span>{{ v.name }}</span>
                      <span style="color: #999; float: right; font-size: 12px;">{{ v.gender === 'male' ? '男' : '女' }}</span>
                    </el-option>
                  </el-option-group>
                </el-select>
                <button
                  type="button"
                  class="preview-btn"
                  :class="{ playing: playingVoice && playingVoice === config.voice }"
                  :disabled="!config.voice"
                  @click="config.voice && playPreview(config.voice)"
                >
                  <el-icon :size="14">
                    <VideoPause v-if="playingVoice && playingVoice === config.voice" />
                    <VideoPlay v-else />
                  </el-icon>
                </button>
              </div>
            </el-form-item>

          <el-form-item label="帧率">
            <el-input-number v-model="config.fps" :min="24" :max="60" :step="1" style="width: 100%" />
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 底部提交栏 -->
    <div class="submit-bar">
      <div class="submit-info">
        <span v-if="selectedPresetInfo()">
          {{ selectedPresetInfo()!.width }} x {{ selectedPresetInfo()!.height }}
        </span>
        <span v-if="config.voice" class="divider">|</span>
        <span v-if="config.voice">{{ voices.find(v => v.id === config.voice)?.name }}</span>
        <span v-if="config.speech_rate !== 0" class="divider">|</span>
        <span v-if="config.speech_rate !== 0">语速 {{ config.speech_rate >= 0 ? '+' : '' }}{{ config.speech_rate }}%</span>
      </div>
      <button
        class="submit-btn"
        :class="{ disabled: !hasInput() || submitting }"
        :disabled="!hasInput() || submitting"
        @click="submit"
      >
        <template v-if="submitting">
          <span class="spinner"></span> 创建中...
        </template>
        <template v-else>
          开始生成 <el-icon style="margin-left: 4px;"><ArrowRight /></el-icon>
        </template>
      </button>
    </div>
  </div>
</template>

<style scoped>
.upload-view {
  max-width: 920px;
  margin: 0 auto;
}

/* Hero */
.hero {
  margin-bottom: 28px;
}

.hero h1 {
  font-size: 32px;
  font-weight: 800;
  color: #111;
  letter-spacing: -0.5px;
}

.subtitle {
  color: #6b7280;
  margin-top: 8px;
  font-size: 15px;
}

/* Steps Bar */
.steps-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding: 16px 24px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.step {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e5e7eb;
  color: #9ca3af;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step.active .step-num {
  background: #111;
  color: #fff;
}

.step-label {
  font-size: 13px;
  color: #9ca3af;
  font-weight: 500;
}

.step.active .step-label {
  color: #111;
}

.step-arrow {
  color: #d1d5db;
  font-size: 12px;
  display: flex;
}

/* Main Grid */
.main-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
  margin-bottom: 20px;
  align-items: stretch;
}

/* Panel */
.panel {
  background: #fff;
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.panel-header h2 {
  font-size: 16px;
  font-weight: 700;
  color: #111;
}

/* Mode Tabs */
.mode-tabs {
  display: flex;
  background: #f3f4f6;
  border-radius: 8px;
  padding: 3px;
}

.mode-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.mode-tab:hover {
  color: #374151;
}

.mode-tab.active {
  background: #fff;
  color: #111;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

/* Drop Zone */
.drop-zone {
  border: 2px dashed #e5e7eb;
  border-radius: 12px;
  transition: all 0.2s;
  cursor: pointer;
  background: #fafafa;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.drop-zone :deep(.el-upload) {
  width: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.drop-zone:hover,
.drop-zone.drag-over {
  border-color: #6366f1;
  background: #f5f3ff;
}

.drop-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 36px 20px;
  gap: 10px;
  flex: 1;
}

.drop-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: #eef2ff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}

.drop-title {
  font-size: 15px;
  font-weight: 600;
  color: #374151;
}

.drop-hint {
  font-size: 13px;
  color: #9ca3af;
}

/* File Selected */
.file-selected {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px 20px;
  flex: 1;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 14px;
}

.file-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #eef2ff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-name {
  font-weight: 600;
  font-size: 14px;
  color: #111;
}

.file-size {
  color: #9ca3af;
  font-size: 12px;
  margin-top: 2px;
}

.remove-btn {
  border: none;
  background: transparent;
  color: #ef4444;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.15s;
}

.remove-btn:hover {
  background: #fef2f2;
}

/* URL Zone */
.url-zone {
  border: 2px dashed #e5e7eb;
  border-radius: 12px;
  padding: 36px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #fafafa;
  flex: 1;
}

.url-input {
  width: 100%;
  margin-bottom: 4px;
}

/* Config Form */
.config-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.config-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.voice-row {
  display: flex;
  gap: 8px;
  width: 100%;
}

.preview-btn {
  width: 36px;
  height: 32px;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #6366f1;
  transition: all 0.15s;
  flex-shrink: 0;
}

.preview-btn:hover:not(:disabled) {
  border-color: #6366f1;
  background: #eef2ff;
}

.preview-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.preview-btn.playing {
  color: #ef4444;
  border-color: #fca5a5;
  background: #fef2f2;
}

/* Speech Rate */
.speech-rate-row {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.speech-rate-label {
  font-size: 13px;
  font-weight: 600;
  color: #6366f1;
  min-width: 48px;
  text-align: right;
  white-space: nowrap;
}

/* Submit Bar */
.submit-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-radius: 14px;
  padding: 16px 24px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.submit-info {
  font-size: 13px;
  color: #9ca3af;
  display: flex;
  align-items: center;
  gap: 8px;
}

.submit-info .divider {
  color: #e5e7eb;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 10px 28px;
  border: none;
  border-radius: 10px;
  background: #111;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-btn:hover:not(.disabled) {
  background: #333;
}

.submit-btn.disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .main-grid {
    grid-template-columns: 1fr;
  }

  .steps-bar {
    display: none;
  }
}

.form-hint {
  font-size: 12px;
  color: var(--el-text-color-placeholder, #a8abb2);
  margin-left: 8px;
}
</style>
