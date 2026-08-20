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

export interface ApiEnvelope<T = unknown> {
  code: number
  message: string
  data: T
}
