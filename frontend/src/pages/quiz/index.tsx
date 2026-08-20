/* 「闯关」Tab：有未完成闯关则续答，否则引导去首页 */

import { View, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import TabBar from '../../components/TabBar'
import { loadQuizProgress } from '../../services/storage'
import './index.scss'

export default function QuizTabPage() {
  useDidShow(() => {
    const progress = loadQuizProgress()
    if (progress) {
      Taro.redirectTo({ url: '/pages/gameplay/index' })
    }
  })

  return (
    <View className='page'>
      <View className='empty-state'>
        <Mascot mood='smile' floaty scale={0.9} />
        <Text className='empty-title'>现在还没有进行中的闯关</Text>
        <Text className='empty-desc'>
          去首页输入想学的知识，{'\n'}AI 马上帮你出题闯关！
        </Text>
        <View
          className='btn'
          style={{ marginTop: '40rpx', width: '300rpx' }}
          onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
        >
          去首页闯一关
        </View>
      </View>
      <TabBar active='quiz' />
    </View>
  )
}
