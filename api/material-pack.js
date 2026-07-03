const { request } = require('./index')
function verifyMaterialPack(code) {
  return request({ url: '/material-packs/verify', method: 'POST', data: { code } })
}
function activateMaterialPack(data) {
  return request({ url: '/material-packs/activate', method: 'POST', data })
}
module.exports = { verifyMaterialPack, activateMaterialPack }
