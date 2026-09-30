/* 「我的」Tab：学习档案（严格按原型文件 04-1 学习记录列表）
 * 档案头（头像/昵称/等级徽章/XP 进度条）+ 周统计 + 筛选 + 记录卡（星级/正确率分色）+ 下拉分页
 * 附加：头像微信授权（chooseAvatar）、昵称点击编辑、「📈 学习统计」入口（原型未画入口，导航补充）
 */

import { useCallback, useMemo, useState } from 'react'
import { Button, Input, View, Text, Image, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import TabBar from '../../components/TabBar'
import {
  getQuizHistory,
  getUserProfile,
  isLoggedIn,
  setCachedUser,
  updateUserProfile,
  uploadAvatar,
  waitForLogin,
} from '../../services/api'
import type { HistoryRange } from '../../services/api'
import { getXpTotal } from '../../services/storage'
import type { QuizHistoryItem, UserProfile } from '../../services/types'
import './index.scss'

/* 记录卡图标：按主题关键词映射（原型 04-1 风格，兜底 📚） */
const TOPIC_EMOJIS: Array<{ keys: string[]; emoji: string; bg: string }> = [
  { keys: ['光合作用', '植物'], emoji: '🌱', bg: '#FFF3C2' },
  { keys: ['火山', '地球', '公转', '四季', '地理'], emoji: '🌋', bg: '#FFE1D6' },
  { keys: ['磁铁', '磁性'], emoji: '🧲', bg: '#DCEBFF' },
  { keys: ['数学', '勾股'], emoji: '📐', bg: '#E8E0FF' },
  { keys: ['英语', '单词', '语法'], emoji: '🔤', bg: '#E4F7EC' },
  { keys: ['语文', '古诗'], emoji: '📖', bg: '#FFF3C2' },
  { keys: ['历史'], emoji: '🏛️', bg: '#E8E0FF' },
  { keys: ['化学'], emoji: '🧪', bg: '#DCEBFF' },
  { keys: ['物理'], emoji: '⚡', bg: '#FFE1D6' },
]

function topicEmoji(topic: string): { emoji: string; bg: string } {
  for (const item of TOPIC_EMOJIS) {
    if (item.keys.some((k) => topic.includes(k))) {
      return { emoji: item.emoji, bg: item.bg }
    }
  }
  return { emoji: '📚', bg: '#FFF3C2' }
}

/* 星级：正确率 ≥80 三星 / 60-79 两星 / <60 一星（原型 04-1） */
function starCount(accuracy: number): number {
  if (accuracy >= 80) return 3
  if (accuracy >= 60) return 2
  return 1
}

/* 正确率分色：绿 ≥80 / 黄 60-79 / 红 <60 */
function accuracyClass(accuracy: number): string {
  if (accuracy >= 80) return 'g'
  if (accuracy >= 60) return 'y'
  return 'r'
}

/* 相对时间：今天 9:48 / 昨天 19:02 / 3 天前 16:20 / 2026-08-01 */
function formatWhen(createdAt: string): string {
  const date = new Date(createdAt.replace(/-/g, '/'))
  if (Number.isNaN(date.getTime())) return createdAt
  const hm = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  const today = new Date()
  const startOfDay = (d: Date) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const diffDays = Math.round((startOfDay(today) - startOfDay(date)) / 86400000)
  if (diffDays === 0) return `今天 ${hm}`
  if (diffDays === 1) return `昨天 ${hm}`
  if (diffDays < 7) return `${diffDays} 天前 ${hm}`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function formatDuration(totalMs: number): string {
  const totalSec = Math.max(0, Math.round(totalMs / 1000))
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m} 分 ${String(s).padStart(2, '0')} 秒`
}

const FILTERS: Array<{ key: HistoryRange; label: string }> = [
  { key: 'all', label: '全部' },
  { key: 'week', label: '最近 7 天' },
  { key: 'month', label: '本月' },
]

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [items, setItems] = useState<QuizHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [range, setRange] = useState<HistoryRange>('all')
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState(false)
  const [nicknameDraft, setNicknameDraft] = useState('')

  const loggedIn = isLoggedIn()

  const loadProfile = useCallback(async () => {
    try {
      const data = await getUserProfile()
      setProfile(data)
      setCachedUser({
        id: data.id,
        nickname: data.nickname,
        avatar_url: data.avatar_url,
        total_xp: data.total_xp,
      })
    } catch {
      /* 未登录/失败：保持匿名态 */
    }
  }, [])

  const loadHistory = useCallback(
    async (p: number, r: HistoryRange, reset: boolean) => {
      if (!isLoggedIn()) return
      setLoading(true)
      try {
        const data = await getQuizHistory({ page: p, pageSize: 10, range: r })
        setItems((prev) => (reset ? data.items : [...prev, ...data.items]))
        setTotal(data.total)
        setPage(p)
        setHasMore(data.items.length >= 10 && p * 10 < data.total)
      } catch {
        /* 网络失败保持现状 */
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  useDidShow(() => {
    void waitForLogin().then(() => {
      loadProfile()
      loadHistory(1, range, true)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  })

  const handleFilter = (key: HistoryRange) => {
    if (key === range) return
    setRange(key)
    loadHistory(1, key, true)
  }

  const handleLoadMore = () => {
    if (!hasMore || loading) return
    loadHistory(page + 1, range, false)
  }

  const handleViewDetail = (quizId: string) => {
    Taro.navigateTo({ url: `/pages/reportDetail/index?quizId=${quizId}` })
  }

  /* 头像：微信头像授权（官方 chooseAvatar），上传到后端换持久 URL */
  const handleChooseAvatar = (e: { detail: { avatarUrl?: string } }) => {
    const avatarUrl = e.detail.avatarUrl
    if (!avatarUrl) return
    uploadAvatar(avatarUrl)
      .then(() => loadProfile())
      .catch(() => Taro.showToast({ title: '头像保存失败，请重试', icon: 'none' }))
  }

  /* 昵称编辑 */
  const startEditNickname = () => {
    setNicknameDraft(profile?.nickname || '')
    setEditing(true)
  }

  const submitNickname = () => {
    const name = nicknameDraft.trim()
    setEditing(false)
    if (!name || name === profile?.nickname) return
    updateUserProfile({ nickname: name })
      .then(() => loadProfile())
      .catch(() => Taro.showToast({ title: '昵称保存失败', icon: 'none' }))
  }

  /* 等级进度条（原型 4.1）：当前等级内进度 / 本级所需 */
  const levelInfo = useMemo(() => {
    if (!profile) return null
    const { level } = profile
    const inLevel = profile.total_xp - level.level_start_xp
    const needed = level.level_end_xp === null ? null : level.level_end_xp - level.level_start_xp
    const percent = level.is_max || !needed ? 100 : Math.min(100, Math.round((inLevel / needed) * 100))
    return { inLevel, needed, percent }
  }, [profile])

  return (
    <View className='page'>
      <ScrollView scrollY className='sbody' onScrollToLower={handleLoadMore} lowerThreshold={120}>
        <View className='sbody-inner'>
          {/* ---- 档案头 ---- */}
          <View className='profile-head'>
            {profile?.avatar_url ? (
              <Button className='avatar-btn' openType='chooseAvatar' onChooseAvatar={handleChooseAvatar}>
                <Image className='avatar-img' src={profile.avatar_url} mode='aspectFill' />
              </Button>
            ) : (
              <Button className='avatar-btn mascot-avatar' openType='chooseAvatar' onChooseAvatar={handleChooseAvatar}>
                <View className='avatar'>
                  <View className='avatar-hair h1' />
                  <View className='avatar-hair h2' />
                  <View className='avatar-eye l' />
                  <View className='avatar-eye r' />
                  <View className='avatar-blush l' />
                  <View className='avatar-blush r' />
                  <View className='avatar-mouth' />
                </View>
              </Button>
            )}

            <View className='profile-info'>
              {editing ? (
                <Input
                  className='nickname-input'
                  value={nicknameDraft}
                  maxlength={12}
                  focus
                  onInput={(e) => setNicknameDraft(e.detail.value)}
                  onBlur={submitNickname}
                  onConfirm={submitNickname}
                />
              ) : (
                <View className='name-row'>
                  <Text className='name' onClick={startEditNickname}>
                    {profile?.nickname || '小闯同学'}
                  </Text>
                  <Text className='name-edit'>✏️</Text>
                </View>
              )}
              <View className='lvl'>
                <View className='lvl-chip'>
                  Lv.{profile?.level.level ?? 1} {profile?.level.title ?? '闯关新星'}
                </View>
                {levelInfo && (
                  <>
                    <View className='xpbar'>
                      <View className='xpbar-fill' style={{ width: `${levelInfo.percent}%` }} />
                    </View>
                    <Text className='xpt'>
                      {profile && profile.level.is_max
                        ? 'MAX'
                        : `${levelInfo.inLevel}/${levelInfo.needed}`}
                    </Text>
                  </>
                )}
              </View>
            </View>

            <View
              className='stats-entry'
              onClick={() => Taro.navigateTo({ url: '/pages/stats/index' })}
            >
              <Text className='stats-entry-t'>📈 学习统计</Text>
              <Text className='stats-entry-arrow'>›</Text>
            </View>
          </View>

          {/* ---- 周统计 ---- */}
          <View className='week-stats'>
            <View className='wstat'>
              <View className='wstat-v'>{profile?.week_quiz_count ?? 0}</View>
              <View className='wstat-k'>本周闯关</View>
            </View>
            <View className='wstat'>
              <View className='wstat-v'>{profile?.average_accuracy ?? 0}%</View>
              <View className='wstat-k'>平均正确率</View>
            </View>
            <View className='wstat'>
              <View className='wstat-v'>
                {loggedIn ? (profile?.total_xp ?? 0) : getXpTotal()}
              </View>
              <View className='wstat-k'>累计⭐</View>
            </View>
          </View>

          {/* ---- 筛选 ---- */}
          <View className='filter'>
            {FILTERS.map((f) => (
              <View
                key={f.key}
                className={`f${range === f.key ? ' on' : ''}`}
                onClick={() => handleFilter(f.key)}
              >
                {f.label}
              </View>
            ))}
          </View>

          {/* ---- 记录列表 ---- */}
          {loggedIn && items.length === 0 && !loading ? (
            <View className='empty-note'>还没有闯关记录，去首页闯一关吧 🎯</View>
          ) : (
            items.map((item) => {
              const icon = topicEmoji(item.title)
              const stars = starCount(item.accuracy)
              return (
                <View
                  key={item.quiz_id}
                  className='rec'
                  onClick={() => handleViewDetail(item.quiz_id)}
                >
                  <View className='rec-ic' style={{ background: icon.bg }}>
                    <Text>{icon.emoji}</Text>
                  </View>
                  <View className='rec-main'>
                    <View className='rec-t'>{item.title}</View>
                    <View className='rec-d'>
                      {formatWhen(item.created_at)} · {item.question_count} 题 ·{' '}
                      {formatDuration(item.duration_ms)}
                    </View>
                  </View>
                  <View className='rec-acc'>
                    <View className={`rec-p ${accuracyClass(item.accuracy)}`}>
                      {Math.round(item.accuracy)}%
                    </View>
                    <View className='rec-s'>正确率</View>
                    <View className='rec-stars'>
                      {[0, 1, 2].map((i) => (
                        <View
                          key={i}
                          className={`star${i < stars ? ' on' : ''}`}
                        >
                          ★
                        </View>
                      ))}
                    </View>
                  </View>
                </View>
              )
            })
          )}

          {loading && <View className='empty-note'>加载中…</View>}
          {loggedIn && items.length > 0 && (
            <View className='empty-note'>
              {hasMore ? '下拉加载更早的记录' : `共 ${total} 次闯关`}
            </View>
          )}
        </View>
      </ScrollView>

      <TabBar active='profile' />
    </View>
  )
}
