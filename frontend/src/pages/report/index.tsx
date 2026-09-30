/* 「报告」Tab：历史报告库（严格按原型文件 04-3）
 * 报告卡 = 主题 + 时间 + 迷你环形正确率 + 三句总结摘要；按成绩给动作：
 * 低分「重闯这一关」/ 中分「再次复习」/ 高分「查看完整报告」；每份可转发分享
 * 未登录：保持 M1 行为，展示本地最近一份报告
 */

import { useCallback, useState } from 'react'
import { View, Text, ScrollView, Button } from '@tarojs/components'
import Taro, { useDidShow, useShareAppMessage } from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import TabBar from '../../components/TabBar'
import ReportView from '../../components/ReportView'
import { generateQuizAsync, getQuizHistory, isLoggedIn, pollQuizTask, waitForLogin } from '../../services/api'
import { loadLatestReport, saveQuizProgress } from '../../services/storage'
import type { QuizHistoryItem } from '../../services/types'
import './index.scss'

const POLL_INTERVAL = 1200
const POLL_TIMEOUT = 60000

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

function donutClass(accuracy: number): string {
  if (accuracy >= 80) return ''
  if (accuracy >= 60) return 'mid'
  return 'low'
}

/* 按成绩的动作按钮文案 */
function actionLabel(accuracy: number): string {
  if (accuracy < 60) return '🎯 重闯这一关'
  if (accuracy < 80) return '📖 再次复习'
  return '📖 查看完整报告'
}

export default function ReportTabPage() {
  const [items, setItems] = useState<QuizHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [shareTarget, setShareTarget] = useState<QuizHistoryItem | null>(null)
  const [retrying, setRetrying] = useState(false)
  const [loggedIn, setLoggedIn] = useState(isLoggedIn())

  const localReport = loadLatestReport()

  const loadList = useCallback(
    async (p: number, reset: boolean) => {
      if (!isLoggedIn()) {
        setLoggedIn(false)
        return
      }
      setLoggedIn(true)
      setLoading(true)
      try {
        const data = await getQuizHistory({ page: p, pageSize: 10, onlyCompleted: true })
        setItems((prev) => (reset ? data.items : [...prev, ...data.items]))
        setTotal(data.total)
        setPage(p)
        setHasMore(data.items.length >= 10 && p * 10 < data.total)
      } catch {
        /* 保持现状 */
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  useDidShow(() => {
    void waitForLogin().then(() => loadList(1, true))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  })

  useShareAppMessage(() => {
    const target = shareTarget
    if (target) {
      const quote = target.report_snippet || '我在闯关学堂的学习报告'
      return {
        title: `「${target.title}」正确率 ${Math.round(target.accuracy)}%｜${quote}`,
        path: `/pages/reportDetail/index?quizId=${target.quiz_id}`,
      }
    }
    return {
      title: '闯关学堂 · AI 知识闯关',
      path: '/pages/index/index',
    }
  })

  const handleLoadMore = () => {
    if (!hasMore || loading) return
    loadList(page + 1, false)
  }

  const handleViewDetail = (quizId: string) => {
    Taro.navigateTo({ url: `/pages/reportDetail/index?quizId=${quizId}` })
  }

  /* 低分「重闯这一关」：用原主题重新出题并进入闯关页 */
  const handleRetry = async (item: QuizHistoryItem) => {
    if (retrying || !item.user_input) return
    setRetrying(true)
    Taro.showLoading({ title: 'AI 正在出题…' })
    try {
      const { task_id } = await generateQuizAsync({
        user_input: item.user_input,
        question_count: Math.min(10, Math.max(3, item.question_count || 5)),
        difficulty: 'medium',
      })
      const deadline = Date.now() + POLL_TIMEOUT
      while (Date.now() < deadline) {
        await sleep(POLL_INTERVAL)
        const status = await pollQuizTask(task_id)
        if (status.status === 'completed' && status.result) {
          saveQuizProgress({
            quiz: status.result,
            currentIndex: 0,
            answerRecords: [],
            heartsLost: 0,
            startAt: Date.now(),
          })
          Taro.hideLoading()
          Taro.navigateTo({ url: '/pages/gameplay/index' })
          return
        }
        if (status.status === 'failed') break
      }
      Taro.hideLoading()
      Taro.showToast({ title: '出题失败，请重试', icon: 'none' })
    } catch {
      Taro.hideLoading()
      Taro.showToast({ title: '出题失败，请重试', icon: 'none' })
    } finally {
      setRetrying(false)
    }
  }

  const handleCardAction = (item: QuizHistoryItem) => {
    if (item.accuracy < 60) {
      void handleRetry(item)
    } else {
      handleViewDetail(item.quiz_id)
    }
  }

  /* ---------- 未登录：本地最近报告（M1 行为） ---------- */
  if (!loggedIn) {
    return (
      <View className='page'>
        <ScrollView scrollY className='sbody'>
          <View className='sbody-inner'>
            {localReport ? (
              <ReportView report={localReport.report} topic={localReport.topic} />
            ) : (
              <View className='empty-state'>
                <Mascot mood='think' floaty scale={0.9} />
                <Text className='empty-title'>还没有报告哦</Text>
                <Text className='empty-desc'>
                  完成一次闯关，就能拿到专属的{'\n'}复盘报告啦
                </Text>
                <View
                  className='btn'
                  style={{ marginTop: '40rpx', width: '300rpx' }}
                  onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
                >
                  去首页闯一关
                </View>
              </View>
            )}
          </View>
        </ScrollView>
        <TabBar active='report' />
      </View>
    )
  }

  /* ---------- 已登录：报告库 ---------- */
  return (
    <View className='page'>
      <ScrollView scrollY className='sbody' onScrollToLower={handleLoadMore} lowerThreshold={120}>
        <View className='sbody-inner'>
          <View className='page-title'>
            <Text className='font-display title-t'>🗂️ 我的报告库</Text>
            <View className='tag'>共 {total} 份</View>
          </View>

          {items.length === 0 && !loading ? (
            <View className='empty-note'>
              完成一次闯关，报告就会收进这里{'\n'}成为你的「轻量知识档案」📚
            </View>
          ) : (
            items.map((item) => (
              <View className='rptcard' key={item.quiz_id}>
                <View className='rc-head'>
                  <View className='rc-head-main'>
                    <View className='rc-topic'>{item.title}</View>
                    <View className='rc-date'>
                      {item.created_at} · {item.question_count} 题
                    </View>
                  </View>
                  <View
                    className={`mini-donut ${donutClass(item.accuracy)}`}
                    style={{
                      background: `conic-gradient(var(--dc, #3dbe6b) 0 ${Math.round(
                        item.accuracy,
                      )}%, var(--line, #efe2c2) ${Math.round(item.accuracy)}% 100%)`,
                    }}
                  >
                    <Text>{Math.round(item.accuracy)}%</Text>
                  </View>
                </View>

                {item.report_snippet && (
                  <View className='snippet'>「{item.report_snippet}」</View>
                )}

                <View className='rc-foot'>
                  <Button
                    className={`btn rc-action${item.accuracy >= 80 ? '' : item.accuracy >= 60 ? ' ghost' : ''}`}
                    onClick={() => handleCardAction(item)}
                  >
                    {actionLabel(item.accuracy)}
                  </Button>
                  <Button
                    className='rc-share'
                    openType='share'
                    onClick={() => setShareTarget(item)}
                  >
                    <Text className='rc-share-icon'>↗️</Text>
                  </Button>
                </View>
              </View>
            ))
          )}

          {loading && <View className='empty-note'>加载中…</View>}
          {items.length > 0 && (
            <View className='empty-note'>{hasMore ? '下拉加载更早的报告' : '到底啦'}</View>
          )}
        </View>
      </ScrollView>

      <TabBar active='report' />
    </View>
  )
}
