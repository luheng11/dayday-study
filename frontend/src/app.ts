import { Component, PropsWithChildren } from 'react'
import Taro from '@tarojs/taro'
import { getToken, loginByCode, resolveLogin, setCachedUser, setToken } from './services/api'
import './app.scss'

/* 说明：标题字体「站酷快乐体」暂不通过网络加载 ——
 * wx.loadFontFace 使用网络字体源时，基础库会触发异步域名安全检查
 * （webapi_getwxaasyncsecinfo），域名未加入小程序 request 合法域名时
 * 控制台会报 SystemError。当前 .font-display 自动回退为系统粗体。
 * Phase 9 打磨时再接入：方案 A 域名白名单 + 已备案 CDN 上的字体文件；
 * 方案 B 字体子集化后以 base64 data URI 本地加载（免域名检查）。
 */

class App extends Component<PropsWithChildren> {
  componentDidMount() {
    // 静默登录（Phase 5）：成功拿到 token 后所有请求自动携带；
    // 失败不阻断核心功能（可选登录，出题/答题/报告匿名可用）。
    if (getToken()) {
      resolveLogin()
      return
    }
    Taro.login({
      success: (res) => {
        if (!res.code) {
          resolveLogin()
          return
        }
        loginByCode(res.code)
          .then((data) => {
            setToken(data.token)
            setCachedUser(data.user)
          })
          .catch(() => {
            /* 登录失败不阻断核心功能 */
          })
          .finally(() => resolveLogin())
      },
      fail: () => resolveLogin(),
    })
  }

  render() {
    return this.props.children
  }
}

export default App
