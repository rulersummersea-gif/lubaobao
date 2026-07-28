const config = require('../config/index')
const { request } = require('./index')

function wxLogin(code) {
  // mock: /auth/login ; real: /auth/wx-login
  const url = config.useMock ? '/auth/login' : '/auth/wx-login'
  return request({ url, method: 'POST', data: { code } })
}

function getOnboardingStatus() {
  return request({ url: '/auth/onboarding-status' })
}

function completeOnboarding(data) {
  return request({ url: '/auth/complete-onboarding', method: 'POST', data })
}

function saveCurrentBoiler(boilerId) {
  return request({ url: '/auth/current-boiler', method: 'POST', data: { boilerId } })
}

module.exports = { wxLogin, getOnboardingStatus, completeOnboarding, saveCurrentBoiler }
