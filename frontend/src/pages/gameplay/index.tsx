/* 闯关答题页：单选/多选/判断 + 即时判题 + 讲解气泡（严格按原型文件 02） */

import { useEffect, useMemo, useState } from 'react'
import { View, Text, Image, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import { ICONS } from '../../components/Icon/icons'
import type { AnswerRecord, Question, QuizData } from '../../services/types'
import {
  clearQuizProgress,
  loadQuizProgress,
  saveQuizProgress,
  saveResult,
} from '../../services/storage'
import './index.scss'

const XP_BY_TYPE: Record<string, number> = { single: 10, multiple: 15, judge: 10 }

const TYPE_LABEL: Record<string, string> = {
  single: '单选题',
  multiple: '多选题',
  judge: '判断题',
}

const TYPE_TAG_BG: Record<string, string> = {
  single: 'var(--pri-soft)',
  multiple: '#E4F0FF',
  judge: '#FFE9D6',
}

function xpOfType(type: string): number {
  return XP_BY_TYPE[type] ?? 10
}

export default function GameplayPage() {
  const [progress, setProgress] = useState(() => loadQuizProgress())
  const [selected, setSelected] = useState<string[]>([])
  const [submitted, setSubmitted] = useState(false)
  const [questionStartAt, setQuestionStartAt] = useState(Date.now())

  const quiz: QuizData | null = progress?.quiz ?? null
  const currentIndex = progress?.currentIndex ?? 0
  const answerRecords = progress?.answerRecords ?? []
  const heartsLost = progress?.heartsLost ?? 0

  const question: Question | null = quiz?.questions[currentIndex] ?? null
  const total = quiz?.questions.length ?? 0

  const isLast = currentIndex === total - 1
  const nextIsLast = currentIndex === total - 2

  const lastRecord = answerRecords[answerRecords.length - 1]

  const correctCount = useMemo(
    () => answerRecords.filter((r) => r.is_correct).length,
    [answerRecords],
  )

  useEffect(() => {
    if (quiz?.title) {
      Taro.setNavigationBarTitle({ title: `${quiz.title} · 闯关中` })
    }
  }, [quiz?.title])

  if (!quiz || !question) {
    return (
      <View className='page'>
        <View className='empty-state'>
          <Mascot mood='sad' scale={0.9} />
          <Text className='empty-text'>题目加载失败</Text>
          <View
            className='btn'
            style={{ marginTop: '32rpx', width: '300rpx' }}
            onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
          >
            返回首页
          </View>
        </View>
      </View>
    )
  }

  const persist = (next: {
    currentIndex?: number
    answerRecords?: AnswerRecord[]
    heartsLost?: number
  }) => {
    const merged = {
      quiz,
      currentIndex: next.currentIndex ?? currentIndex,
      answerRecords: next.answerRecords ?? answerRecords,
      heartsLost: next.heartsLost ?? heartsLost,
      startAt: progress?.startAt ?? Date.now(),
    }
    setProgress(merged)
    saveQuizProgress(merged)
  }

  const handleOptionTap = (key: string) => {
    if (submitted) return
    if (question.type === 'multiple') {
      setSelected((prev) =>
        prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
      )
    } else {
      setSelected([key])
    }
  }

  const handleSubmit = () => {
    if (selected.length === 0 || submitted) return

    const isCorrect =
      question.answer.length === selected.length &&
      question.answer.every((a) => selected.includes(a))

    const record: AnswerRecord = {
      question_id: question.id,
      selected_answers: [...selected],
      is_correct: isCorrect,
      duration_ms: Date.now() - questionStartAt,
    }

    const nextRecords = [...answerRecords, record]
    persist({
      answerRecords: nextRecords,
      heartsLost: isCorrect ? heartsLost : heartsLost + 1,
    })
    setSubmitted(true)
  }

  const handleNext = () => {
    if (!isLast) {
      persist({ currentIndex: currentIndex + 1 })
      setSelected([])
      setSubmitted(false)
      setQuestionStartAt(Date.now())
      return
    }

    // 全部完成 → 结算页
    const xpEarned = answerRecords.reduce(
      (sum, r) => sum + (r.is_correct ? xpOfType(questionTypeOf(r)) : 0),
      0,
    )
    saveResult({
      quiz,
      answerRecords,
      correctCount,
      heartsLost,
      totalMs: Date.now() - (progress?.startAt ?? Date.now()),
      xpEarned,
      finishedAt: Date.now(),
    })
    clearQuizProgress()
    Taro.redirectTo({ url: '/pages/result/index' })
  }

  const questionTypeOf = (r: AnswerRecord): string => {
    const q = quiz.questions.find((qq) => qq.id === r.question_id)
    return q?.type ?? 'single'
  }

  const handleBack = () => {
    // 进度已实时落盘，返回后可经「闯关」Tab 续答。
    // 若栈里没有上一页（从「闯关」Tab 重定向进入），回首页避免循环。
    const pages = Taro.getCurrentPages()
    if (pages.length <= 1) {
      Taro.reLaunch({ url: '/pages/index/index' })
      return
    }
    Taro.navigateBack()
  }

  const isCorrectKey = (key: string) => question.answer.includes(key)
  const isSelectedKey = (key: string) => selected.includes(key)

  const optionClass = (key: string): string => {
    if (!submitted) return isSelectedKey(key) ? 'opt picked' : 'opt'
    if (isCorrectKey(key)) return 'opt correct'
    if (isSelectedKey(key)) return 'opt wrong'
    return 'opt dim'
  }

  const isLastRecordCorrect = !!lastRecord?.is_correct

  return (
    <View className='page'>
      <ScrollView scrollY className='sbody'>
        <View className='sbody-inner'>
          {submitted && question.type !== 'judge' && (
            <View className={`burst${isLastRecordCorrect ? '' : ' bad'}`} />
          )}

          <View className='qtop'>
            <View className='qback' onClick={handleBack}>
              <Image className='qback-icon' src={ICONS.back} />
            </View>
            <View className='qlevel'>
              第 <Text className='qlevel-num'>{currentIndex + 1}</Text> / {total} 关
            </View>
            <View className='hearts'>
              {[0, 1, 2].map((i) => (
                <Image
                  key={i}
                  className='heart-icon'
                  src={i < 3 - heartsLost ? ICONS.heart : ICONS.heartLost}
                />
              ))}
            </View>
          </View>

          <View className='segs'>
            {quiz.questions.map((q, i) => (
              <View
                key={q.id}
                className={`seg${i < currentIndex ? ' done' : i === currentIndex ? ' cur' : ''}`}
              />
            ))}
          </View>

          <View className={`qcard${question.type === 'judge' ? ' qcard-center' : ''}`}>
            <View className='qnum'>Q{currentIndex + 1}</View>
            <View className={`qmeta${question.type === 'judge' ? ' qmeta-center' : ''}`}>
              <Text className='tag qtype-tag' style={{ background: TYPE_TAG_BG[question.type] }}>
                {TYPE_LABEL[question.type]}
              </Text>
              <Text className='kp'>知识点：{question.knowledge_point}</Text>
            </View>
            <Text className='stem'>{question.stem}</Text>
            {question.type === 'judge' && (
              <View className='judge-hint'>✋ 想一想：先自己判断，再作答哦</View>
            )}
          </View>

          {question.type === 'judge' ? (
            <View className='judge'>
              {(
                [
                  ['A', '✓', '对 · 正确', 'true'],
                  ['B', '✗', '错 · 不对', 'false'],
                ] as const
              ).map(([key, mark, label, cls]) => {
                const picked = isSelectedKey(key)
                const correct = isCorrectKey(key)
                let clsName = `jbtn ${cls}`
                if (submitted) {
                  if (correct) clsName += ' correct'
                  else if (picked) clsName += ' wrong'
                  else clsName += ' ghosty'
                } else if (picked) {
                  clsName += ' hover'
                }
                return (
                  <View key={key} className={clsName} onClick={() => handleOptionTap(key)}>
                    <View className='jbtn-ic'>{mark}</View>
                    <Text className='jbtn-lb'>{label}</Text>
                  </View>
                )
              })}
            </View>
          ) : (
            <View className='opts'>
              {question.options.map((opt) => (
                <View
                  key={opt.key}
                  className={optionClass(opt.key)}
                  onClick={() => handleOptionTap(opt.key)}
                >
                  {question.type === 'multiple' ? (
                    <View className='cb'>{submitted && isCorrectKey(opt.key) ? '✓' : ''}</View>
                  ) : (
                    <View className='key'>{opt.key}</View>
                  )}
                  <Text className='opt-txt'>{opt.text}</Text>
                  {submitted && isCorrectKey(opt.key) && <View className='mark'>✓</View>}
                  {submitted && !isCorrectKey(opt.key) && isSelectedKey(opt.key) && (
                    <View className='mark'>✗</View>
                  )}
                </View>
              ))}
            </View>
          )}

          {submitted && (
            <View className='feedback'>
              <Mascot mood={isLastRecordCorrect ? 'cheer' : 'smile'} scale={0.8} />
              <View className={`say fb-say ${isLastRecordCorrect ? 'ok' : 'bad'}`}>
                <View className='fb-title'>
                  {isLastRecordCorrect ? '叮！答对啦 🎉' : '哎呀，差一点点！'}
                </View>
                <Text>{question.explanation}</Text>
                <View>
                  <Text className='tag fb-kp'>📌 {question.knowledge_point}</Text>
                </View>
              </View>
            </View>
          )}

          <View className='footer-actions'>
            {submitted && isLastRecordCorrect && (
              <View className='xpfloat'>⭐ +{xpOfType(question.type)}</View>
            )}
            {submitted ? (
              <View className='btn big ok' onClick={handleNext}>
                {isLast ? '查看通关报告 →' : nextIsLast ? '最后一关 →' : '下一关 →'}
              </View>
            ) : (
              <>
                <View
                  className={`btn big${selected.length > 0 ? '' : ' disabled'}`}
                  onClick={handleSubmit}
                >
                  选好答案，点击提交
                </View>
                <View className='hintline'>
                  {isLast
                    ? '最后一关！答完就能看到通关报告 🎁'
                    : '选择后立即判分，答对答错都有讲解哦'}
                </View>
              </>
            )}
          </View>
        </View>
      </ScrollView>
    </View>
  )
}
