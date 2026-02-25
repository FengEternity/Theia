import axios from 'axios'
import type {
  PendingReview,
  PresetInfo,
  ReviewDecision,
  TaskConfig,
  TaskListResponse,
  TaskLogItem,
  TaskResponse,
  UserResponse,
  UserSettingResponse,
  VoiceInfo,
} from './types'

const http = axios.create({ baseURL: '/api' })

// ------------------------------------------------------------------
// 预设
// ------------------------------------------------------------------

export async function getPresets(): Promise<PresetInfo[]> {
  const { data } = await http.get<PresetInfo[]>('/presets')
  return data
}

// ------------------------------------------------------------------
// 声音
// ------------------------------------------------------------------

export async function getVoices(language?: string): Promise<VoiceInfo[]> {
  const { data } = await http.get<VoiceInfo[]>('/voices', {
    params: language ? { language } : undefined,
  })
  return data
}

export function getVoicePreviewUrl(voiceId: string, rate: number = 0): string {
  const base = `/api/voices/${encodeURIComponent(voiceId)}/preview`
  return rate !== 0 ? `${base}?rate=${rate}` : base
}

// ------------------------------------------------------------------
// 任务
// ------------------------------------------------------------------

export async function createTask(
  file: File,
  config: TaskConfig,
  userId: string = 'default',
): Promise<TaskResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('config', JSON.stringify(config))
  form.append('user_id', userId)
  const { data } = await http.post<TaskResponse>('/tasks', form)
  return data
}

export async function createTaskFromUrl(
  url: string,
  config: TaskConfig,
  userId: string = 'default',
): Promise<TaskResponse> {
  const { data } = await http.post<TaskResponse>('/tasks/from-url', {
    url,
    config,
    user_id: userId,
  })
  return data
}

export async function listTasks(params?: {
  user_id?: string
  page?: number
  size?: number
}): Promise<TaskListResponse> {
  const { data } = await http.get<TaskListResponse>('/tasks', { params })
  return data
}

export async function getTask(id: string): Promise<TaskResponse> {
  const { data } = await http.get<TaskResponse>(`/tasks/${id}`)
  return data
}

export async function deleteTask(id: string): Promise<void> {
  await http.delete(`/tasks/${id}`)
}

export async function cancelTask(id: string): Promise<void> {
  await http.post(`/tasks/${id}/cancel`)
}

export async function retryTask(id: string): Promise<TaskResponse> {
  const { data } = await http.post<TaskResponse>(`/tasks/${id}/retry`)
  return data
}

export async function getTaskLogs(id: string): Promise<TaskLogItem[]> {
  const { data } = await http.get<TaskLogItem[]>(`/tasks/${id}/logs`)
  return data
}

export async function getTaskScript(id: string): Promise<any> {
  const { data } = await http.get(`/tasks/${id}/script`)
  return data
}

export async function getTaskMarkdown(id: string): Promise<string> {
  const { data } = await http.get(`/tasks/${id}/markdown`, { responseType: 'text', transformResponse: [(d: string) => d] })
  return data
}

export async function getTaskSummary(id: string): Promise<any> {
  const { data } = await http.get(`/tasks/${id}/summary`)
  return data
}

export async function getTaskFigures(id: string): Promise<string[]> {
  const { data } = await http.get<string[]>(`/tasks/${id}/figures`)
  return data
}

export function getFigureUrl(id: string, filename: string): string {
  return `/api/tasks/${id}/figures/${encodeURIComponent(filename)}`
}

export function getAudioUrl(id: string, index: number): string {
  return `/api/tasks/${id}/audio/${index}`
}

export function getThumbnailUrl(id: string): string {
  return `/api/tasks/${id}/thumbnail`
}

export function getVideoUrl(id: string): string {
  return `/api/tasks/${id}/video`
}

export function getEventSourceUrl(id: string): string {
  return `/api/tasks/${id}/events`
}

// ------------------------------------------------------------------
// 人工审核（Interactive Mode）
// ------------------------------------------------------------------

export async function getPendingReview(id: string): Promise<PendingReview> {
  const { data } = await http.get<PendingReview>(`/tasks/${id}/pending-review`)
  return data
}

export async function approveStep(id: string, decision?: ReviewDecision): Promise<void> {
  await http.post(`/tasks/${id}/approve`, decision ?? { action: 'approve' })
}

export async function updateArtifact(
  id: string,
  artifactType: string,
  data: Record<string, unknown>,
): Promise<void> {
  await http.put(`/tasks/${id}/artifacts/${artifactType}`, data)
}

export async function resumeFromStep(id: string, step: string): Promise<TaskResponse> {
  const { data: resp } = await http.post<TaskResponse>(`/tasks/${id}/resume-from`, null, {
    params: { step },
  })
  return resp
}

export async function reanalyzeFigure(
  id: string,
  figurePath: string,
  caption?: string,
): Promise<Record<string, unknown>> {
  const { data } = await http.post(`/tasks/${id}/reanalyze-figure`, {
    figure_path: figurePath,
    caption: caption ?? '',
  })
  return data
}

export async function rerunFigures(id: string): Promise<{ figures: any[]; count: number }> {
  const { data } = await http.post(`/tasks/${id}/rerun-figures`)
  return data
}

export async function rotateFigure(
  id: string,
  figurePath: string,
  angle: number = 90,
): Promise<{ ok: boolean }> {
  const { data } = await http.post(`/tasks/${id}/rotate-figure`, {
    figure_path: figurePath,
    angle,
  })
  return data
}

export async function updateSummary(
  id: string,
  summary: Record<string, unknown>,
): Promise<void> {
  await http.post(`/tasks/${id}/update-summary`, summary)
}

// ------------------------------------------------------------------
// 用户
// ------------------------------------------------------------------

export async function listUsers(): Promise<UserResponse[]> {
  const { data } = await http.get<UserResponse[]>('/users')
  return data
}

export async function createUser(name: string, email?: string): Promise<UserResponse> {
  const { data } = await http.post<UserResponse>('/users', { name, email })
  return data
}

export async function getUser(id: string): Promise<UserResponse> {
  const { data } = await http.get<UserResponse>(`/users/${id}`)
  return data
}

export async function getUserSettings(userId: string): Promise<UserSettingResponse[]> {
  const { data } = await http.get<UserSettingResponse[]>(`/users/${userId}/settings`)
  return data
}

export async function updateUserSetting(
  userId: string,
  key: string,
  value: string | Record<string, unknown>,
): Promise<UserSettingResponse> {
  const { data } = await http.put<UserSettingResponse>(`/users/${userId}/settings`, { key, value })
  return data
}
