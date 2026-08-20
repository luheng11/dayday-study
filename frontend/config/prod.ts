import type { UserConfigExport } from '@tarojs/cli'

export default {
  defineConstants: {
    // 生产环境后端地址（部署微信云托管后替换为正式域名）
    API_BASE_URL: '"https://your-domain.example.com/api/v1"',
  },
  mini: {},
  h5: {},
} satisfies UserConfigExport<'webpack5'>
