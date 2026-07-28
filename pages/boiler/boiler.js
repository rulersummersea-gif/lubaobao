// pages/boiler/boiler.js
// 锅炉选择页：从 mock 数据加载锅炉列表，选择后写入本地状态，供首页/巡检/激活页复用。
const { request } = require('../../api/index')
const { saveCurrentBoiler } = require('../../api/auth')
const { getState, saveLastBoiler, setState } = require('../../store/app-state')
const ui = require('../../utils/ui')

Page({
  data: { boilers: [], currentBoilerId: null, selectingId: null },

  async onShow() {
    try {
      ui.showLoading('加载锅炉')
      const state = getState()
      const boilers = await request({ url: '/boilers', data: { enterpriseId: state.user && state.user.enterpriseId } })
      const currentBoilerId = state.currentBoiler && state.currentBoiler.id
      this.setData({
        currentBoilerId,
        boilers: (boilers || []).map((item) => ({
          ...this.normalizeBoiler(item),
          isSelected: Number(item.id) === Number(currentBoilerId)
        }))
      })
    } catch (e) {
      ui.error('锅炉加载失败')
    } finally {
      ui.hideLoading()
    }
  },

  normalizeBoiler(item) {
    return {
      ...item,
      name: item.name || item.model || `锅炉 #${item.id}`,
      codeText: item.code || item.deviceCode || `ID：${item.id}`,
      locationText: item.location || `企业ID：${item.enterpriseId || '-'}`,
      specText: item.evaporation || item.pressure ? `蒸发量 ${item.evaporation || '-'} ｜ 压力 ${item.pressure || '-'}` : '已接入联调服务器',
      statusLabel: item.status === 'warning' ? '预警' : '正常',
      statusClass: item.status === 'warning' ? 'tag-warn' : 'tag-normal'
    }
  },

  async chooseBoiler(e) {
    const boiler = e.currentTarget.dataset.item
    if (!boiler || this.data.selectingId) return
    this.setData({ selectingId: boiler.id })
    try {
      const res = await saveCurrentBoiler(boiler.id)
      const currentBoiler = res.currentBoiler || boiler
      setState({ currentBoiler, onboarding: res.onboarding || null })
      const state = getState()
      saveLastBoiler(state.user && state.user.id, currentBoiler)
      const app = getApp()
      app.globalData.currentBoiler = currentBoiler
      ui.success(`已选择${currentBoiler.name}`)
      setTimeout(() => {
        if (getCurrentPages().length > 1) wx.navigateBack()
        else wx.switchTab({ url: '/pages/index/index' })
      }, 300)
    } catch (e) {
      ui.error(e.message || '锅炉切换失败')
    } finally {
      this.setData({ selectingId: null })
    }
  }
})
