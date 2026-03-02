export type TaskStage =
  | 'pending'
  | 'parsing'
  | 'extracting'
  | 'scripting'
  | 'tts'
  | 'rendering'
  | 'completed'
  | 'failed'

export interface TaskResponse {
  id: string
  filename: string
  stage: TaskStage
  progress: number
  stage_label: string
  video_path: string | null
  thumbnail_path: string | null
  error: string | null
  paper_title: string | null
  user_id: string | null
  created_at: string
  updated_at: string
}

export interface TaskListResponse {
  items: TaskResponse[]
  total: number
  page: number
  size: number
}

export interface QualityDetail {
  score: number
  max: number
  threshold: number
  passed: boolean | null
  detail: Record<string, unknown> | null
  phase: 'pre_repair' | 'post_repair' | null
}

export interface TaskEvent {
  stage: TaskStage
  progress: number
  stage_label: string
  message: string
  video_path: string | null
  error: string | null
  token_delta?: string
  token_step?: string
  quality_detail?: QualityDetail
}

export interface TaskLogItem {
  stage: string
  progress: number
  message: string
  created_at: string
}

export interface PresetInfo {
  key: string
  label: string
  width: number
  height: number
}

export interface TaskConfig {
  preset: string
  language: string
  fps: number
  skip_tts: boolean
  voice: string | null
  speech_rate: number
  narration_style: string
  theme: string
  extract_mode?: string
  interactive_mode?: boolean
}

export interface PendingReview {
  step: string
  artifact_type?: string
  data?: Record<string, unknown>
  message: string
  quality_score?: number
  quality_max?: number
  quality_threshold?: number
  quality_passed?: boolean
  quality_l1?: Record<string, number>
  quality_l2?: Record<string, number>
  quality_weaknesses?: string[]
  quality_detail?: Record<string, number>
}

export interface ReviewDecision {
  action: 'approve' | 'edit' | 'retry'
  data?: Record<string, unknown>
}

export interface VoiceInfo {
  id: string
  name: string
  language: string
  gender: string
  preview_text: string
}

export interface UserResponse {
  id: string
  name: string
  email: string | null
  created_at: string
}

export interface UserSettingResponse {
  key: string
  value: string
  updated_at: string
}
