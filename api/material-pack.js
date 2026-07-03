const config = require('../config/index')
const { request } = require('./index')

function verifyMaterialPack(code) {
  const url = config.useMock ? '/material-packs/verify' : '/packs/verify'
  return request({ url, method: 'POST', data: { code } })
}

function activateMaterialPack(data) {
  const url = config.useMock ? '/material-packs/activate' : '/packs/activate'
  return request({ url, method: 'POST', data })
}

module.exports = { verifyMaterialPack, activateMaterialPack }
