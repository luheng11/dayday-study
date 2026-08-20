/* 图标资源索引（tools/gen-icons.mjs 生成的 PNG） */

import tabHome from '../../assets/icons/tab-home.png'
import tabHomeOn from '../../assets/icons/tab-home-on.png'
import tabQuiz from '../../assets/icons/tab-quiz.png'
import tabQuizOn from '../../assets/icons/tab-quiz-on.png'
import tabReport from '../../assets/icons/tab-report.png'
import tabReportOn from '../../assets/icons/tab-report-on.png'
import tabProfile from '../../assets/icons/tab-profile.png'
import tabProfileOn from '../../assets/icons/tab-profile-on.png'
import iconStar from '../../assets/icons/icon-star.png'
import iconHeart from '../../assets/icons/icon-heart.png'
import iconHeartLost from '../../assets/icons/icon-heart-lost.png'
import iconBack from '../../assets/icons/icon-back.png'
import iconSun from '../../assets/icons/icon-sun.png'
import iconVolcano from '../../assets/icons/icon-volcano.png'
import iconMagnet from '../../assets/icons/icon-magnet.png'

export const ICONS = {
  tabHome,
  tabHomeOn,
  tabQuiz,
  tabQuizOn,
  tabReport,
  tabReportOn,
  tabProfile,
  tabProfileOn,
  star: iconStar,
  heart: iconHeart,
  heartLost: iconHeartLost,
  back: iconBack,
  sun: iconSun,
  volcano: iconVolcano,
  magnet: iconMagnet,
}

export type IconName = keyof typeof ICONS
