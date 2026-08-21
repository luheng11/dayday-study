/* 请求封装：Taro.request + 统一响应解析 {code, message, data} */

import Taro from '@tarojs/taro'
import type {
  AnswerRecord,
  ApiEnvelope,
  Question,
  QuizData,
  ReportData,
  TaskStatusData,
} from './types'

export class ApiError extends Error {
  code: number

  constructor(code: number, message: string) {
    super(message)
    this.code = code
  }
}

type Method = 'GET' | 'POST'

export async function request<T>(
  url: string,
  method: Method = 'GET',
  data?: unknown,
): Promise<T> {
  let resp
  try {
    resp = await Taro.request({
      url: `${API_BASE_URL}${url}`,
      method,
      data,
      timeout: 60000,
      header: { 'Content-Type': 'application/json' },
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
