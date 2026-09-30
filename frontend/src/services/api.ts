/* 请求封装：Taro.request + 统一响应解析 {code, message, data}
 * Phase 5：自动携带 JWT；401 清空本地凭证但不阻断核心流程（可选登录）
 */

import Taro from '@tarojs/taro'
import type {
  AnswerRecord,
  ApiEnvelope,
  LoginResponse,
  Question,
  QuizData,
  QuizDetailResponse,
  QuizHistoryList,
  ReportData,
  TaskStatusData,
  UserBrief,
  UserProfile,
  UserStats,
} from './types'

export class ApiError extends Error {
  code: number

  constructor(code: number, message: string) {
    super(message)
    this.code = code
  }
}

type Method = 'GET' | 'POST' | 'PUT'

/* ---- 登录态 ---- */

const TOKEN_KEY = 'cqq_token'
const USER_KEY = 'cqq_user'

export function getToken(): string {
  try {
    return Taro.getStorageSync(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setToken(token: string): void {
  Taro.setStorageSync(TOKEN_KEY, token)
}

export function clearToken(): void {
  Taro.removeStorageSync(TOKEN_KEY)
  Taro.removeStorageSync(USER_KEY)
}

export function getCachedUser(): UserBrief | null {
  try {
    const raw = Taro.getStorageSync(USER_KEY)
    return (raw as UserBrief) || null
  } catch {
    return null
  }
}

export function setCachedUser(user: UserBrief): void {
  Taro.setStorageSync(USER_KEY, user)
}

export function isLoggedIn(): boolean {
  return Boolean(getToken())
}

/* ---- 登录就绪机制：页面在登录流程结束后再发起鉴权请求 ---- */

let _loginResolve: () => void = () => {}
const _loginReady = new Promise<void>((resolve) => {
  _loginResolve = resolve
})

export function waitForLogin(): Promise<void> {
  return _loginReady
}

export function resolveLogin(): void {
  _loginResolve()
}

export async function request<T>(
  url: string,
  method: Method = 'GET',
  data?: unknown,
): Promise<T> {
  const header: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) {
    header.Authorization = `Bearer ${token}`
  }

  let resp
  try {
    resp = await Taro.request({
      url: `${API_BASE_URL}${url}`,
      method,
      data,
      timeout: 60000,
      header,
    })
  } catch (e) {
    const errMsg = (e as { errMsg?: string })?.errMsg || String(e)
    console.error('[api] request failed:', url, errMsg)
    if (errMsg.includes('timeout')) {
      throw new ApiError(-1, '请求超时了，请稍后重试')
    }
    throw new ApiError(-1, '网络开小差了，请检查网络后重试')
  }

  if (resp.statusCode < 200 || resp.statusCode >= 300) {
    throw new ApiError(resp.statusCode, '服务暂时不可用，请稍后重试')
  }

  const body = resp.data as ApiEnvelope<T>
  if (body.code === 4010) {
    // 凭证失效：清空本地登录态（核心出题/报告仍可匿名使用）
    clearToken()
    throw new ApiError(body.code, body.message)
  }
  if (body.code !== 0) {
    throw new ApiError(body.code, body.message)
  }
  return body.data
}

/* ---------- 接口 ---------- */

export function generateQuizSync(params: {
  user_input: string
  question_count: number
  difficulty: string
}): Promise<QuizData> {
  return request<QuizData>('/quiz/generate', 'POST', params)
}

export function generateQuizAsync(params: {
  user_input: string
  question_count: number
  difficulty: string
}): Promise<{ task_id: string }> {
  return request<{ task_id: string }>('/quiz/generate/async', 'POST', params)
}

export function pollQuizTask(taskId: string): Promise<TaskStatusData> {
  return request<TaskStatusData>(`/quiz/task/${taskId}`, 'GET')
}

export function generateReport(params: {
  quiz_id: string
  topic: string
  questions: Question[]
  answer_records: AnswerRecord[]
}): Promise<ReportData> {
  return request<ReportData>('/report/generate', 'POST', params)
}

/* ---------- 用户系统接口 ---------- */

export function loginByCode(code: string): Promise<LoginResponse> {
  return request<LoginResponse>('/user/login', 'POST', { code })
}

export function getUserProfile(): Promise<UserProfile> {
  return request<UserProfile>('/user/profile')
}

export function updateUserProfile(params: {
  nickname?: string
  avatar_url?: string
}): Promise<null> {
  return request<null>('/user/profile', 'PUT', params)
}

export type HistoryRange = 'all' | 'week' | 'month'

export function getQuizHistory(params: {
  page?: number
  pageSize?: number
  range?: HistoryRange
  onlyCompleted?: boolean
} = {}): Promise<QuizHistoryList> {
  const { page = 1, pageSize = 10, range = 'all', onlyCompleted = false } = params
  const query = `page=${page}&page_size=${pageSize}&range=${range}&only_completed=${onlyCompleted}`
  return request<QuizHistoryList>(`/user/quizzes?${query}`)
}

export function getQuizDetail(quizId: string): Promise<QuizDetailResponse> {
  return request<QuizDetailResponse>(`/user/quizzes/${quizId}`)
}

export function getUserStats(): Promise<UserStats> {
  return request<UserStats>('/user/stats')
}

/** 上传头像（微信 chooseAvatar 临时文件 → 后端持久化），返回新头像 URL */
export function uploadAvatar(filePath: string): Promise<{ avatar_url: string }> {
  const token = getToken()
  const header: Record<string, string> = {}
  if (token) {
    header.Authorization = `Bearer ${token}`
  }
  return new Promise((resolve, reject) => {
    Taro.uploadFile({
      url: `${API_BASE_URL}/user/avatar`,
      filePath,
      name: 'file',
      header,
      timeout: 60000,
      success: (res) => {
        try {
          const body = JSON.parse(res.data) as ApiEnvelope<{ avatar_url: string }>
          if (body.code === 4010) {
            clearToken()
            reject(new ApiError(body.code, body.message))
            return
          }
          if (body.code !== 0) {
            reject(new ApiError(body.code, body.message))
            return
          }
          resolve(body.data)
        } catch (e) {
          reject(new ApiError(-1, '头像上传响应解析失败'))
        }
      },
      fail: (err) => reject(new ApiError(-1, err.errMsg || '头像上传失败')),
    })
  })
}
