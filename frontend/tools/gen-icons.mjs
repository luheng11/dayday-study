/**
 * 图标管线：把 tools/icons-src/*.svg 栅格化为 src/assets/icons/*.png
 * （微信小程序 Image 组件对 SVG 支持不稳定，PNG 零风险；3x 输出保证清晰度）
 *
 * 用法：node tools/gen-icons.mjs
 */
import { readFileSync, writeFileSync, mkdirSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Resvg } from '@resvg/resvg-js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC_DIR = join(__dirname, 'icons-src')
const OUT_DIR = join(__dirname, '..', 'src', 'assets', 'icons')

// 每个图标的输出宽度（px，按最大展示尺寸的 3 倍渲染）
const SIZES = {
  'tab-': 69, // 23px 展示
  'icon-star': 156, // 52px 展示
  'icon-heart': 60, // 20px 展示
  'icon-back': 54, // 18px 展示
  'icon-sun': 66, // 22px 展示
  'icon-volcano': 66,
  'icon-magnet': 66,
}

mkdirSync(OUT_DIR, { recursive: true })

const files = readdirSync(SRC_DIR).filter((f) => f.endsWith('.svg'))
const results = []

for (const file of files) {
  const svg = readFileSync(join(SRC_DIR, file), 'utf8')
  const sizeKey = Object.keys(SIZES).find((prefix) => file.startsWith(prefix))
  const width = sizeKey ? SIZES[sizeKey] : 96
  const resvg = new Resvg(svg, {
    fitTo: { mode: 'width', value: width },
    background: 'rgba(0,0,0,0)', // 透明背景
  })
  const png = resvg.render().asPng()
  const outName = file.replace(/\.svg$/, '.png')
  writeFileSync(join(OUT_DIR, outName), png)
  results.push(`${outName} (${width}px, ${png.length} bytes)`)
}

console.log(results.join('\n'))
console.log(`\n共生成 ${results.length} 个 PNG → ${OUT_DIR}`)
