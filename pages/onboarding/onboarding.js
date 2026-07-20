const config = require('../../config/index')
const { verifyMaterialPack } = require('../../api/material-pack')
const { completeOnboarding } = require('../../api/auth')
const { getState, setState } = require('../../store/app-state')
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

  onLoad(options) {
    const reason = options.reason || 'first_login'
    const state = getState()
    const reasonText = reason === 'pack_expired'
      ? '当前材料包已经过期，请扫描新的材料包继续使用。'
      : reason === 'pack_invalid'
        ? '当前材料包已失效，请扫描新的材料包继续使用。'
        : '首次登录，请先扫描材料包完成企业用户和锅炉绑定。'
    const savedName = state.user && !['微信用户', '测试用户'].includes(state.user.name) ? state.user.name : ''
    this.setData({ reason, reasonText, userName: savedName })
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

  async useLocalTestPack() {
    await this.loadPack('PACK-001')
  },

  async loadPack(code) {
    try {
      ui.showLoading('校验材料包')
      const res = await verifyMaterialPack(code)
      const pack = res.pack || res
      if (pack.status === 'expired' || pack.status === 'invalid' || pack.status === 'exhausted') {
        throw new Error('材料包已过期或不可用')
      }
      this.setData({ code, pack, needsRegistration: !pack.boilerId })
      ui.success('材料包有效')
    } catch (e) {
      this.setData({ code: '', pack: null, needsRegistration: false })
      ui.error(e.message || '材料包校验失败')
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
    const payload = {
      packCode: this.data.code,
      userName: this.data.userName.trim()
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
      setToken(res.token)
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
      ui.success('绑定成功')
      setTimeout(() => wx.switchTab({ url: '/pages/index/index' }), 300)
    } catch (e) {
      ui.error(e.message || '绑定失败')
    } finally {
      ui.hideLoading()
      this.setData({ submitting: false })
    }
  }
})
