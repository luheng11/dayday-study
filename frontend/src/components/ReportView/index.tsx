/* 复盘报告内容视图（原型 03-2）：结算后报告页与「报告」Tab 共用 */

import { View, Text, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import Mascot from '../Mascot'
import type { ReportData } from '../../services/types'
import './index.scss'

interface ReportViewProps {
  report: ReportData
  topic: string
  /** 统计信息（结算页传入） */
  stats?: {
    correct: number
    total: number
    totalMs: number
    xpEarned: number
  }
}

export function formatDuration(totalMs: number): string {
  const totalSec = Math.max(0, Math.round(totalMs / 1000))
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return m > 0 ? `${m} 分 ${s} 秒` : `${s} 秒`
}

export default function ReportView({ report, topic, stats }: ReportViewProps) {
  const wrong = stats ? stats.total - stats.correct : 0
  const accuracy = report.accuracy

  const handlePlayAgain = () => {
    Taro.reLaunch({ url: '/pages/index/index' })
  }

  return (
    <View className='report-view'>
      <View className='rpt-head'>
        <Text className='font-display rpt-head-t'>📊 闯关复盘报告</Text>
        <Text className='tag rpt-topic'>{topic}</Text>
      </View>

      <View className='donut-wrap'>
        <View
          className='donut'
          style={{
            background: `conic-gradient(var(--ok) 0 ${accuracy}%, var(--line) ${accuracy}% 100%)`,
          }}
        >
          <View className='donut-num'>
            <Text className='donut-big'>{accuracy}</Text>
            <Text className='donut-small'>% 正确率</Text>
          </View>
        </View>
        <View className='donut-side'>
          {stats ? (
            <>
              <View className='donut-side-big'>
                {stats.correct} 题答对 · {wrong} 题还需巩固
              </View>
              <View className='donut-side-sm'>
                用时 {formatDuration(stats.totalMs)}
                {'\n'}获得 {stats.xpEarned} 星 · 成长值 +{stats.xpEarned}
              </View>
            </>
          ) : (
            <View className='donut-side-sm'>这次闯关的复盘都在这里了，随时回来看哦</View>
          )}
        </View>
      </View>

      <View className='three-line'>
        {report.three_line_summary.map((line, i) => (
          <View className='three-line-item' key={i}>
            <View className='three-line-no'>{i + 1}</View>
            <Text className='three-line-text'>{line}</Text>
          </View>
        ))}
      </View>

      <View className='pt-grid'>
        <View className='pt-box master'>
          <View className='pt-box-title'>✅ 掌握较好</View>
          <View className='pt-box-body'>
            {report.mastered_points.length > 0 ? (
              report.mastered_points.map((p, i) => <View key={i}>· {p}</View>)
            ) : (
              <View>· 继续加油，下次一定更好</View>
            )}
          </View>
        </View>
        <View className='pt-box weak'>
          <View className='pt-box-title'>⚠️ 需要加强</View>
          <View className='pt-box-body'>
            {report.weak_points.length > 0 ? (
              report.weak_points.map((p, i) => <View key={i}>· {p}</View>)
            ) : (
              <View>· 全部掌握，真棒！</View>
            )}
          </View>
        </View>
      </View>

      <View className='sect-title report-sec'>复习建议</View>
      <View className='advice'>
        {report.advice.map((item, i) => (
          <View className='advice-item' key={i}>
            {item}
          </View>
        ))}
      </View>

      <View className='quote-row'>
        <Mascot mood='smile' scale={0.62} />
        <View className='say tail-l quote-say'>「{report.share_quote}」</View>
      </View>

      <View className='report-footer'>
        <Button className='btn share-btn' openType='share'>
          📮 分享给好友
        </Button>
        <View className='btn ghost play-btn' onClick={handlePlayAgain}>
          🎯 再学一关
        </View>
      </View>
    </View>
  )
}
