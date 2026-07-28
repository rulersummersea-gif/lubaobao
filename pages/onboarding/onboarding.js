const config = require('../../config/index')
const { verifyMaterialPack, resolveMaterialPackScene } = require('../../api/material-pack')
const { completeOnboarding } = require('../../api/auth')
const { getState, saveLastBoiler, setState } = require('../../store/app-state')
const { setToken } = require('../../utils/auth')
const ui = require('../../utils/ui')

function extractPackCode(raw) {
  const value = String(raw || '').trim()
  if (!value) return ''
  try {
    const parsed = JSON.parse(value)
    if (parsed.packCode || parsed.code) return String(parsed.packCode || parsed.code).trim()
  } catch (e) {}
  const match = value.match(/[?&](?:packCode|code)=([^&#]+)/i)
  if (match) return decodeURIComponent(match[1])
  return value
}

Page({
  data: {
    reason: 'first_login',
    reasonText: '首次登录，请先扫描材料包完成绑定。',
    code: '',
    pack: null,
    needsRegistration: false,
    currentBoilerName: '',
    userName: '',
    submitting: false,
    isLocal: config.getEnvKey() === 'local',
    boilerTypes: ['蒸汽锅炉'],
    form: {
      enterpriseName: '',
      deviceCode: '',
      productNo: '',
      model: '',
      deviceType: '蒸汽锅炉',
      ratedCapacity: '',
      ratedPressure: '',
      fuelType: '',
      manufacturer: ''
    }
  },

  onLoad(options = {}) {
    const reason = options.reason || 'first_login'
    const state = getState()
    let scene = ''
    try { scene = decodeURIComponent(options.scene || '') } catch (e) { scene = options.scene || '' }
    if (scene && !state.token) {
      wx.reLaunch({ url: `/pages/login/login?scene=${encodeURIComponent(scene)}` })
      return
    }
    const reasonText = reason === 'scan_code'
      ? '已识别材料包，请确认使用人和绑定信息。'
      : reason === 'pack_expired'
      ? '当前材料包已经过期，请扫描新的材料包继续使用。'
      : reason === 'pack_invalid'
        ? '当前材料包已失效，请扫描新的材料包继续使用。'
        : reason === 'pack_missing'
          ? '当前锅炉暂无有效材料包，请扫描材料包完成绑定。'
        : '首次登录，请先扫描材料包完成企业用户和锅炉绑定。'
    const savedName = state.user && !['微信用户', '测试用户'].includes(state.user.name) ? state.user.name : ''
    this.setData({
      reason,
      reasonText,
      userName: savedName,
      currentBoilerName: state.currentBoiler ? state.currentBoiler.name : ''
    })
    if (scene) this.loadPackByScene(scene)
  },

  onUserNameInput(e) {
    this.setData({ userName: e.detail.value })
  },

  onFormInput(e) {
    const key = e.currentTarget.dataset.key
    this.setData({ [`form.${key}`]: e.detail.value })
  },

  async scanPack() {
    try {
      const scanRes = await new Promise((resolve, reject) => {
        wx.scanCode({ scanType: ['qrCode'], success: resolve, fail: reject })
      })
      const code = extractPackCode(scanRes.result)
      if (!code) return ui.error('未识别到材料包编码')
      await this.loadPack(code)
    } catch (e) {
      if (e && String(e.errMsg || '').includes('cancel')) return
      ui.error(e.message || '扫码失败')
    }
  },

  saveSessionAndEnter(res, successText = '绑定成功') {
    setToken(res.token)
    saveLastBoiler(res.user && res.user.id, res.currentBoiler)
    setState({
      token: res.token,
      user: res.user,
      enterprise: res.enterprise,
      currentBoiler: res.currentBoiler,
      onboarding: res.onboarding
    })
    const app = getApp()
    app.globalData.user = res.user
    app.globalData.enterprise = res.enterprise
    app.globalData.currentBoiler = res.currentBoiler
    app.globalData.isLoggedIn = true
    ui.success(successText)
    setTimeout(() => wx.switchTab({ url: '/pages/index/index' }), 300)
  },

  async quickPass() {
    if (this.data.submitting) return
    this.setData({ submitting: true })
    try {
      ui.showLoading('测试绑定中')
      const res = await completeOnboarding({ packCode: 'PACK-001', userName: '本地灰测用户' })
      this.saveSessionAndEnter(res, '测试通过')
    } catch (e) {
      ui.error(e.message || '测试通过失败')
    } finally {
      ui.hideLoading()
      this.setData({ submitting: false })
    }
  },

  async loadPack(code) {
    try {
      ui.showLoading('校验材料包')
      const res = await verifyMaterialPack(code)
      const pack = res.pack || res
      if (pack.status === 'expired' || pack.status === 'invalid' || pack.status === 'exhausted') {
        throw new Error('材料包已过期或不可用')
      }
      const state = getState()
      this.setData({ code, pack, needsRegistration: !pack.boilerId && !state.currentBoiler })
      ui.success('材料包有效')
    } catch (e) {
      this.setData({ code: '', pack: null, needsRegistration: false })
      ui.error(e.message || '材料包校验失败')
    } finally {
      ui.hideLoading()
    }
  },

  async loadPackByScene(scene) {
    try {
      ui.showLoading('识别材料包')
      const res = await resolveMaterialPackScene(scene)
      const pack = res.pack || res
      const state = getState()
      this.setData({
        code: pack.code,
        pack,
        needsRegistration: !pack.boilerId && !state.currentBoiler
      })
      ui.success('材料包已识别')
    } catch (e) {
      this.setData({ code: '', pack: null, needsRegistration: false })
      ui.error(e.message || '材料包识别失败')
    } finally {
      ui.hideLoading()
    }
  },

  validate() {
    if (!this.data.pack || !this.data.code) return '请先扫描材料包'
    if (!String(this.data.userName || '').trim()) return '请填写使用人姓名'
    if (!this.data.needsRegistration) return ''
    const form = this.data.form
    const required = ['enterpriseName', 'deviceCode', 'productNo', 'model', 'deviceType']
    if (required.some((key) => !String(form[key] || '').trim())) return '请填写完整企业和锅炉信息'
    return ''
  },

  async submit() {
    if (this.data.submitting) return
    const error = this.validate()
    if (error) return ui.error(error)
    const form = this.data.form
    const state = getState()
    const payload = {
      packCode: this.data.code,
      userName: this.data.userName.trim(),
      boilerId: state.currentBoiler && state.currentBoiler.id
    }
    if (this.data.needsRegistration) {
      payload.enterpriseName = form.enterpriseName.trim()
      payload.boiler = {
        deviceCode: form.deviceCode.trim(),
        productNo: form.productNo.trim(),
        model: form.model.trim(),
        deviceType: form.deviceType.trim(),
        ratedCapacity: form.ratedCapacity.trim(),
        ratedPressure: form.ratedPressure.trim(),
        fuelType: form.fuelType.trim(),
        manufacturer: form.manufacturer.trim()
      }
    }

    this.setData({ submitting: true })
    try {
      ui.showLoading('正在绑定')
      const res = await completeOnboarding(payload)
      this.saveSessionAndEnter(res)
    } catch (e) {
      ui.error(e.message || '绑定失败')
    } finally {
      ui.hideLoading()
      this.setData({ submitting: false })
    }
  }
})
