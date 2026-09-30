/* 复盘报告页：结算后跳转（无参）或历史回看（?quizId=xxx），支持微信转发分享 */

import { useEffect, useState } from 'react'
import { useRouter, useShareAppMessage } from '@tarojs/taro'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import ReportView from '../../components/ReportView'
import { getQuizDetail } from '../../services/api'
import { loadLatestReport, loadResult } from '../../services/storage'
import type { QuizDetailResponse } from '../../services/types'
import './index.scss'

/* 与后端/结算页一致的 XP 分值（沿用 M1：单选10/多选15/判断10，答对才有） */
const XP_BY_TYPE: Record<string, number> = { single: 10, multiple: 15, judge: 10 }

function computeXp(detail: QuizDetailResponse): number {
  const typeMap: Record<string, string> = {}
  for (const q of detail.questions) typeMap[q.id] = q.type
  return (detail.answer_records ?? []).reduce(
    (sum, r) => sum + (r.is_correct ? XP_BY_TYPE[typeMap[r.question_id] ?? ''] ?? 0 : 0),
    0,
  )
}

export default function ReportDetailPage() {
  const router = useRouter()
  const quizId = router.params.quizId
  const [detail, setDetail] = useState<QuizDetailResponse | null>(null)
  const [failed, setFailed] = useState(false)
  const [loading, setLoading] = useState(Boolean(quizId))

  /* 历史回看：从服务端拉完整详情 */
  useEffect(() => {
    if (!quizId) return
    getQuizDetail(quizId)
      .then(setDetail)
      .catch(() => setFailed(true))
      .finally(() => setLoading(false))
  }, [quizId])

  const localStored = loadLatestReport()
  const localResult = loadResult()

  useShareAppMessage(() => {
    if (detail?.report) {
      return {
        title: `「${detail.title}」${detail.report.share_quote}`,
        path: `/pages/reportDetail/index?quizId=${detail.quiz_id}`,
      }
    }
    if (localStored) {
      return {
        title: `「${localStored.topic}」${localStored.report.share_quote}`,
        path: '/pages/index/index',
      }
    }
    return { title: '闯关学堂 · AI 知识闯关', path: '/pages/index/index' }
  })

  /* ---- 加载中 ---- */
  if (loading) {
    return (
      <View className='page'>
        <View className='empty-state'>
          <Mascot mood='think' floaty scale={0.9} />
          <Text className='empty-text'>正在翻开你的报告…</Text>
        </View>
      </View>
    )
  }

  /* ---- 历史回看结果 ---- */
  if (quizId) {
    if (failed || !detail) {
      return (
        <View className='page'>
          <View className='empty-state'>
            <Mascot mood='sad' scale={0.9} />
            <Text className='empty-text'>报告没找到</Text>
            <Text className='empty-desc'>这条记录可能已经被清理，{'\n'}去闯一关新的吧！</Text>
            <View
              className='btn'
              style={{ marginTop: '40rpx', width: '300rpx' }}
              onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
            >
              去首页闯关
            </View>
          </View>
        </View>
      )
    }

    if (!detail.report) {
      return (
        <View className='page'>
          <View className='empty-state'>
            <Mascot mood='think' scale={0.9} />
            <Text className='empty-text'>这次闯关还没有报告</Text>
            <Text className='empty-desc'>
              「{detail.title}」只完成了答题，{'\n'}报告生成时断开了，重闯一次吧！
            </Text>
            <View
              className='btn'
              style={{ marginTop: '40rpx', width: '300rpx' }}
              onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
            >
              去首页闯关
            </View>
          </View>
        </View>
      )
    }

    const records = detail.answer_records ?? []
    const correct = records.filter((r) => r.is_correct).length
    const totalMs = records.reduce((sum, r) => sum + r.duration_ms, 0)
    return (
      <View className='page'>
        <ScrollView scrollY className='sbody'>
          <View className='sbody-inner'>
            <View className='history-tip'>
              <Text>📅 {detail.created_at} 的闯关记录</Text>
            </View>
            <ReportView
              report={detail.report}
              topic={detail.title}
              stats={{ correct, total: records.length, totalMs, xpEarned: computeXp(detail) }}
            />
          </View>
        </ScrollView>
      </View>
    )
  }

  /* ---- 结算后进入（M1 行为，读本地） ---- */
  const stored = localStored
  if (!stored) {
    return (
      <View className='page'>
        <View className='empty-state'>
          <Mascot mood='smile' scale={0.9} />
          <Text className='empty-text'>报告不见了，先去闯一关吧</Text>
          <View
            className='btn'
            style={{ marginTop: '32rpx', width: '300rpx' }}
            onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
          >
            去首页闯关
          </View>
        </View>
      </View>
    )
  }

  const stats = localResult
    ? {
        correct: localResult.correctCount,
        total: localResult.quiz.questions.length,
        totalMs: localResult.totalMs,
        xpEarned: localResult.xpEarned,
      }
    : undefined

  return (
    <View className='page'>
      <ScrollView scrollY className='sbody'>
        <View className='sbody-inner'>
          <ReportView report={stored.report} topic={stored.topic} stats={stats} />
        </View>
      </ScrollView>
    </View>
  )
}
