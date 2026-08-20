declare module '*.png' {
  const src: string
  export default src
}

declare module '*.svg' {
  const src: string
  export default src
}

declare const API_BASE_URL: string

/* 微信小程序全局对象（app.ts 字体加载用） */
declare const wx: {
  loadFontFace?: (options: {
    family: string
    source: string
    global?: boolean
    success?: () => void
    fail?: () => void
  }) => void
}
