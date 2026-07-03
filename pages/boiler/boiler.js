// pages/boiler/boiler.js
// 锅炉选择页：从 mock 数据加载锅炉列表，选择后写入本地状态，供首页/巡检/激活页复用。
const { request } = require('../../api/index')
const { setState } = require('../../store/app-state')
const ui = require('../../utils/ui')

Page({
  data: { boilers: [] },

  async onShow() {
    try {
      ui.showLoading('加载锅炉')
      const boilers = await request({ url: '/boilers' })
      this.setData({ boilers: boilers || [] })
    } catch (e) {
      ui.error('锅炉加载失败')
    } finally {
      ui.hideLoading()
    }
  },

  chooseBoiler(e) {
    const boiler = e.currentTarget.dataset.item
    setState({ currentBoiler: boiler })
    const app = getApp()
    app.globalData.currentBoiler = boiler
    ui.success(`已选择${boiler.name}`)
    setTimeout(() => {
      if (getCurrentPages().length > 1) wx.navigateBack()
      else wx.switchTab({ url: '/pages/index/index' })
    }, 300)
  }
})
