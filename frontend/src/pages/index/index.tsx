/* 首页：默认 / 输入态 / AI 生成中 / 失败重试（严格按原型文件 01） */

import { useState } from 'react'
import { View, Text, Textarea, Image, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import TabBar from '../../components/TabBar'
import { ICONS } from '../../components/Icon/icons'
import { generateQuizAsync, pollQuizTask } from '../../services/api'
import { getXpTotal, saveQuizProgress } from '../../services/storage'
import './index.scss'

type ViewState = 'default' | 'input' | 'loading' | 'fail'

const MAX_LEN = 2000
const POLL_INTERVAL = 1200
const POLL_TIMEOUT = 60000

interface Example {
  icon: string
  bg: string
  title: string
  desc: string
  topic: string
}

const EXAMPLES: Example[] = [
  {
    icon: ICONS.sun,
    bg: '#FFF3C2',
    title: '光合作用',
    desc: '植物是怎么「吃饭」的？',
    topic: '光合作用是怎么进行的？',
  },
  {
    icon: ICONS.volcano,
    bg: '#FFE1D6',
    title: '火山为什么会喷发',
    desc: '地球内部的能量',
    topic: '火山为什么会喷发？',
  },
  {
    icon: ICONS.magnet,
    bg: '#DCEBFF',
    title: '磁铁的秘密',
    desc: '看不见的吸引力',
    topic: '磁铁的秘密：磁铁为什么能吸铁？',
  },
]

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export default function IndexPage() {
  const [viewState, setViewState] = useState<ViewState>('default')
  const [text, setText] = useState('')
  const [mode, setMode] = useState<'topic' | 'paste'>('topic')
  const [count, setCount] = useState(5)
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium')
  const [xp] = useState(() => getXpTotal())

  const placeholder =
    mode === 'topic'
      ? '一句话、一段课文、甚至一个主题都行，比如：光合作用是怎么进行的？'
      : '把课文、笔记粘贴到这里，AI 会帮你出题闯关'

  const handleStart = () => {
    if (!text.trim()) {
      setViewState('input')
      return
    }
    void doGenerate()
  }

  const handleGenerate = () => {
    if (!text.trim()) {
      Taro.showToast({ title: '先输入想学的知识哦', icon: 'none' })
      return
    }
    void doGenerate()
  }

  const doGenerate = async () => {
    const input = text.trim()
    setViewState('loading')
    try {
      const { task_id } = await generateQuizAsync({
        user_input: input,
        question_count: count,
        difficulty,
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
          setViewState('default')
          Taro.navigateTo({ url: '/pages/gameplay/index' })
          return
        }
        if (status.status === 'failed') {
          setViewState('fail')
          return
        }
      }
      setViewState('fail')
    } catch (e) {
      console.error('[generate]', e)
      setViewState('fail')
    }
  }

  const handleExampleTap = (example: Example) => {
    setText(example.topic)
    setMode('topic')
    setViewState('input')
  }

  const clearText = () => setText('')

  /* ---------- 生成中（全屏，无顶栏无底栏） ---------- */
  if (viewState === 'loading') {
    return (
      <View className='page loading-page'>
        <View className='loading'>
          <View className='burst' />
          <View className='thought'>
            <View className='dot' />
            <View className='dot' />
            <View className='dot' />
          </View>
          <Mascot mood='think' floaty scale={1} className='loading-mascot' />
          <View className='font-display loading-title'>AI 正在出题…</View>

          <View className='steps'>
            <View className='step done'>
              <View className='st'>✓</View>
              <Text>读懂你的问题</Text>
            </View>
            <View className='step doing'>
              <View className='st' />
              <Text>拆解知识点 · 规划题目</Text>
            </View>
            <View className='step todo'>
              <View className='st'>3</View>
              <Text>生成闯关题目与讲解</Text>
            </View>
          </View>

          <View className='progress'>
            <View className='bar' />
          </View>
          <View className='tips'>💡 小提示：答题前先自己想一想，再看讲解，记得更牢！</View>
        </View>
      </View>
    )
  }

  /* ---------- 默认 / 输入 / 失败 三态（有顶栏与底栏） ---------- */
  return (
    <View className='page'>
      <ScrollView scrollY className='sbody'>
        <View className='sbody-inner'>
          <View className='topbar'>
            <View className='logo'>
              <View className='logo-m'>闯</View>
              <Text className='font-display'>闯关学堂</Text>
            </View>
            <View className='xpchip'>
              <Image className='xp-star' src={ICONS.star} />
              <Text>成长值 {xp}</Text>
            </View>
          </View>

          {viewState === 'fail' ? (
            <View className='fail-wrap'>
              <View className='crack'>✗</View>
              <View className='squig' />
              <View className='fail-center'>
                <Mascot mood='sad' scale={0.92} />
                <View className='errbox'>
                  <View className='font-display err-title'>哎呀，出题卡住了</View>
                  <Text className='err-desc'>
                    网络好像开小差了，题目没有生成成功。{'\n'}别急，我们再来一次！
                  </Text>
                </View>
                <View className='err-btns'>
                  <View className='btn big' onClick={handleGenerate}>
                    🔄 重新生成
                  </View>
                  <View className='btn big ghost' onClick={() => setViewState('input')}>
                    ✏️ 换个说法再试
                  </View>
                </View>
                <View className='retrytip'>
                  <Text className='rt-icon'>💡</Text>
                  <Text>
                    可以把主题写得更具体一点，比如「小学科学 · 光合作用」，出题会更准。
                  </Text>
                </View>
              </View>
            </View>
          ) : viewState === 'input' ? (
            <View>
              <View className='sect-title'>想学什么？</View>
              <View className='input-card focus'>
                <Textarea
                  className='input-textarea'
                  value={text}
                  placeholder={placeholder}
                  maxlength={MAX_LEN}
                  autoHeight={false}
                  onInput={(e) => setText(e.detail.value)}
                />
                <View className='input-meta'>
                  <Text className='clear-link' onClick={clearText}>
                    ✕ 清空
                  </Text>
                  <Text>
                    {text.length} / {MAX_LEN}
                  </Text>
                </View>
              </View>

              <View className='optrow'>
                <View
                  className={`chip${mode === 'topic' ? ' on' : ''}`}
                  onClick={() => setMode('topic')}
                >
                  ✨ 主题
                </View>
                <View
                  className={`chip${mode === 'paste' ? ' on' : ''}`}
                  onClick={() => setMode('paste')}
                >
                  📋 粘贴一段文本
                </View>
              </View>

              <View className='settings'>
                <Text>出题数量</Text>
                <View className='segcount'>
                  {[3, 5].map((n) => (
                    <View
                      key={n}
                      className={`n${count === n ? ' on' : ''}`}
                      onClick={() => setCount(n)}
                    >
                      {n}
                    </View>
                  ))}
                </View>
              </View>
              <View className='settings settings-2'>
                <Text>题目难度</Text>
                <View className='diff'>
                  {(
                    [
                      ['入门', 'easy'],
                      ['适中', 'medium'],
                      ['挑战', 'hard'],
                    ] as const
                  ).map(([label, value]) => (
                    <View
                      key={value}
                      className={`d${difficulty === value ? ' on' : ''}`}
                      onClick={() => setDifficulty(value)}
                    >
                      {label}
                    </View>
                  ))}
                </View>
              </View>

              <View className='gen-btn-wrap'>
                <View className='btn big' onClick={handleGenerate}>
                  ⚡ 生成闯关题目
                </View>
              </View>
              <View className='hint'>约 10 秒出题 · 每道题都带讲解 · 答错也会讲明白</View>

              <View className='retrytip'>
                <Text className='rt-icon'>💡</Text>
                <Text>
                  不知道怎么问？试试从「试试这些」里挑一个示例主题，一键体验完整闯关流程。
                </Text>
              </View>
            </View>
          ) : (
            <View>
              <View className='hero'>
                <View className='card hero-card'>
                  <View className='hero-mascot'>
                    <Mascot mood='smile' floaty scale={0.76} />
                  </View>
                  <View>
                    <View className='greet'>
                      早上好，<Text className='greet-em'>小闯同学</Text>！👋
                    </View>
                    <View className='say hero-say'>
                      今天想学点什么？<Text className='say-b'>我来帮你出题闯关！</Text>
                    </View>
                  </View>
                </View>
              </View>

              <View className='sect-title'>输入想学的知识</View>
              <View className='input-card' onClick={() => setViewState('input')}>
                <Textarea
                  className='input-textarea'
                  value={text}
                  placeholder={placeholder}
                  maxlength={MAX_LEN}
                  onInput={(e) => setText(e.detail.value)}
                  onFocus={() => setViewState('input')}
                />
                <View className='input-meta'>
                  <Text className='chip soft'>✨ 主题</Text>
                  <Text className='chip soft'>📋 粘贴文本</Text>
                  <Text>
                    {text.length} / {MAX_LEN}
                  </Text>
                </View>
              </View>
              <View className='start-btn-wrap'>
                <View className='btn big' onClick={handleStart}>
                  🔍 一键生成闯关
                </View>
              </View>

              <View className='sect-title'>
                试试这些{' '}
                <Text className='sect-sub'>适合中小学生的示例主题</Text>
              </View>
              {EXAMPLES.map((example) => (
                <View
                  key={example.title}
                  className='example-card'
                  onClick={() => handleExampleTap(example)}
                >
                  <View className='example-ic' style={{ background: example.bg }}>
                    <Image className='example-icon' src={example.icon} />
                  </View>
                  <View>
                    <View className='example-t'>{example.title}</View>
                    <View className='example-d'>{example.desc}</View>
                  </View>
                  <Text className='example-go'>5 关 →</Text>
                </View>
              ))}
            </View>
          )}
        </View>
      </ScrollView>

      <TabBar active='home' />
    </View>
  )
}
