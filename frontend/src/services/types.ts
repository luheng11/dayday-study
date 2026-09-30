/* 与后端 app/models 数据协议一一对应 */

export type QuestionType = 'single' | 'multiple' | 'judge'
export type Difficulty = 'easy' | 'medium' | 'hard' | 'mixed'

export interface QuestionOption {
  key: string
  text: string
}

export interface Question {
  id: string
  type: QuestionType
  stem: string
  options: QuestionOption[]
  answer: string[]
  explanation: string
  knowledge_point: string
  difficulty: Difficulty
  image_url: string | null
}

export interface QuizData {
  quiz_id: string
  title: string
  summary: string
  questions: Question[]
}

export interface AnswerRecord {
  question_id: string
  selected_answers: string[]
  is_correct: boolean
  duration_ms: number
}

export interface ReportData {
  accuracy: number
  mastered_points: string[]
  weak_points: string[]
  three_line_summary: string[]
  advice: string[]
  share_quote: string
}

export interface TaskStatusData {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  result: QuizData | null
  error_message: string | null
}

/* ---------- 用户系统（与后端 app/models/user.py 一一对应） ---------- */

export interface UserBrief {
  id: number
  nickname: string
  avatar_url: string
  total_xp: number
}

export interface LoginResponse {
  token: string
  user: UserBrief
}

export interface LevelInfo {
  level: number
  title: string
  level_start_xp: number
  level_end_xp: number | null
  is_max: boolean
}

export interface UserProfile {
  id: number
  nickname: string
  avatar_url: string
  total_xp: number
  quiz_count: number
  correct_count: number
  average_accuracy: number
  week_quiz_count: number
  streak_days: number
  level: LevelInfo
}

export interface QuizHistoryItem {
  quiz_id: string
  title: string
  user_input: string | null
  accuracy: number
  question_count: number
  duration_ms: number
  created_at: string
  has_report: boolean
  report_snippet: string | null
}

export interface QuizHistoryList {
  items: QuizHistoryItem[]
  total: number
  page: number
  page_size: number
}

export interface QuizDetailResponse {
  quiz_id: string
  title: string
  summary: string
  user_input: string | null
  questions: Question[]
  answer_records: AnswerRecord[] | null
  report: ReportData | null
  created_at: string
}

export interface DailyStat {
  date: string
  label: string
  accuracy: number | null
  quiz_count: number
}

export interface MasteryItem {
  knowledge_point: string
  accuracy: number
}

export interface WeakPointItem {
  knowledge_point: string
  accuracy: number
  quiz_title: string
}

export interface UserStats {
  days: DailyStat[]
  average_accuracy_7d: number
  mastery: MasteryItem[]
  weak_points: WeakPointItem[]
  streak_days: number
}

export interface ApiEnvelope<T = unknown> {
  code: number
  message: string
  data: T
}
