<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download, Edit, Plus, RefreshRight, Star, ZoomIn } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import {
  getTask, getTaskLogs, getVideoUrl, getEventSourceUrl, cancelTask, retryTask,
  getTaskScript, getTaskMarkdown, getTaskSummary, getTaskFigures,
  getFigureUrl, getAudioUrl, getPendingReview, approveStep, updateArtifact,
  resumeFromStep, reanalyzeFigure, rerunFigures, updateSummary, rotateFigure,
} from '@/api/client'
import type { TaskResponse, TaskEvent, TaskStage, TaskLogItem, PendingReview } from '@/api/types'
import ArtifactEditor from '@/components/ArtifactEditor.vue'
import StepActions from '@/components/StepActions.vue'

const md = new MarkdownIt({ html: true, linkify: true, typographer: true })

function renderLatex(latex: string): string {
  try {
    return katex.renderToString(latex, { displayMode: true, throwOnError: false, output: 'html' })
  } catch {
    return latex
  }
}

const props = defineProps<{ id: string }>()
const router = useRouter()

const task = ref<TaskResponse | null>(null)
const loading = ref(true)
const eventLog = ref<string[]>([])
const logContainer = ref<HTMLElement | null>(null)
const cancelling = ref(false)
const retrying = ref(false)
let evtSource: EventSource | null = null

// --- Step expand state ---
const expandedStep = ref<TaskStage | null>(null)
const stepLoading = ref(false)

// Intermediate data per stage
const markdownHtml = ref('')
const figureList = ref<string[]>([])
const summaryData = ref<any>(null)
const scriptData = ref<any>(null)
const audioCount = ref(0)
const lightboxSrc = ref('')
const lightboxVisible = ref(false)

// --- Streaming LLM output ---
const streamingText = ref('')
const streamingStep = ref('')
const isStreaming = ref(false)
const streamingContainer = ref<HTMLElement | null>(null)

const STEP_STREAM_LABELS: Record<string, string> = {
  extract: '信息提取',
  pass1: '快速扫描',
  pass2: '深度提取',
  script: '脚本生成',
  quality_gate: '质量优化',
  figure: '图表分析',
  story_architect: '故事架构师',
  scene_writer: '场景编剧',
  visual_director: '视觉导演',
  pacing_reviewer: '节奏审核员',
}

const streamingStepLabel = computed(() =>
  STEP_STREAM_LABELS[streamingStep.value] || streamingStep.value
)

watch(streamingText, () => {
  nextTick(() => {
    if (streamingContainer.value) {
      streamingContainer.value.scrollTop = streamingContainer.value.scrollHeight
    }
  })
})

// --- Interactive mode ---
const pendingReview = ref<PendingReview | null>(null)
const showEditor = ref(false)
const reviewLoading = ref(false)

function figFilename(path: string): string {
  return path.split('/').pop() || path
}

const FIGURE_TYPE_LABELS: Record<string, string> = {
  architecture: '架构图',
  comparison: '对比图',
  result: '结果图',
  visualization: '可视化',
  other: '其他',
}

function figureTypeLabel(type: string): string {
  return FIGURE_TYPE_LABELS[type] || type
}

const reanalyzingFigIdx = ref<number | null>(null)
const rotatingFigIdx = ref<number | null>(null)
const rerunningFigures = ref(false)
const savingSummary = ref(false)

function setFigureImportance(figIndex: number, score: number) {
  if (!summaryData.value?.figures?.[figIndex]) return
  const fig = summaryData.value.figures[figIndex]
  fig.importance = fig.importance === score ? 0 : score
}

async function handleReanalyzeFigure(figIndex: number) {
  if (!summaryData.value?.figures?.[figIndex]) return
  const fig = summaryData.value.figures[figIndex]
  reanalyzingFigIdx.value = figIndex
  try {
    const result = await reanalyzeFigure(props.id, fig.path, fig.caption)
    summaryData.value.figures[figIndex] = { ...fig, ...result }
    ElMessage.success('图片重新分析完成')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '重新分析失败')
  } finally {
    reanalyzingFigIdx.value = null
  }
}

async function handleRotateFigure(figIndex: number) {
  if (!summaryData.value?.figures?.[figIndex]) return
  const fig = summaryData.value.figures[figIndex]
  rotatingFigIdx.value = figIndex
  try {
    await rotateFigure(props.id, fig.path, 90)
    const imgElements = document.querySelectorAll(`.figure-analysis-card:nth-child(${figIndex + 1}) img`)
    imgElements.forEach(el => {
      const img = el as HTMLImageElement
      const src = img.src
      img.src = ''
      img.src = src + (src.includes('?') ? '&' : '?') + 't=' + Date.now()
    })
    ElMessage.success('图片已旋转 90°')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '旋转失败')
  } finally {
    rotatingFigIdx.value = null
  }
}

async function handleRotateRawFigure(fi: number, filename: string) {
  try {
    await rotateFigure(props.id, `images/${filename}`, 90)
    const imgElements = document.querySelectorAll(`.figure-grid .figure-item:nth-child(${fi + 1}) img`)
    imgElements.forEach(el => {
      const img = el as HTMLImageElement
      img.src = img.src.split('?')[0] + '?t=' + Date.now()
    })
    ElMessage.success('图片已旋转 90°')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '旋转失败')
  }
}

async function handleRerunAllFigures() {
  rerunningFigures.value = true
  try {
    const result = await rerunFigures(props.id)
    if (summaryData.value) {
      summaryData.value.figures = result.figures
    }
    ElMessage.success(`图表全部重新分析完成 (${result.count} 张)`)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '重新分析失败')
  } finally {
    rerunningFigures.value = false
  }
}

async function handleSaveSummary() {
  if (!summaryData.value) return
  savingSummary.value = true
  try {
    await updateSummary(props.id, summaryData.value)
    ElMessage.success('摘要已保存')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '保存失败')
  } finally {
    savingSummary.value = false
  }
}

function openLightbox(src: string) {
  lightboxSrc.value = src
  lightboxVisible.value = true
}

function closeLightbox() {
  lightboxVisible.value = false
  lightboxSrc.value = ''
}

const PIPELINE_STEPS: { stage: TaskStage; label: string }[] = [
  { stage: 'parsing', label: 'PDF 解析' },
  { stage: 'extracting', label: '信息提取' },
  { stage: 'scripting', label: '脚本生成' },
  { stage: 'tts', label: '语音合成' },
  { stage: 'rendering', label: '视频渲染' },
]

const stageOrder: TaskStage[] = ['pending', 'parsing', 'extracting', 'scripting', 'tts', 'rendering', 'completed']

const stepTimestamps = ref<Record<string, number>>({})
const stepDurations = ref<Record<string, number>>({})

function stageIndex(stage: TaskStage): number {
  return stageOrder.indexOf(stage)
}

const isFinished = computed(() =>
  task.value?.stage === 'completed' || task.value?.stage === 'failed'
)

const videoUrl = computed(() =>
  task.value?.stage === 'completed' ? getVideoUrl(props.id) : null
)

const progressPercent = computed(() => {
  if (!task.value) return 0
  return Math.max(task.value.progress, 0)
})

const STAGE_PROGRESS_THRESHOLDS: Record<TaskStage, number> = {
  pending: 0,
  parsing: 10,
  extracting: 30,
  scripting: 50,
  tts: 70,
  rendering: 85,
  completed: 100,
  failed: -1,
}

function stepStatus(stepStage: TaskStage): 'wait' | 'process' | 'finish' | 'error' {
  if (!task.value) return 'wait'
  if (task.value.stage === 'completed') return 'finish'

  if (task.value.stage === 'failed') {
    const failedAt = task.value.progress
    const stepThreshold = STAGE_PROGRESS_THRESHOLDS[stepStage] ?? 0
    const nextStep = PIPELINE_STEPS[PIPELINE_STEPS.findIndex(s => s.stage === stepStage) + 1]
    const nextThreshold = nextStep ? (STAGE_PROGRESS_THRESHOLDS[nextStep.stage] ?? 100) : 100
    if (failedAt >= nextThreshold) return 'finish'
    if (failedAt >= stepThreshold) return 'error'
    return 'wait'
  }

  const current = stageIndex(task.value.stage)
  const step = stageIndex(stepStage)
  if (step < current) return 'finish'
  if (step === current) return 'process'
  return 'wait'
}

const isWaitingReview = computed(() =>
  task.value?.stage_label?.includes('等待审核') ?? false
)

function isStepClickable(stage: TaskStage): boolean {
  const s = stepStatus(stage)
  if (s === 'finish' || s === 'error') return true
  if (s === 'process' && isWaitingReview.value) return true
  return false
}

function formatDuration(ms: number): string {
  if (ms < 1000) return '<1s'
  const sec = Math.round(ms / 1000)
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  const s = sec % 60
  return `${min}m ${s}s`
}

function trackStageChange(stage: TaskStage) {
  const now = Date.now()
  const prevStage = PIPELINE_STEPS.find(
    (_, i) => PIPELINE_STEPS[i + 1]?.stage === stage || (stage === 'completed' && i === PIPELINE_STEPS.length - 1)
  )
  if (stepTimestamps.value[stage] === undefined) {
    stepTimestamps.value[stage] = now
  }
  if (prevStage && stepTimestamps.value[prevStage.stage]) {
    stepDurations.value[prevStage.stage] = now - stepTimestamps.value[prevStage.stage]
  }
  if (stage === 'completed') {
    const last = PIPELINE_STEPS[PIPELINE_STEPS.length - 1]
    if (stepTimestamps.value[last.stage]) {
      stepDurations.value[last.stage] = now - stepTimestamps.value[last.stage]
    }
  }
}

const SCENE_LABELS: Record<string, string> = {
  title: '标题', overview: '概述', method: '方法', formula: '公式',
  figure: '图表', result: '结果', conclusion: '结论',
}

function sceneTypeLabel(type: string): string {
  return SCENE_LABELS[type] || type
}

// --- Load stage data on expand ---
async function toggleStep(stage: TaskStage) {
  if (!isStepClickable(stage)) return
  if (expandedStep.value === stage) {
    expandedStep.value = null
    return
  }
  expandedStep.value = stage
  stepLoading.value = true
  try {
    await loadStageData(stage)
  } finally {
    stepLoading.value = false
  }
}

async function loadStageData(stage: TaskStage) {
  switch (stage) {
    case 'parsing':
      if (!markdownHtml.value) {
        const [rawMd, figs] = await Promise.all([
          getTaskMarkdown(props.id).catch(() => ''),
          getTaskFigures(props.id).catch(() => [] as string[]),
        ])
        markdownHtml.value = rawMd ? md.render(rawMd) : ''
        figureList.value = figs
      }
      break
    case 'extracting':
      if (!summaryData.value) {
        summaryData.value = await getTaskSummary(props.id).catch(() => null)
      }
      break
    case 'scripting':
      if (!scriptData.value) {
        scriptData.value = await getTaskScript(props.id).catch(() => null)
      }
      break
    case 'tts':
      if (!scriptData.value) {
        scriptData.value = await getTaskScript(props.id).catch(() => null)
      }
      audioCount.value = scriptData.value?.scenes?.length || 0
      break
    case 'rendering':
      break
  }
}

async function loadHistoryLogs() {
  try {
    const logs: TaskLogItem[] = await getTaskLogs(props.id)
    eventLog.value = logs
      .filter((l) => l.message)
      .map((l) => {
        const ts = l.created_at.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(l.created_at) ? l.created_at : l.created_at + 'Z'
        return `[${new Date(ts).toLocaleTimeString('zh-CN')}] ${l.message}`
      })
  } catch {
    // ignore
  }
}

function connectSSE() {
  evtSource = new EventSource(getEventSourceUrl(props.id))
  evtSource.onmessage = (e) => {
    try {
      const evt: TaskEvent = JSON.parse(e.data)

      if (evt.token_delta) {
        streamingText.value += evt.token_delta
        streamingStep.value = evt.token_step || ''
        isStreaming.value = true
        return
      }

      if (task.value) {
        const prevStage = task.value.stage
        task.value.stage = evt.stage
        task.value.progress = evt.progress
        task.value.stage_label = evt.stage_label
        task.value.video_path = evt.video_path
        task.value.error = evt.error
        if (prevStage !== evt.stage) {
          trackStageChange(evt.stage)
          streamingText.value = ''
          streamingStep.value = ''
          isStreaming.value = false
        }
      }
      if (evt.message) {
        const isAgentStep = evt.token_step && !evt.token_delta
        if (isAgentStep) {
          streamingStep.value = evt.token_step || ''
          isStreaming.value = true
          streamingText.value = evt.message
        } else {
          streamingText.value = ''
          isStreaming.value = false
        }
        const ts = new Date().toLocaleTimeString('zh-CN')
        eventLog.value.push(`[${ts}] ${evt.message}`)
        if (eventLog.value.length > 200) eventLog.value.shift()
      }
      if (evt.stage_label?.includes('等待审核')) {
        isStreaming.value = false
        checkPendingReview()
      }
      if (evt.stage === 'completed' || evt.stage === 'failed') {
        isStreaming.value = false
        pendingReview.value = null
        showEditor.value = false
        evtSource?.close()
      }
    } catch {
      // ignore
    }
  }
  evtSource.onerror = () => {
    evtSource?.close()
  }
}

// --- Interactive mode methods ---
const REVIEW_STEP_TO_STAGE: Record<string, TaskStage> = {
  extract: 'extracting',
  script: 'scripting',
  tts: 'tts',
}

async function checkPendingReview() {
  try {
    const review = await getPendingReview(props.id)
    pendingReview.value = review
    if (review?.step) {
      const stage = REVIEW_STEP_TO_STAGE[review.step]
      if (stage && expandedStep.value !== stage) {
        expandedStep.value = stage
        stepLoading.value = true
        try {
          await loadStageData(stage)
        } finally {
          stepLoading.value = false
        }
      }
    }
  } catch {
    pendingReview.value = null
  }
}

const STEP_LABELS: Record<string, string> = {
  extract: '信息提取',
  script: '脚本生成',
  tts: '语音合成',
}

async function handleApprove() {
  if (!pendingReview.value) return
  reviewLoading.value = true
  try {
    await approveStep(props.id)
    pendingReview.value = null
    showEditor.value = false
    ElMessage.success('已批准，继续执行')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '操作失败')
  } finally {
    reviewLoading.value = false
  }
}

async function handleEditAndContinue() {
  showEditor.value = true
}

async function handleSaveEdit(data: Record<string, unknown>) {
  if (!pendingReview.value) return
  reviewLoading.value = true
  try {
    await approveStep(props.id, { action: 'edit', data })
    pendingReview.value = null
    showEditor.value = false
    ElMessage.success('已保存编辑并继续')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '保存失败')
  } finally {
    reviewLoading.value = false
  }
}

async function handleRetryStep() {
  if (!pendingReview.value) return
  const step = pendingReview.value.step
  reviewLoading.value = true
  try {
    await resumeFromStep(props.id, step)
    pendingReview.value = null
    showEditor.value = false
    ElMessage.success('正在重新执行该步骤')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '操作失败')
  } finally {
    reviewLoading.value = false
  }
}

async function handleResumeFrom(step: string) {
  reviewLoading.value = true
  try {
    await resumeFromStep(props.id, step)
    ElMessage.success(`从 ${step} 步骤开始重新执行`)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '操作失败')
  } finally {
    reviewLoading.value = false
  }
}

async function handleCancel() {
  if (cancelling.value) return
  cancelling.value = true
  try {
    await cancelTask(props.id)
    ElMessage.success('已发送取消请求')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '取消失败')
  } finally {
    cancelling.value = false
  }
}

async function handleRetry() {
  if (retrying.value) return
  retrying.value = true
  try {
    const updated = await retryTask(props.id)
    task.value = updated
    eventLog.value = []
    expandedStep.value = null
    markdownHtml.value = ''
    figureList.value = []
    summaryData.value = null
    scriptData.value = null
    stepTimestamps.value = {}
    stepDurations.value = {}
    connectSSE()
    ElMessage.success('任务已重新开始')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '重试失败')
  } finally {
    retrying.value = false
  }
}

watch(eventLog, () => {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}, { deep: true })

onMounted(async () => {
  try {
    task.value = await getTask(props.id)
    if (task.value) {
      trackStageChange(task.value.stage)
      if (task.value.stage_label?.includes('等待审核')) {
        checkPendingReview()
      }
    }
    if (isFinished.value) {
      await loadHistoryLogs()
    } else {
      connectSSE()
    }
  } catch {
    ElMessage.error('任务不存在')
    router.push('/tasks')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  evtSource?.close()
})
</script>

<template>
  <div class="detail-view" v-loading="loading">
    <div v-if="task" class="detail-content">
      <!-- 顶部导航 -->
      <div class="top-nav">
        <button class="back-btn" @click="router.push('/tasks')">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </button>
      </div>

      <!-- 标题区 -->
      <div class="detail-header">
        <div class="header-info">
          <h1>{{ task.filename }}</h1>
          <p v-if="task.paper_title" class="paper-title">{{ task.paper_title }}</p>
        </div>
        <div class="header-actions">
          <button
            v-if="!isFinished"
            class="cancel-btn"
            :disabled="cancelling"
            @click="handleCancel"
          >
            {{ cancelling ? '取消中...' : '取消任务' }}
          </button>
          <button
            v-if="isFinished"
            class="retry-btn"
            :disabled="retrying"
            @click="handleRetry"
          >
            {{ retrying ? '重试中...' : '重新执行' }}
          </button>
          <div
            class="status-badge"
            :class="{
              success: task.stage === 'completed',
              error: task.stage === 'failed',
              running: !isFinished,
            }"
          >
            <span v-if="!isFinished" class="status-dot" />
            {{ task.stage_label }}
          </div>
        </div>
      </div>

      <!-- 进度区域 -->
      <div class="panel progress-panel">
        <!-- 步骤条 -->
        <div class="steps-row">
          <template v-for="(step, idx) in PIPELINE_STEPS" :key="step.stage">
            <div
              class="step-card"
              :class="{
                done: stepStatus(step.stage) === 'finish',
                active: stepStatus(step.stage) === 'process',
                error: stepStatus(step.stage) === 'error',
                clickable: isStepClickable(step.stage),
                expanded: expandedStep === step.stage,
              }"
              @click="toggleStep(step.stage)"
            >
              <div class="step-num">{{ idx + 1 }}</div>
              <div class="step-info">
                <span class="step-name">{{ step.label }}</span>
                <span v-if="stepDurations[step.stage]" class="step-time">
                  {{ formatDuration(stepDurations[step.stage]) }}
                </span>
                <span v-else-if="stepStatus(step.stage) === 'process' && isWaitingReview" class="step-time review">
                  等待审核
                </span>
                <span v-else-if="stepStatus(step.stage) === 'process'" class="step-time running">
                  进行中...
                </span>
              </div>
              <span v-if="isStepClickable(step.stage)" class="step-arrow" :class="{ open: expandedStep === step.stage }">&#9662;</span>
            </div>
            <div v-if="idx < PIPELINE_STEPS.length - 1" class="step-connector" :class="{ filled: stepStatus(PIPELINE_STEPS[idx + 1].stage) !== 'wait' }" />
          </template>
        </div>

        <!-- 进度条 -->
        <div class="progress-bar-wrapper">
          <div class="progress-track">
            <div
              class="progress-fill"
              :class="{ success: task.stage === 'completed', error: task.stage === 'failed' }"
              :style="{ width: progressPercent + '%' }"
            />
          </div>
          <span class="progress-text">{{ progressPercent }}%</span>
        </div>
      </div>

      <!-- AI 流式输出面板 -->
      <transition name="expand">
        <div v-if="isStreaming" class="panel streaming-panel" :key="'streaming'">
          <div class="streaming-header">
            <span class="streaming-dot" />
            <span class="streaming-label">{{ streamingStepLabel }} — AI 输出中</span>
          </div>
          <div ref="streamingContainer" class="streaming-content">
            <pre class="streaming-text">{{ streamingText }}<span class="streaming-cursor">|</span></pre>
          </div>
        </div>
      </transition>

      <!-- 展开面板 -->
      <transition name="expand">
        <div v-if="expandedStep" class="panel expand-panel" :key="expandedStep">
          <div v-if="stepLoading" class="expand-loading">加载中...</div>

          <!-- ===== 解析阶段 ===== -->
          <template v-else-if="expandedStep === 'parsing'">
            <div class="expand-header">
              <h3>PDF 解析结果</h3>
              <span class="expand-hint">Markdown 全文预览及提取的图片</span>
            </div>
            <div v-if="markdownHtml" class="markdown-body" v-html="markdownHtml" />
            <div v-else class="expand-empty">暂无解析数据</div>
            <div v-if="figureList.length > 0" class="figure-gallery">
              <h4>提取的图片 ({{ figureList.length }})</h4>
              <div class="figure-grid">
                <div v-for="(fig, fi) in figureList" :key="fig" class="figure-item">
                  <div class="figure-img-wrapper" @click="openLightbox(getFigureUrl(id, fig))">
                    <img :src="getFigureUrl(id, fig)" :alt="fig" loading="lazy" />
                    <div class="figure-zoom-hint"><el-icon><ZoomIn /></el-icon></div>
                  </div>
                  <el-button
                    size="small"
                    text
                    class="figure-rotate-btn"
                    @click.stop="handleRotateRawFigure(fi, fig)"
                  ><el-icon><RefreshRight /></el-icon></el-button>
                </div>
              </div>
            </div>
          </template>

          <!-- ===== 提取阶段 ===== -->
          <template v-else-if="expandedStep === 'extracting'">
            <div class="expand-header">
              <h3>论文摘要</h3>
              <span class="expand-hint">结构化信息提取</span>
            </div>
            <div v-if="summaryData" class="summary-content">
              <div class="summary-meta">
                <h2 class="summary-title">{{ summaryData.title }}</h2>
                <p v-if="summaryData.authors?.length" class="summary-authors">
                  {{ summaryData.authors.join(', ') }}
                  <span v-if="summaryData.year" class="summary-year">({{ summaryData.year }})</span>
                </p>
              </div>

              <div class="summary-section" v-if="summaryData.problem">
                <h4>研究问题</h4>
                <p>{{ summaryData.problem }}</p>
              </div>

              <div class="summary-section" v-if="summaryData.method">
                <h4>方法</h4>
                <p>{{ summaryData.method.summary }}</p>
                <ul v-if="summaryData.method.key_steps?.length">
                  <li v-for="(s, i) in summaryData.method.key_steps" :key="i">{{ s }}</li>
                </ul>
                <div v-if="summaryData.method.formulas?.length" class="formula-list">
                  <div v-for="(f, i) in summaryData.method.formulas" :key="i" class="formula-item" v-html="renderLatex(f)" />
                </div>
              </div>

              <div class="summary-section" v-if="summaryData.results">
                <h4>实验结果</h4>
                <p v-if="summaryData.results.datasets?.length">
                  <strong>数据集：</strong>{{ summaryData.results.datasets.join(', ') }}
                </p>
                <ul v-if="summaryData.results.metrics?.length">
                  <li v-for="(m, i) in summaryData.results.metrics" :key="i">{{ m }}</li>
                </ul>
                <div v-if="summaryData.results.baselines?.length" class="baselines-table">
                  <strong>对比方法：</strong>
                  <table>
                    <thead>
                      <tr><th>方法</th><th>指标</th><th>数值</th></tr>
                    </thead>
                    <tbody>
                      <tr v-for="(b, i) in summaryData.results.baselines" :key="i" :class="{ highlight: b.highlight }">
                        <td>{{ b.name }}</td>
                        <td>{{ b.metric }}</td>
                        <td>{{ b.value }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p v-if="summaryData.results.findings">
                  <strong>发现：</strong>{{ summaryData.results.findings }}
                </p>
              </div>

              <div class="summary-section" v-if="summaryData.conclusion">
                <h4>结论</h4>
                <p>{{ summaryData.conclusion }}</p>
              </div>

              <div class="summary-section" v-if="summaryData.contributions?.length">
                <h4>贡献</h4>
                <ul>
                  <li v-for="(c, i) in summaryData.contributions" :key="i">{{ c }}</li>
                </ul>
              </div>

              <div class="summary-section" v-if="summaryData.key_insights?.length">
                <h4>关键洞察</h4>
                <ul>
                  <li v-for="(ins, i) in summaryData.key_insights" :key="i">{{ ins }}</li>
                </ul>
              </div>

              <div class="summary-actions" v-if="isWaitingReview || true">
                <el-button size="small" :loading="savingSummary" @click="handleSaveSummary">保存修改</el-button>
                <el-button size="small" :loading="rerunningFigures" @click="handleRerunAllFigures">重新分析全部图表</el-button>
              </div>

              <div class="summary-section" v-if="summaryData.figures?.length">
                <h4>图表分析 ({{ summaryData.figures.length }})</h4>
                <p class="figure-hint">点击星级评分可标记重要性（5 星 = 必须在视频中展示）。不评分则沿用 AI 默认判断。</p>
                <div class="figure-analysis-grid">
                  <div
                    v-for="(fig, i) in summaryData.figures"
                    :key="i"
                    class="figure-analysis-card"
                    :class="{ 'must-include': fig.importance === 5 }"
                  >
                    <div class="figure-analysis-img" @click="openLightbox(getFigureUrl(id, figFilename(fig.path)))">
                      <img :src="getFigureUrl(id, figFilename(fig.path))" :alt="fig.caption || fig.path" loading="lazy" />
                      <div class="figure-zoom-hint"><el-icon><ZoomIn /></el-icon></div>
                    </div>
                    <div class="figure-analysis-body">
                      <div class="figure-analysis-meta">
                        <span v-if="fig.figure_type" class="figure-type-tag">{{ figureTypeLabel(fig.figure_type) }}</span>
                        <span v-else class="figure-type-tag unknown">未分类</span>
                        <span class="figure-star-rating">
                          <el-icon
                            v-for="s in 5"
                            :key="s"
                            class="star-icon"
                            :class="{ filled: s <= fig.importance }"
                            @click.stop="setFigureImportance(i, s)"
                          ><Star /></el-icon>
                        </span>
                      </div>
                      <p v-if="fig.caption" class="figure-caption">{{ fig.caption }}</p>
                      <p v-else class="figure-caption placeholder">无标题</p>
                      <p v-if="fig.description" class="figure-description">{{ fig.description }}</p>
                      <p v-else class="figure-description placeholder">AI 未生成描述（可能因接口限流跳过）</p>
                      <div class="figure-actions">
                        <el-button
                          size="small"
                          text
                          :loading="rotatingFigIdx === i"
                          @click.stop="handleRotateFigure(i)"
                        ><el-icon><RefreshRight /></el-icon> 旋转</el-button>
                        <el-button
                          size="small"
                          text
                          :loading="reanalyzingFigIdx === i"
                          @click.stop="handleReanalyzeFigure(i)"
                        >重新分析</el-button>
                      </div>
                      <span v-if="fig.importance === 5" class="must-include-badge">必选</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="summary-tags" v-if="summaryData.paper_type || summaryData.core_idea">
                <span v-if="summaryData.paper_type" class="summary-tag">{{ summaryData.paper_type }}</span>
                <span v-if="summaryData.core_idea" class="summary-core-idea">{{ summaryData.core_idea }}</span>
              </div>
            </div>
            <div v-else class="expand-empty">暂无摘要数据</div>
          </template>

          <!-- ===== 脚本阶段 ===== -->
          <template v-else-if="expandedStep === 'scripting'">
            <div class="expand-header">
              <h3>旁白脚本</h3>
              <span v-if="scriptData?.scenes" class="expand-hint">共 {{ scriptData.scenes.length }} 个场景</span>
            </div>
            <div v-if="scriptData?.scenes?.length" class="script-list">
              <div v-for="(scene, idx) in scriptData.scenes" :key="idx" class="script-item">
                <div class="script-item-header">
                  <span class="script-idx">{{ idx + 1 }}</span>
                  <span class="script-type">{{ sceneTypeLabel(scene.type) }}</span>
                </div>
                <p class="script-narration">{{ scene.narration }}</p>
              </div>
            </div>
            <div v-else class="expand-empty">暂无脚本数据</div>
          </template>

          <!-- ===== 语音阶段 ===== -->
          <template v-else-if="expandedStep === 'tts'">
            <div class="expand-header">
              <h3>语音合成</h3>
              <span v-if="audioCount" class="expand-hint">共 {{ audioCount }} 段音频</span>
            </div>
            <div v-if="audioCount > 0" class="audio-list">
              <div v-for="idx in audioCount" :key="idx - 1" class="audio-item">
                <div class="audio-info">
                  <span class="audio-idx">{{ idx }}</span>
                  <span v-if="scriptData?.scenes?.[idx - 1]" class="audio-text">
                    {{ scriptData.scenes[idx - 1].narration.slice(0, 60) }}{{ scriptData.scenes[idx - 1].narration.length > 60 ? '...' : '' }}
                  </span>
                </div>
                <audio controls preload="none" :src="getAudioUrl(id, idx - 1)" class="audio-player" />
              </div>
            </div>
            <div v-else class="expand-empty">暂无音频数据</div>
          </template>

          <!-- ===== 渲染阶段 ===== -->
          <template v-else-if="expandedStep === 'rendering'">
            <div class="expand-header">
              <h3>生成结果</h3>
            </div>
            <div v-if="videoUrl">
              <div class="video-wrapper">
                <video controls :src="videoUrl" class="video-player">
                  您的浏览器不支持视频播放
                </video>
              </div>
              <div class="video-actions">
                <a :href="videoUrl" download class="action-btn primary">
                  <el-icon><Download /></el-icon>
                  下载视频
                </a>
                <button class="action-btn" @click="router.push('/')">
                  <el-icon><Plus /></el-icon>
                  生成新视频
                </button>
              </div>
            </div>
            <div v-else class="expand-empty">视频尚未生成</div>
          </template>
        </div>
      </transition>

      <!-- 错误信息 -->
      <div v-if="task.error" class="panel error-panel">
        <div class="error-header">
          <span class="error-icon">!</span>
          <h3>错误信息</h3>
          <button
            class="retry-btn retry-btn-sm"
            :disabled="retrying"
            @click="handleRetry"
          >
            {{ retrying ? '重试中...' : '重试' }}
          </button>
        </div>
        <pre class="error-text">{{ task.error }}</pre>
      </div>

      <!-- 人工审核面板 (Interactive Mode) -->
      <div v-if="pendingReview" class="panel review-panel">
        <h3>
          <el-icon style="vertical-align: middle; margin-right: 4px"><Edit /></el-icon>
          等待审核 — {{ STEP_LABELS[pendingReview.step] || pendingReview.step }}
        </h3>
        <p class="review-message">{{ pendingReview.message }}</p>

        <ArtifactEditor
          v-if="showEditor"
          :data="pendingReview.data"
          :artifact-type="pendingReview.artifact_type"
          @save="handleSaveEdit"
        />

        <StepActions
          v-else
          :step="STEP_LABELS[pendingReview.step] || pendingReview.step"
          :loading="reviewLoading"
          @approve="handleApprove"
          @edit="handleEditAndContinue"
          @retry="handleRetryStep"
        />
      </div>

      <!-- 日志 -->
      <div v-if="eventLog.length > 0" class="panel log-panel">
        <h3>处理日志</h3>
        <div ref="logContainer" class="log-list">
          <div v-for="(msg, i) in eventLog" :key="i" class="log-item">
            <span class="log-dot" />
            <span>{{ msg }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Lightbox overlay -->
  <Teleport to="body">
    <div v-if="lightboxVisible" class="lightbox-overlay" @click="closeLightbox">
      <img :src="lightboxSrc" class="lightbox-img" @click.stop />
      <button class="lightbox-close" @click="closeLightbox">&times;</button>
    </div>
  </Teleport>
</template>

<style scoped>
.detail-view {
  max-width: 900px;
  margin: 0 auto;
}

/* Top Nav */
.top-nav {
  margin-bottom: 16px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 13px;
  cursor: pointer;
  padding: 6px 0;
  transition: color 0.15s;
}

.back-btn:hover {
  color: #111;
}

/* Header */
.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.detail-header h1 {
  font-size: 24px;
  font-weight: 800;
  color: #111;
  letter-spacing: -0.3px;
}

.paper-title {
  font-size: 14px;
  color: #9ca3af;
  margin-top: 4px;
  max-width: 520px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.cancel-btn {
  padding: 6px 14px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fff;
  color: #dc2626;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.cancel-btn:hover:not(:disabled) {
  background: #fef2f2;
}

.cancel-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.retry-btn {
  padding: 6px 14px;
  border: 1px solid #c7d2fe;
  border-radius: 8px;
  background: #fff;
  color: #4f46e5;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.retry-btn:hover:not(:disabled) {
  background: #eef2ff;
  border-color: #818cf8;
}

.retry-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.retry-btn-sm {
  margin-left: auto;
  padding: 4px 12px;
  font-size: 12px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.status-badge.success { background: #ecfdf5; color: #059669; }
.status-badge.error { background: #fef2f2; color: #dc2626; }
.status-badge.running { background: #eef2ff; color: #6366f1; }

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: blink 1.2s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* Panel */
.panel {
  background: #fff;
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  margin-bottom: 16px;
}

.panel h3 {
  font-size: 15px;
  font-weight: 700;
  color: #111;
  margin: 0;
}

/* Steps Row */
.steps-row {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
}

.step-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;
  flex-shrink: 0;
  position: relative;
  user-select: none;
}

.step-card.clickable {
  cursor: pointer;
}

.step-card.clickable:hover {
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.12);
  border-color: #a5b4fc;
}

.step-card.done { background: #ecfdf5; border-color: #a7f3d0; }
.step-card.active { background: #eef2ff; border-color: #c7d2fe; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1); }
.step-card.error { background: #fef2f2; border-color: #fecaca; }
.step-card.expanded { border-color: #818cf8; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15); }

.step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e5e7eb;
  color: #9ca3af;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-card.done .step-num { background: #10b981; color: #fff; }
.step-card.active .step-num { background: #6366f1; color: #fff; }
.step-card.error .step-num { background: #ef4444; color: #fff; }

.step-info {
  display: flex;
  flex-direction: column;
}

.step-name {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.step-card.done .step-name { color: #059669; }
.step-card.active .step-name { color: #4f46e5; }
.step-card.error .step-name { color: #dc2626; }

.step-time {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 1px;
}

.step-time.running { color: #6366f1; }
.step-time.review { color: #f59e0b; font-weight: 600; }

.step-arrow {
  font-size: 10px;
  color: #9ca3af;
  transition: transform 0.2s;
  margin-left: 2px;
}

.step-arrow.open {
  transform: rotate(180deg);
}

.step-connector {
  flex: 1;
  height: 2px;
  background: #e5e7eb;
  margin: 0 6px;
  min-width: 12px;
  transition: background 0.3s;
}

.step-connector.filled { background: #10b981; }

/* Progress Bar */
.progress-bar-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-track {
  flex: 1;
  height: 8px;
  background: #f3f4f6;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #6366f1;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.progress-fill.success { background: #10b981; }
.progress-fill.error { background: #ef4444; }

.progress-text {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
  min-width: 40px;
  text-align: right;
}

/* Expand panel transition */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.25s ease;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Expand Panel */
.expand-panel {
  border: 1px solid #e0e7ff;
  background: #fafaff;
}

.expand-loading {
  text-align: center;
  padding: 32px 0;
  color: #9ca3af;
  font-size: 14px;
}

.expand-empty {
  text-align: center;
  padding: 32px 0;
  color: #9ca3af;
  font-size: 14px;
}

.expand-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.expand-hint {
  font-size: 13px;
  color: #94a3b8;
}

/* ===== Parsing: Markdown ===== */
.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: #1e293b;
  max-height: 500px;
  overflow-y: auto;
  padding: 16px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin-top: 1.2em;
  margin-bottom: 0.4em;
  font-weight: 700;
  color: #111;
}

.markdown-body :deep(h1) { font-size: 20px; }
.markdown-body :deep(h2) { font-size: 17px; }
.markdown-body :deep(h3) { font-size: 15px; }

.markdown-body :deep(p) {
  margin-bottom: 0.8em;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  font-size: 13px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f8fafc;
  font-weight: 600;
}

.markdown-body :deep(code) {
  background: #f1f5f9;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}

.markdown-body :deep(pre) {
  background: #f8fafc;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
}

/* Figure gallery */
.figure-gallery {
  margin-top: 20px;
}

.figure-gallery h4 {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 12px;
}

.figure-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.figure-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  aspect-ratio: 4/3;
  display: flex;
  align-items: center;
  justify-content: center;
}

.figure-item img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

/* ===== Extracting: Summary ===== */
.summary-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-meta {
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.summary-title {
  font-size: 20px;
  font-weight: 800;
  color: #111;
  margin: 0 0 6px;
}

.summary-authors {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.summary-year {
  color: #9ca3af;
}

.summary-section h4 {
  font-size: 14px;
  font-weight: 700;
  color: #4f46e5;
  margin: 0 0 8px;
}

.summary-section p {
  font-size: 14px;
  line-height: 1.7;
  color: #374151;
  margin: 0 0 8px;
}

.summary-section ul {
  margin: 0;
  padding-left: 20px;
}

.summary-section li {
  font-size: 14px;
  line-height: 1.7;
  color: #374151;
  margin-bottom: 4px;
}

.formula-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.formula-item {
  display: block;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px 16px;
  overflow-x: auto;
  text-align: center;
}

.baselines-table {
  margin-top: 8px;
}

.baselines-table table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 6px;
  font-size: 13px;
}

.baselines-table th,
.baselines-table td {
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  text-align: left;
}

.baselines-table th {
  background: #f8fafc;
  font-weight: 600;
  font-size: 12px;
  color: #6b7280;
}

.baselines-table tr.highlight td {
  background: #eef2ff;
  font-weight: 600;
  color: #4f46e5;
}

.summary-tags {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

.summary-tag {
  display: inline-block;
  padding: 3px 10px;
  background: #eef2ff;
  color: #4f46e5;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.summary-core-idea {
  font-size: 13px;
  color: #6b7280;
  font-style: italic;
}

/* ===== Figure Analysis ===== */
.figure-hint {
  font-size: 12px;
  color: #9ca3af;
  margin: 0 0 12px;
}

.figure-analysis-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.figure-analysis-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  background: #fafbfc;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.figure-analysis-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.figure-analysis-card.must-include {
  border-color: #f59e0b;
  box-shadow: 0 0 0 1px #f59e0b;
}

.figure-analysis-img {
  position: relative;
  cursor: pointer;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  max-height: 220px;
  overflow: hidden;
}

.figure-analysis-img img {
  max-width: 100%;
  max-height: 220px;
  object-fit: contain;
}

.figure-analysis-body {
  padding: 12px;
  position: relative;
}

.figure-analysis-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.figure-type-tag {
  padding: 2px 8px;
  background: #e0e7ff;
  color: #4338ca;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.figure-type-tag.unknown {
  background: #f3f4f6;
  color: #9ca3af;
}

.figure-star-rating {
  display: flex;
  gap: 2px;
}

.star-icon {
  font-size: 16px;
  color: #d1d5db;
  cursor: pointer;
  transition: color 0.15s, transform 0.15s;
}

.star-icon:hover { transform: scale(1.2); }
.star-icon.filled { color: #f59e0b; }

.figure-caption {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 4px;
  line-height: 1.4;
}

.figure-caption.placeholder {
  font-weight: 400;
  color: #d1d5db;
  font-style: italic;
}

.figure-description {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
}

.figure-description.placeholder {
  color: #d1d5db;
  font-style: italic;
}

.figure-actions {
  margin-top: 6px;
}

.must-include-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 8px;
  background: #f59e0b;
  color: #fff;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 700;
}

.summary-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

/* ===== Scripting: Script list ===== */
.script-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 500px;
  overflow-y: auto;
}

.script-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 16px;
  background: #fff;
  transition: border-color 0.2s;
}

.script-item:hover {
  border-color: #818cf8;
}

.script-item-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.script-idx {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #6366f1;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.script-type {
  font-size: 12px;
  font-weight: 600;
  color: #6366f1;
  background: #eef2ff;
  padding: 2px 10px;
  border-radius: 10px;
}

.script-narration {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #475569;
}

/* ===== TTS: Audio list ===== */
.audio-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 500px;
  overflow-y: auto;
}

.audio-item {
  display: flex;
  align-items: center;
  gap: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  background: #fff;
}

.audio-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.audio-idx {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #8b5cf6;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.audio-text {
  font-size: 13px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.audio-player {
  height: 32px;
  flex-shrink: 0;
}

/* ===== Rendering: Video ===== */
.video-wrapper {
  border-radius: 10px;
  overflow: hidden;
  background: #000;
  margin-bottom: 16px;
}

.video-player {
  width: 100%;
  max-height: 480px;
  display: block;
}

.video-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s;
}

.action-btn:hover {
  border-color: #d1d5db;
  background: #f9fafb;
}

.action-btn.primary {
  background: #111;
  color: #fff;
  border-color: #111;
}

.action-btn.primary:hover {
  background: #333;
}

/* Error */
.error-panel {
  border: 1px solid #fecaca;
  background: #fff;
}

.error-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.error-header h3 {
  color: #dc2626;
}

.error-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #fef2f2;
  color: #dc2626;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-text {
  font-size: 13px;
  color: #991b1b;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow: auto;
  background: #fef2f2;
  padding: 12px;
  border-radius: 8px;
  margin: 0;
}

/* Review Panel (Interactive Mode) */
.review-panel {
  border-left: 4px solid var(--el-color-primary);
}
.review-panel h3 {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}
.review-message {
  color: var(--el-text-color-secondary, #909399);
  font-size: 14px;
  margin-bottom: 16px;
}

/* Log */
.log-panel {
  padding-bottom: 16px;
}

.log-panel h3 {
  margin-bottom: 16px;
}

.log-list {
  max-height: 260px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-right: 8px;
}

.log-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 12px;
  color: #6b7280;
  font-family: 'SF Mono', 'Fira Code', monospace;
  line-height: 1.6;
}

.log-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #d1d5db;
  flex-shrink: 0;
  margin-top: 6px;
}

.log-item:last-child .log-dot {
  background: #6366f1;
}

/* Figure zoom hint */
.figure-item {
  cursor: pointer;
  position: relative;
}

.figure-img-wrapper {
  position: relative;
}

.figure-zoom-hint {
  position: absolute;
  bottom: 6px;
  right: 6px;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  border-radius: 4px;
  padding: 2px 4px;
  font-size: 14px;
  opacity: 0;
  transition: opacity 0.2s;
}

.figure-item:hover .figure-zoom-hint,
.figure-img-wrapper:hover .figure-zoom-hint {
  opacity: 1;
}

.figure-rotate-btn {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.figure-rotate-btn:hover {
  color: #6366f1;
}

/* Lightbox */
.lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  cursor: zoom-out;
}

.lightbox-img {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  cursor: default;
}

.lightbox-close {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.15);
  border: none;
  color: #fff;
  font-size: 28px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.lightbox-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* ===== Streaming Panel ===== */
.streaming-panel {
  border: 1px solid #c7d2fe;
  background: #fafaff;
}

.streaming-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.streaming-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6366f1;
  animation: blink 1.2s ease-in-out infinite;
}

.streaming-label {
  font-size: 13px;
  font-weight: 600;
  color: #4f46e5;
}

.streaming-content {
  max-height: 340px;
  overflow-y: auto;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 16px;
}

.streaming-text {
  font-family: 'SF Mono', 'Fira Code', 'Menlo', monospace;
  font-size: 12px;
  line-height: 1.7;
  color: #334155;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.streaming-cursor {
  color: #6366f1;
  font-weight: 700;
  animation: cursor-blink 0.8s step-end infinite;
}

@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* Responsive */
@media (max-width: 768px) {
  .steps-row {
    flex-wrap: wrap;
    gap: 8px;
  }

  .step-connector {
    display: none;
  }

  .step-card {
    flex: 1;
    min-width: 120px;
  }

  .audio-item {
    flex-direction: column;
    align-items: stretch;
  }

  .audio-player {
    width: 100%;
  }
}
</style>
