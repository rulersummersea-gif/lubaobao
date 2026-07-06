const { request } = require('./index')

function verifyMaterialPack(code) {
  const url = '/material-packs/verify'
  return request({ url, method: 'POST', data: { code } })
}

function activateMaterialPack(data) {
  const url = '/material-packs/activate'
  return request({ url, method: 'POST', data })
}

module.exports = { verifyMaterialPack, activateMaterialPack }
