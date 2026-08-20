/* 「报告」Tab：展示最近一份报告；无报告则空态引导 */

import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useShareAppMessage } from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import TabBar from '../../components/TabBar'
import ReportView from '../../components/ReportView'
import { loadLatestReport } from '../../services/storage'
import './index.scss'

export default function ReportTabPage() {
  const stored = loadLatestReport()

  useShareAppMessage(() => {
    return {
      title: stored ? `「${stored.topic}」${stored.report.share_quote}` : '闯关学堂 · AI 知识闯关',
      path: '/pages/index/index',
    }
  })

  return (
    <View className='page'>
      <ScrollView scrollY className='sbody'>
        <View className='sbody-inner'>
          {stored ? (
            <ReportView report={stored.report} topic={stored.topic} />
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
