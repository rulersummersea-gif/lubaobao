// app.js
// 炉保保智能小程序入口：负责启动时恢复用户、企业、当前锅炉等全局上下文。
const { getState } = require('./store/app-state')

App({
  // globalData 用于跨页面共享运行时数据。
  globalData: {
    appName: '炉保保智能',
    user: null,
    enterprise: null,
    currentBoiler: null,
    isLoggedIn: false
  },

  // 小程序启动时，从本地缓存恢复登录态和业务上下文。
  onLaunch() {
    const state = getState()
    this.globalData.user = state.user || null
    this.globalData.enterprise = state.enterprise || null
    this.globalData.currentBoiler = state.currentBoiler || null
    this.globalData.isLoggedIn = !!state.token
  }
})
