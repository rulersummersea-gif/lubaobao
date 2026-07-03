const { getInspectionResult } = require('../../api/inspection')
const config = require('../../config/index')

Page({
  data: {
    progress: 18,
    dots: '.',
    timer: null,
    pollTimer: null,
    startTs: 0,
    timeoutMs: 30000
  },

  onLoad() {
    this.setData({ startTs: Date.now() })
    this.startAnimation()
    this.startPolling()
  },

  onUnload() {
    if (this.data.timer) clearInterval(this.data.timer)
    if (this.data.pollTimer) clearInterval(this.data.pollTimer)
  },

  startAnimation() {
    const timer = setInterval(() => {
      let p = this.data.progress + 7
      if (p > 95) p = 95
      const nextDots = this.data.dots.length >= 3 ? '.' : `${this.data.dots}.`
      this.setData({ progress: p, dots: nextDots, timer })
    }, 800)
    this.setData({ timer })
  },

  async tryFetchResult() {
    const inspectionId = wx.getStorageSync('BG_LAST_INSPECTION_ID')
    if (!inspectionId) return false

    const cfg = config.getConfig ? config.getConfig() : config
    // mock 模式直接读取本地结果
    if (cfg.useMock) {
      const result = wx.getStorageSync('BG_LAST_RESULT')
      if (result) {
        this.finishAndJump(result)
        return true
      }
      return false
    }

    try {
      const result = await getInspectionResult(inspectionId)
      if (!result) return false
      const status = result.status || result.taskStatus || 'done'
      if (['done', 'success', 'finished', 'submitted'].includes(String(status).toLowerCase())) {
        wx.setStorageSync('BG_LAST_RESULT', result)
        this.finishAndJump(result)
        return true
      }
      return false
    } catch (e) {
      return false
    }
  },

  startPolling() {
    const pollTimer = setInterval(async () => {
      const elapsed = Date.now() - this.data.startTs
      if (elapsed > this.data.timeoutMs) {
        clearInterval(pollTimer)
        this.setData({ pollTimer: null })
        wx.showToast({ title: '识别超时，请稍后重试', icon: 'none' })
        setTimeout(() => wx.navigateBack({ delta: 1 }), 400)
        return
      }
      const ok = await this.tryFetchResult()
      if (ok) {
        clearInterval(pollTimer)
        this.setData({ pollTimer: null })
      }
    }, 1500)
    this.setData({ pollTimer })
  },

  finishAndJump() {
    if (this.data.timer) clearInterval(this.data.timer)
    this.setData({ progress: 100 })
    setTimeout(() => wx.redirectTo({ url: '/pages/result/result' }), 250)
  }
})
