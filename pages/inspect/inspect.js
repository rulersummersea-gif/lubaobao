const config = require('../../config/index')
const { verifyPack } = require('../../api/index')
const { getMaterialPacks } = require('../../api/material-pack')
const { createInspection, uploadImage, recognizeInspection } = require('../../api/inspection')
const { getState } = require('../../store/app-state')
const ui = require('../../utils/ui')

Page({
  data: {
    currentBoiler: null,
    inspectionId: null,
    materialPackId: null,
    materialPackCode: '',
    materialPackBoilerId: null,
    materialPackBoilerName: '',
    previewImage: '',
    photoQuality: null,
    retestTask: null,
    waterItems: [
      { code: 'ph', name: 'pH', unit: '', value: '8.2', placeholder: '如 8.2' },
      { code: 'phosphate', name: '磷酸根', unit: 'mg/L', value: '8', placeholder: '如 8' },
      { code: 'sulfite', name: '亚硫酸根', unit: 'mg/L', value: '18', placeholder: '如 18' },
      { code: 'alkalinity', name: '总碱度', unit: 'mmol/L', value: '22', placeholder: '如 22' },
      { code: 'chloride', name: '氯离子', unit: 'mg/L', value: '320', placeholder: '如 320' },
      { code: 'hardness', name: '硬度', unit: 'mmol/L', value: '0.05', placeholder: '如 0.05' }
    ],
    submitting: false
  },

  onShow() {
    const state = getState()
    if (state.onboarding && state.onboarding.canInspect === false) {
      ui.error(state.onboarding.message || '请先更换材料包')
      const reason = encodeURIComponent(state.onboarding.reason || 'pack_expired')
      wx.navigateTo({ url: `/pages/onboarding/onboarding?reason=${reason}` })
      return
    }
    const retestTask = wx.getStorageSync('BG_RETEST_TASK') || null
    const currentBoiler = state.currentBoiler || null
    const targetBoilerId = (retestTask && retestTask.boilerId) || (currentBoiler && currentBoiler.id)
    const packChangedBoiler = this.data.materialPackBoilerId && targetBoilerId && Number(this.data.materialPackBoilerId) !== Number(targetBoilerId)
    this.setData({
      currentBoiler,
      retestTask,
      ...(packChangedBoiler ? {
        materialPackId: null,
        materialPackCode: '',
        materialPackBoilerId: null,
        materialPackBoilerName: ''
      } : {})
    })
    if (packChangedBoiler) ui.error('锅炉已变更，请重新校验材料包')
  },

  goChooseBoiler() { wx.navigateTo({ url: '/pages/boiler/boiler' }) },

  async setPackByCode(code, successText = '材料包校验成功') {
    const state = getState()
    const retestTask = this.data.retestTask
    const targetBoiler = retestTask
      ? { id: retestTask.boilerId, name: retestTask.boilerName }
      : state.currentBoiler
    if (!targetBoiler || !targetBoiler.id) throw new Error('请先选择锅炉')
    const packRes = await verifyPack(code)
    let pack = packRes.pack || packRes
    if (!config.useMock && !pack.boilerId) {
      const packs = await getMaterialPacks({ enterpriseId: pack.enterpriseId || 1 })
      const boundPack = (packs || []).find((item) => item.code === code)
      if (boundPack) pack = { ...pack, ...boundPack }
    }
    if (pack.status !== 'activated') throw new Error('材料包尚未激活')
    if (!pack.boilerId) throw new Error('材料包尚未绑定锅炉')
    if (Number(pack.boilerId) !== Number(targetBoiler.id)) {
      throw new Error(`材料包已绑定${pack.boilerName || '其他锅炉'}`)
    }
    this.setData({
      materialPackCode: code,
      materialPackId: pack.id,
      materialPackBoilerId: pack.boilerId,
      materialPackBoilerName: pack.boilerName || targetBoiler.name || ''
    })
    ui.success(successText)
  },

  async useTestPack() {
    const testCode = 'PACK-001'
    if (config.useMock) {
      const state = getState()
      const targetBoiler = this.data.retestTask
        ? { id: this.data.retestTask.boilerId, name: this.data.retestTask.boilerName }
        : state.currentBoiler
      if (!targetBoiler || !targetBoiler.id) return ui.error('请先选择锅炉')
      this.setData({
        materialPackCode: testCode,
        materialPackId: 9001,
        materialPackBoilerId: targetBoiler.id,
        materialPackBoilerName: targetBoiler.name || ''
      })
      ui.success('已使用测试包')
      return
    }
    try {
      await this.setPackByCode(testCode, '测试包校验成功')
    } catch (e) {
      ui.error(e.message || '材料包校验失败')
    }
  },

  async scanPack() {
    if (config.useMock) {
      this.useTestPack()
      return
    }
    try {
      const scanRes = await new Promise((resolve, reject) => {
        wx.scanCode({ success: resolve, fail: reject })
      })
      const code = scanRes.result || ''
      if (!code) return ui.error('未识别到材料包编码')
      await this.setPackByCode(code, '扫码校验成功')
    } catch (e) {
      ui.error(e.message || '扫码失败')
    }
  },

  async chooseInspectionImage() {
    if (config.useMock) {
      this.setData({ previewImage: '/images/mock-board.png', photoQuality: null })
      ui.success('已选择图片')
      return
    }
    try {
      const chooseRes = await new Promise((resolve, reject) => {
        wx.chooseMedia({ count: 1, mediaType: ['image'], sourceType: ['camera', 'album'], success: resolve, fail: reject })
      })
      const filePath = chooseRes.tempFiles && chooseRes.tempFiles[0] && chooseRes.tempFiles[0].tempFilePath
      if (!filePath) return ui.error('未获取到图片')
      this.setData({ previewImage: filePath, photoQuality: null })
      ui.success('图片已选择')
    } catch (e) {
      ui.error('拍照失败')
    }
  },

  onWaterValueInput(e) {
    const index = Number(e.currentTarget.dataset.index)
    const waterItems = this.data.waterItems.slice()
    waterItems[index].value = e.detail.value
    this.setData({ waterItems })
  },

  buildWaterValues() {
    const values = {}
    for (const item of this.data.waterItems) {
      const value = String(item.value || '').trim()
      if (!value) throw new Error(`请填写${item.name}`)
      const numberValue = Number(value)
      if (!Number.isFinite(numberValue) || numberValue < 0) throw new Error(`${item.name}读数格式不正确`)
      if (item.code === 'ph' && numberValue > 14) throw new Error('pH读数应在0至14之间')
      values[item.code] = value
    }
    return values
  },

  confirmInspection(boilerName, waterValues) {
    const lines = this.data.waterItems.map((item) => `${item.name}：${waterValues[item.code]}${item.unit ? ' ' + item.unit : ''}`)
    return new Promise((resolve) => {
      wx.showModal({
        title: `确认提交｜${boilerName}`,
        content: lines.join('\n'),
        confirmText: '确认提交',
        cancelText: '返回修改',
        success: (res) => resolve(Boolean(res.confirm)),
        fail: () => resolve(false)
      })
    })
  },

  cancelRetest() {
    const state = getState()
    const currentBoilerId = state.currentBoiler && state.currentBoiler.id
    const clearPack = this.data.materialPackBoilerId && currentBoilerId && Number(this.data.materialPackBoilerId) !== Number(currentBoilerId)
    wx.removeStorageSync('BG_RETEST_TASK')
    this.setData({
      retestTask: null,
      ...(clearPack ? {
        materialPackId: null,
        materialPackCode: '',
        materialPackBoilerId: null,
        materialPackBoilerName: ''
      } : {})
    })
    ui.success('已退出复测')
  },

  async startInspection() {
    if (this.data.submitting) return
    const state = getState()
    const retestTask = this.data.retestTask
    const boilerId = (retestTask && retestTask.boilerId) || (state.currentBoiler && state.currentBoiler.id)
    if (!boilerId) return ui.error('请先选择锅炉')
    if (!this.data.materialPackCode) return ui.error('请先扫码材料包')
    if (!this.data.previewImage) return ui.error('请先拍照')
    let waterValues
    try {
      waterValues = this.buildWaterValues()
    } catch (e) {
      return ui.error(e.message)
    }
    const boilerName = (retestTask && retestTask.boilerName) || (state.currentBoiler && state.currentBoiler.name) || `锅炉 #${boilerId}`
    const confirmed = await this.confirmInspection(boilerName, waterValues)
    if (!confirmed) return

    this.setData({ submitting: true })
    try {
      ui.showLoading('创建巡检中')
      const created = await createInspection({
        boilerId,
        materialPackId: this.data.materialPackId,
        inspectionType: retestTask ? 'retest' : 'daily',
        retestTaskId: retestTask ? retestTask.id : null
      })
      const inspectionId = created.inspectionId || created.id
      if (!inspectionId) throw new Error('创建巡检失败：缺少inspectionId')

      // 真实接口优先：上传图片 -> 发起识别；mock 下也兼容
      const uploadResult = await uploadImage(this.data.previewImage, inspectionId)
      const photoQuality = uploadResult.qualityStatus ? {
        status: uploadResult.qualityStatus,
        score: uploadResult.qualityScore,
        messages: (uploadResult.qualityFlags || []).map((item) => item.message)
      } : null
      this.setData({ photoQuality })
      if (photoQuality && photoQuality.status === 'reject') {
        throw new Error(photoQuality.messages.join('；') || '照片质量不合格，请重新拍摄')
      }
      const result = await recognizeInspection({ inspectionId, values: waterValues })

      wx.setStorageSync('BG_LAST_RESULT', result.result || result)
      wx.setStorageSync('BG_LAST_INSPECTION_ID', inspectionId)
      if (retestTask) wx.removeStorageSync('BG_RETEST_TASK')
      wx.navigateTo({ url: '/pages/recognizing/recognizing' })
    } catch (e) {
      ui.error(e.message || '巡检失败')
    } finally {
      ui.hideLoading()
      this.setData({ submitting: false })
    }
  }
})
