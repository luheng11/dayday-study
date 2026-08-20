/* 通关结算页（原型 03-1）：庆祝动效 + 三个核心数据 + 报告引导 */

import { useEffect, useState } from 'react'
import { View, Text, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import { ICONS } from '../../components/Icon/icons'
import { generateReport } from '../../services/api'
import {
  addXp,
  loadResult,
  saveLatestReport,
  saveResult,
} from '../../services/storage'
import './index.scss'

function formatShort(totalMs: number): string {
  const totalSec = Math.max(0, Math.round(totalMs / 1000))
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}'${String(s).padStart(2, '0')}"`
}

const CONFETTI_COLORS = [
  '#FFB300',
  '#3DBE6B',
  '#4A90E2',
  '#F04F4F',
  '#E29C00',
  '#3DBE6B',
  '#4A90E2',
  '#F04F4F',
  '#3DBE6B',
]

export default function ResultPage() {
  const [result, setResult] = useState(() => loadResult())
  const [generating, setGenerating] = useState(false)

  // 成长值入账（每局一次，防重复）
  useEffect(() => {
    if (result && !result.credited) {
      addXp(result.xpEarned)
      const next = { ...result, credited: true }
      setResult(next)
      saveResult(next)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!result) {
    return (
      <View className='page'>
        <View className='empty-state'>
          <Mascot mood='sad' scale={0.9} />
          <Text className='empty-text'>结算数据不见了</Text>
          <View
            className='btn'
            style={{ marginTop: '32rpx', width: '300rpx' }}
            onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
          >
            返回首页
          </View>
        </View>
      </View>
    )
  }

  const { quiz, correctCount, totalMs, xpEarned } = result
  const total = quiz.questions.length

  const handleViewReport = async () => {
    setGenerating(true)
    try {
      const report = await generateReport({
        quiz_id: quiz.quiz_id,
        topic: quiz.title,
        questions: quiz.questions,
        answer_records: result.answerRecords,
      })
      saveLatestReport(report, quiz.title, Date.now())
      setGenerating(false)
      Taro.redirectTo({ url: '/pages/reportDetail/index' })
    } catch (e) {
      console.error('[report]', e)
      setGenerating(false)
      Taro.showToast({ title: '报告生成失败，请重试', icon: 'none' })
    }
  }

  const handlePlayAgain = () => {
    Taro.reLaunch({ url: '/pages/index/index' })
  }

  return (
    <View className='page'>
      <View className='burst' />
      <View className='confetti'>
        {CONFETTI_COLORS.map((color, i) => (
          <View
            key={i}
            className={`confetti-piece${i % 2 === 0 ? '' : ' round'}`}
            style={{ left: `${8 + i * 10}%`, background: color }}
          />
        ))}
      </View>

      <View className='result-center'>
        <Mascot mood='cheer' scale={1} />
      </View>

      <View className='font-display win-title'>唰——通关成功！</View>

      <View className='stars'>
        {[0, 1, 2].map((i) => (
          <Image key={i} className='star-icon' src={ICONS.star} />
        ))}
      </View>

      <View className='win-sub'>「{quiz.title}」{total} 关全部完成！</View>

      <View className='stat-row'>
        <View className='stat'>
          <View className='stat-v'>
            {correctCount}/{total}
          </View>
          <View className='stat-k'>答对题数</View>
        </View>
        <View className='stat'>
          <View className='stat-v'>{formatShort(totalMs)}</View>
          <View className='stat-k'>用时</View>
        </View>
        <View className='stat'>
          <View className='stat-v'>{xpEarned}</View>
          <View className='stat-k'>获得⭐</View>
        </View>
      </View>

      <View className='result-quote'>
        <View className='say'>
          表现超棒！<Text className='say-b'>看看你的通关报告吧～</Text>
        </View>
      </View>

      <View className='result-btns'>
        <View className='btn big' onClick={handleViewReport}>
          📊 查看复盘报告
        </View>
        <View className='btn big ghost' onClick={handlePlayAgain}>
          🎮 再闯一关
        </View>
      </View>

      {generating && (
        <View className='gen-overlay'>
          <Mascot mood='think' floaty scale={0.9} />
          <View className='font-display gen-text'>AI 正在生成报告…</View>
        </View>
      )}
    </View>
  )
}
