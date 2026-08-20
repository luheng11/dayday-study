import { Component, PropsWithChildren } from 'react'
import './app.scss'

// 站酷快乐体（标题字体）。加载失败时静默回退到系统字体，不影响任何功能。
const DISPLAY_FONT_FAMILY = 'ZCOOL KuaiLe'
const DISPLAY_FONT_URL =
  'https://cdn.jsdelivr.net/gh/jasonyapri/zcool-kuaile@1.0/ZCOOLKuaiLe-Regular.ttf'

function tryLoadDisplayFont() {
  try {
    // eslint-disable-next-line no-undef
    if (typeof wx !== 'undefined' && wx.loadFontFace) {
      wx.loadFontFace({
        family: DISPLAY_FONT_FAMILY,
        source: `url("${DISPLAY_FONT_URL}")`,
        global: true,
        success: () => console.log('[font] ZCOOL KuaiLe loaded'),
        fail: () => console.log('[font] fallback to system font'),
      })
    }
  } catch (e) {
    console.log('[font] loader unavailable:', e)
  }
}

class App extends Component<PropsWithChildren> {
  componentDidMount() {
    tryLoadDisplayFont()
  }

  render() {
    return this.props.children
  }
}

export default App
