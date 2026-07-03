const { request } = require('./index')
function getBoilers() {
  return request({ url: '/boilers' })
}
module.exports = { getBoilers }
