const config = require('../config/index')
const { request } = require('./index')

function wxLogin(code) {
  // mock: /auth/login ; real: /auth/wx-login
  const url = config.useMock ? '/auth/login' : '/auth/wx-login'
  return request({ url, method: 'POST', data: { code } })
}

module.exports = { wxLogin }
