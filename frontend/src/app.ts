import { Component, PropsWithChildren } from 'react'
import './app.scss'

/* 说明：标题字体「站酷快乐体」暂不通过网络加载 ——
 * wx.loadFontFace 使用网络字体源时，基础库会触发异步域名安全检查
 * （webapi_getwxaasyncsecinfo），域名未加入小程序 request 合法域名时
 * 控制台会报 SystemError。当前 .font-display 自动回退为系统粗体。
 * Phase 9 打磨时再接入：方案 A 域名白名单 + 已备案 CDN 上的字体文件；
 * 方案 B 字体子集化后以 base64 data URI 本地加载（免域名检查）。
 */

class App extends Component<PropsWithChildren> {
  render() {
    return this.props.children
  }
}

export default App
