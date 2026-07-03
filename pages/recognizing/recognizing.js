Page({
  data: { steps: ['定位比色卡', '识别检测区域', '分析颜色结果', '生成诊断建议'] },
  onLoad() {
    setTimeout(() => {
      const id = wx.getStorageSync('BG_LAST_INSPECTION_ID')
      if (id) wx.redirectTo({ url: '/pages/result/result?id=' + id })
    }, 1200)
  }
})
