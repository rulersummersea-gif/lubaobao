const config = require('../../config/index')
const { verifyPack } = require('../../api/index')
const { createInspection, uploadImage, recognizeInspection } = require('../../api/inspection')
const { getState } = require('../../store/app-state')
const ui = require('../../utils/ui')

Page({
  data: {
    currentBoiler: null,
    inspectionId: null,
    materialPackId: null,
    materialPackCode: '',
    previewImage: '',
    submitting: false
  },

  onShow() {
    const state = getState()
    this.setData({ currentBoiler: state.currentBoiler || null })
  },

  goChooseBoiler() { wx.navigateTo({ url: '/pages/boiler/boiler' }) },

  async mockScanPack() {
    const fallbackCode = 'PACK-001'
    if (config.useMock) {
      this.setData({ materialPackCode: fallbackCode, materialPackId: 9001 })
      ui.success('已模拟扫码')
      return
    }
    try {
      const code = fallbackCode
      const packRes = await verifyPack(code)
      this.setData({ materialPackCode: code, materialPackId: (packRes.pack && packRes.pack.id) || packRes.id })
      ui.success('材料包校验成功')
    } catch (e) {
      ui.error(e.message || '材料包校验失败')
    }
  },

  async mockTakePhoto() {
    if (config.useMock) {
      this.setData({ previewImage: '/images/mock-board.png' })
      ui.success('已模拟拍照')
      return
    }
    try {
      const chooseRes = await new Promise((resolve, reject) => {
        wx.chooseMedia({ count: 1, mediaType: ['image'], sourceType: ['camera', 'album'], success: resolve, fail: reject })
      })
      const filePath = chooseRes.tempFiles && chooseRes.tempFiles[0] && chooseRes.tempFiles[0].tempFilePath
      if (!filePath) return ui.error('未获取到图片')
      this.setData({ previewImage: filePath })
      ui.success('图片已选择')
    } catch (e) {
      ui.error('拍照失败')
    }
  },

  async startInspection() {
    if (this.data.submitting) return
    const state = getState()
    if (!state.currentBoiler) return ui.error('请先选择锅炉')
    if (!this.data.materialPackCode) return ui.error('请先扫码材料包')
    if (!this.data.previewImage) return ui.error('请先拍照')

    this.setData({ submitting: true })
    try {
      ui.showLoading('创建巡检中')
      const created = await createInspection({
        boilerId: state.currentBoiler.id,
        materialPackId: this.data.materialPackId,
        inspectionType: 'daily'
      })
      const inspectionId = created.inspectionId || created.id
      if (!inspectionId) throw new Error('创建巡检失败：缺少inspectionId')

      // 真实接口优先：上传图片 -> 发起识别；mock 下也兼容
      await uploadImage(this.data.previewImage, inspectionId)
      const result = await recognizeInspection({ inspectionId })

      wx.setStorageSync('BG_LAST_RESULT', result.result || result)
      wx.setStorageSync('BG_LAST_INSPECTION_ID', inspectionId)
      wx.navigateTo({ url: '/pages/recognizing/recognizing' })
    } catch (e) {
      ui.error(e.message || '巡检失败')
    } finally {
      ui.hideLoading()
      this.setData({ submitting: false })
    }
  }
})
