/* 底部 4 Tab（首页/闯关/报告/我的）：原型 tabbar 结构，自定义组件 + reLaunch 切换 */

import { View, Image, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { ICONS } from '../Icon/icons'
import './index.scss'

export type TabKey = 'home' | 'quiz' | 'report' | 'profile'

interface TabDef {
  key: TabKey
  label: string
  path: string
  icon: string
  iconOn: string
}

const TABS: TabDef[] = [
  {
    key: 'home',
    label: '首页',
    path: '/pages/index/index',
    icon: ICONS.tabHome,
    iconOn: ICONS.tabHomeOn,
  },
  {
    key: 'quiz',
    label: '闯关',
    path: '/pages/quiz/index',
    icon: ICONS.tabQuiz,
    iconOn: ICONS.tabQuizOn,
  },
  {
    key: 'report',
    label: '报告',
    path: '/pages/report/index',
    icon: ICONS.tabReport,
    iconOn: ICONS.tabReportOn,
  },
  {
    key: 'profile',
    label: '我的',
    path: '/pages/profile/index',
    icon: ICONS.tabProfile,
    iconOn: ICONS.tabProfileOn,
  },
]

interface TabBarProps {
  active: TabKey
}

export default function TabBar({ active }: TabBarProps) {
  const handleSwitch = (tab: TabDef) => {
    if (tab.key === active) return
    Taro.reLaunch({ url: tab.path })
  }

  return (
    <View className='tabbar'>
      {TABS.map((tab) => {
        const on = tab.key === active
        return (
          <View
            key={tab.key}
            className={`tab${on ? ' on' : ''}`}
            onClick={() => handleSwitch(tab)}
          >
            <Image className='tab-icon' src={on ? tab.iconOn : tab.icon} />
            <Text className='tab-label'>{tab.label}</Text>
            <View className='dotmark' />
          </View>
        )
      })}
    </View>
  )
}
