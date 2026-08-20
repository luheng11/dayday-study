/* 吉祥物「闯闯」：纯 View 组合，严格按原型 mascot 结构（文件 01/02） */

import { View } from '@tarojs/components'
import './index.scss'

export type MascotMood = 'smile' | 'cheer' | 'think' | 'sad'

interface MascotProps {
  mood?: MascotMood
  /** 相对基准 86x102px 的缩放 */
  scale?: number
  /** 上下漂浮动画 */
  floaty?: boolean
  className?: string
}

const BASE_W = 172 // rpx（对应原型 86px）
const BASE_H = 204 // rpx（对应原型 102px）

export default function Mascot({
  mood = 'smile',
  scale = 1,
  floaty = false,
  className = '',
}: MascotProps) {
  return (
    <View
      className={`mascot-wrap ${floaty ? 'floaty' : ''} ${className}`.trim()}
      style={{ width: `${BASE_W * scale}rpx`, height: `${BASE_H * scale}rpx` }}
    >
      <View
        className={`mascot ${mood}`}
        style={{ transform: `scale(${scale})`, transformOrigin: 'top left' }}
      >
        <View className='head'>
          <View className='hair h1' />
          <View className='hair h2' />
          <View className='eye l' />
          <View className='eye r' />
          <View className='blush l' />
          <View className='blush r' />
          <View className='mouth' />
          <View className='tear' />
        </View>
        <View className='body'>
          <View className='bow' />
        </View>
        <View className='arm l' />
        <View className='arm r' />
      </View>
    </View>
  )
}
