/* 复盘报告页：结算后跳转进入，支持微信转发分享 */

import { useShareAppMessage } from '@tarojs/taro'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import ReportView from '../../components/ReportView'
import { loadLatestReport, loadResult } from '../../services/storage'
import './index.scss'

export default function ReportDetailPage() {
  const stored = loadLatestReport()
  const result = loadResult()

  useShareAppMessage(() => {
    return {
      title: stored ? `「${stored.topic}」${stored.report.share_quote}` : '闯关学堂 · AI 知识闯关',
      path: '/pages/index/index',
    }
  })

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

  const stats = result
    ? {
        correct: result.correctCount,
        total: result.quiz.questions.length,
        totalMs: result.totalMs,
        xpEarned: result.xpEarned,
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
