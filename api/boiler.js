const { request } = require('./index')
function getBoilers() {
  return request({ url: '/boilers' })
}
function createBoiler(data) {
  return request({ url: '/boilers/create', method: 'POST', data })
}
module.exports = { getBoilers, createBoiler }
