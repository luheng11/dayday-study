/* 本地存储：闯关进度续答、最近报告、成长值（M1 无账号体系，用本地沉淀） */

import Taro from '@tarojs/taro'
import type { AnswerRecord, QuizData, ReportData } from './types'

const KEYS = {
  CURRENT_QUIZ: 'cqq_current_quiz', // 进行中的闯关快照
  LATEST_REPORT: 'cqq_latest_report', // 最近一份报告
  XP_TOTAL: 'cqq_xp_total', // 累计成长值（⭐）
  RESULT: 'cqq_last_result', // 最近一次闯关结算数据
}

export interface QuizProgress {
  quiz: QuizData
  currentIndex: number
  answerRecords: AnswerRecord[]
  heartsLost: number
  startAt: number
}

export interface QuizResult {
  quiz: QuizData
  answerRecords: AnswerRecord[]
  correctCount: number
  heartsLost: number
  totalMs: number
  xpEarned: number
  finishedAt: number
  /** 成长值是否已入账（防重复累加） */
  credited?: boolean
}

export function saveResult(result: QuizResult): void {
  Taro.setStorageSync(KEYS.RESULT, result)
}

export function loadResult(): QuizResult | null {
  try {
    const raw = Taro.getStorageSync(KEYS.RESULT)
    if (!raw || !(raw as QuizResult).quiz) return null
    return raw as QuizResult
  } catch {
    return null
  }
}

export function clearResult(): void {
  Taro.removeStorageSync(KEYS.RESULT)
}

export function saveQuizProgress(progress: QuizProgress): void {
  Taro.setStorageSync(KEYS.CURRENT_QUIZ, progress)
}

export function loadQuizProgress(): QuizProgress | null {
  try {
    const raw = Taro.getStorageSync(KEYS.CURRENT_QUIZ)
    if (!raw) return null
    const progress = raw as QuizProgress
    // 校验基本结构，防脏数据
    if (!progress.quiz || !Array.isArray(progress.quiz.questions)) return null
    return progress
  } catch {
    return null
  }
}

export function clearQuizProgress(): void {
  Taro.removeStorageSync(KEYS.CURRENT_QUIZ)
}

export function saveLatestReport(report: ReportData, topic: string, createdAt: number): void {
  Taro.setStorageSync(KEYS.LATEST_REPORT, { report, topic, createdAt })
}

export interface StoredReport {
  report: ReportData
  topic: string
  createdAt: number
}

export function loadLatestReport(): StoredReport | null {
  try {
    const raw = Taro.getStorageSync(KEYS.LATEST_REPORT)
    return (raw as StoredReport) || null
  } catch {
    return null
  }
}

export function getXpTotal(): number {
  try {
    const v = Taro.getStorageSync(KEYS.XP_TOTAL)
    return typeof v === 'number' ? v : 0
  } catch {
    return 0
  }
}

export function addXp(delta: number): number {
  const total = getXpTotal() + delta
  Taro.setStorageSync(KEYS.XP_TOTAL, total)
  return total
}
