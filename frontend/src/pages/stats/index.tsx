/* 学习统计页（严格按原型文件 04-2 数据统计）
 * 7 日正确率柱状图（绿≥80/黄60-79/浅黄<60，今日高亮）+ 知识点掌握度 + 连续打卡 + 薄弱知识点
 */

import { useCallback, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import { useDidShow } from '@tarojs/taro'
import TabBar from '../../components/TabBar'
import { getUserStats, isLoggedIn, waitForLogin } from '../../services/api'
import type { UserStats } from '../../services/types'
import './index.scss'

const STREAK_BADGE_DAYS = 7

function barClass(accuracy: number): string {
  if (accuracy >= 80) return 'hot'
  if (accuracy >= 60) return 'mid'
  return ''
}

function trackClass(accuracy: number): string {
  if (accuracy >= 80) return 'hi'
  if (accuracy >= 60) return 'mid'
  return 'lo'
}

function pvClass(accuracy: number): string {
  if (accuracy >= 80) return 'hi'
  if (accuracy >= 60) return 'mid'
  return 'lo'
}

export default function StatsPage() {
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loaded, setLoaded] = useState(false)

  const load = useCallback(() => {
    void waitForLogin().then(() => {
      if (!isLoggedIn()) {
        setLoaded(true)
        return
      }
      getUserStats()
        .then(setStats)
        .catch(() => {})
        .finally(() => setLoaded(true))
    })
  }, [])

  useDidShow(load)

  const todayIndex = stats ? stats.days.length - 1 : -1

  return (
    <View className='page'>
      <ScrollView scrollY className='sbody'>
        <View className='sbody-inner'>
          {/* 页面标题 */}
          <View className='page-title'>
            <Text className='font-display title-t'>📈 学习统计</Text>
            <View className='chip'>近 7 天</View>
          </View>

          {/* 7 日正确率柱状图 */}
          <View className='chart-card card'>
            <View className='chart-head'>
              <Text className='chart-h4'>每日闯关正确率</Text>
              <Text className='chart-avg'>平均 {stats?.average_accuracy_7d ?? 0}%</Text>
            </View>
            <View className='bars'>
              {(stats?.days ?? []).map((day, i) => (
                <View
                  key={day.date}
                  className={`bar-col${i === todayIndex ? ' today' : ''}`}
                >
                  {day.accuracy !== null ? (
                    <>
                      <Text className='bv'>{day.accuracy}</Text>
                      <View
                        className={`bar ${barClass(day.accuracy)}`}
                        style={{ height: `${Math.max(12, day.accuracy * 1.44)}rpx` }}
                      />
                    </>
                  ) : (
                    <>
                      <Text className='bv bv-none'>·</Text>
                      <View className='bar none' />
                    </>
                  )}
                  <Text className='bl'>{day.label}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 知识点掌握度 */}
          <View className='master-card card'>
            <Text className='chart-h4'>知识点掌握度</Text>
            <View className='master-body'>
              {stats && stats.mastery.length === 0 ? (
                <Text className='empty-line'>完成闯关后，这里会展示每个知识点的掌握情况</Text>
              ) : (
                (stats?.mastery ?? []).map((item) => (
                  <View className='mrow' key={item.knowledge_point}>
                    <Text className='kn'>{item.knowledge_point}</Text>
                    <View className='track'>
                      <View
                        className={`track-fill ${trackClass(item.accuracy)}`}
                        style={{ width: `${item.accuracy}%` }}
                      />
                    </View>
                    <Text className={`pv ${pvClass(item.accuracy)}`}>{item.accuracy}%</Text>
                  </View>
                ))
              )}
            </View>
          </View>

          {/* 连续打卡 */}
          <View className='streak'>
            <View className='streak-fire'>
              <Text>🔥</Text>
            </View>
            <View className='streak-txt'>
              <Text className='streak-b'>
                连续学习 {stats?.streak_days ?? 0} 天{stats && stats.streak_days > 0 ? ' 🔥' : ''}
              </Text>
              <Text className='streak-p'>
                {stats && stats.streak_days >= STREAK_BADGE_DAYS
                  ? `已解锁「七日之星」徽章，太棒了！`
                  : `再坚持 ${STREAK_BADGE_DAYS - (stats?.streak_days ?? 0)} 天就能解锁「七日之星」徽章！`}
              </Text>
            </View>
          </View>

          {/* 薄弱知识点 */}
          <View className='weak-list card'>
            <Text className='weak-h4'>⚠️ 需要回炉的知识点</Text>
            {stats && stats.weak_points.length === 0 ? (
              <Text className='weak-empty'>暂时没有薄弱知识点，继续保持！</Text>
            ) : (
              (stats?.weak_points ?? []).map((item) => (
                <View className='weak-item' key={item.knowledge_point}>
                  「{item.knowledge_point}」—— 建议再闯一次
                  {item.quiz_title ? `《${item.quiz_title}》` : '相关主题'}
                </View>
              ))
            )}
          </View>

          {loaded && !isLoggedIn() && (
            <View className='login-hint'>
              登录后可以查看你的学习统计，<Text className='login-hint-b'>去首页闯一关就能自动登录啦</Text>
            </View>
          )}
        </View>
      </ScrollView>

      <TabBar active='profile' />
    </View>
  )
}
