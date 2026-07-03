const { request } = require('./index')
function wxLogin(code) {
  return request({ url: '/auth/login', method: 'POST', data: { code } })
}
module.exports = { wxLogin }
