const { request } = require('./index')

function verifyMaterialPack(code) {
  const url = '/material-packs/verify'
  return request({ url, method: 'POST', data: { code } })
}

function resolveMaterialPackScene(scene) {
  return request({ url: '/material-packs/resolve-scene', method: 'POST', data: { scene } })
}

function getMaterialPacks(params = {}) {
  return request({ url: '/material-packs', method: 'GET', data: params })
}

function activateMaterialPack(data) {
  const url = '/material-packs/activate'
  return request({ url, method: 'POST', data })
}

function getActiveMaterialPack(boilerId) {
  return request({ url: '/material-packs/active', method: 'GET', data: { boilerId } })
}

module.exports = { verifyMaterialPack, resolveMaterialPackScene, getMaterialPacks, activateMaterialPack, getActiveMaterialPack }
