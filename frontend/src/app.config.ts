export default defineAppConfig({
  pages: [
    'pages/index/index',        // 首页（Tab）
    'pages/quiz/index',         // 闯关（Tab 落地：续答/引导）
    'pages/report/index',       // 报告（Tab 落地：最近报告/空态）
    'pages/profile/index',      // 我的（Tab 空态）
    'pages/gameplay/index',     // 答题闯关页
    'pages/result/index',       // 通关结算页
    'pages/reportDetail/index', // 复盘报告页
  ],
  networkTimeout: {
    request: 60000,
    connectSocket: 60000,
    uploadFile: 60000,
    downloadFile: 60000,
  },
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#FFF9EC',
    navigationBarTitleText: '闯关学堂',
    navigationBarTextStyle: 'black',
    backgroundColor: '#FFF9EC',
  },
})
