/* 「我的」Tab：M1 空态页（个人学习后台为 Phase 5，见方案设计） */

import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import TabBar from '../../components/TabBar'
import { getXpTotal } from '../../services/storage'
import './index.scss'

export default function ProfilePage() {
  const [xp] = useState(() => getXpTotal())

  return (
    <View className='page'>
      <View className='profile'>
        <View className='avatar'>
          <View className='avatar-hair h1' />
          <View className='avatar-hair h2' />
          <View className='avatar-eye l' />
          <View className='avatar-eye r' />
          <View className='avatar-blush l' />
          <View className='avatar-blush r' />
          <View className='avatar-mouth' />
        </View>
        <View>
          <View className='name'>小闯同学</View>
          <View className='lvl'>
            <View className='lvl-chip'>Lv.1 闯关新星</View>
            <Text className='xpt'>成长值 {xp}</Text>
          </View>
        </View>
      </View>

      <View className='empty-card card'>
        <Text className='empty-title'>学习档案正在建设中</Text>
        <Text className='empty-desc'>
          个人学习记录、数据统计与历史报告库{'\n'}将在下一个版本开放，敬请期待！
        </Text>
        <View
          className='btn'
          style={{ marginTop: '40rpx', width: '320rpx' }}
          onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
        >
          先去闯一关 🎯
        </View>
      </View>

      <TabBar active='profile' />
    </View>
  )
}
