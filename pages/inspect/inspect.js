// pages/inspect/inspect.js
// 巡检页：支持选择锅炉、扫码占位、拍照占位、图片预览、发起 mock 巡检。
const { request } = require('../../api/index')
const { getState } = require('../../store/app-state')
const ui = require('../../utils/ui')

Page({
  data: {
    currentBoiler: null,
    inspectionId: null,
    materialPackId: 5001,
    materialPackCode: 'BW-202607-000128',
    previewImage: '',
    submitting: false
  },

  onShow() {
    const state = getState()
    this.setData({ currentBoiler: state.currentBoiler || null })
  },

  goChooseBoiler() { wx.navigateTo({ url: '/pages/boiler/boiler' }) },
  mockScanPack() { this.setData({ materialPackCode: 'BW-202607-000128' }); ui.success('已模拟扫码') },
  mockTakePhoto() { this.setData({ previewImage: '/images/mock-board.png' }); ui.success('已模拟拍照') },

  async startInspection() {
    if (this.data.submitting) return
    const state = getState()
    if (!state.currentBoiler) return ui.error('请先选择锅炉')
    if (!this.data.materialPackCode) return ui.error('请先扫码材料包')
    if (!this.data.previewImage) return ui.error('请先拍照')
    this.setData({ submitting: true })
    try {
      ui.showLoading('创建巡检中')
      const res = await request({
        url: '/inspections/create',
        method: 'POST',
        data: { boilerId: state.currentBoiler.id, materialPackId: this.data.materialPackId, inspectionType: 'daily' }
      })
      const result = await request({ url: '/inspections/recognize', method: 'POST', data: { inspectionId: res.inspectionId } })
      wx.setStorageSync('BG_LAST_RESULT', result)
      wx.setStorageSync('BG_LAST_INSPECTION_ID', res.inspectionId)
      wx.navigateTo({ url: '/pages/recognizing/recognizing' })
    } catch (e) {
      ui.error('巡检失败')
    } finally {
      ui.hideLoading()
      this.setData({ submitting: false })
    }
  }
})
