// config/index.js
// 运行环境配置：支持 mock / real 一键切换
const ENV = {
  local: {
    name: 'local',
    useMock: false,
    baseURL: 'http://127.0.0.1:28080',
    timeout: 15000
  },
  dev: {
    name: 'dev',
    useMock: true,
    baseURL: 'http://49.232.174.76:18080',
    timeout: 15000
  },
  staging: {
    name: 'staging',
    useMock: false,
    baseURL: 'http://49.232.174.76:18080',
    timeout: 15000
  },
  prod: {
    name: 'prod',
    useMock: false,
    baseURL: 'http://49.232.174.76:18080',
    timeout: 15000
  }
}

const DEFAULT_ENV_KEY = 'local'

function getEnvKey() {
  try {
    return wx.getStorageSync('BG_ENV') || DEFAULT_ENV_KEY
  } catch (e) {
    return DEFAULT_ENV_KEY
  }
}

function getConfig() {
  const key = getEnvKey()
  return ENV[key] || ENV[DEFAULT_ENV_KEY]
}

function setEnv(envKey) {
  if (!ENV[envKey]) throw new Error('无效环境: ' + envKey)
  wx.setStorageSync('BG_ENV', envKey)
  return ENV[envKey]
}

module.exports = {
  ENV,
  getConfig,
  setEnv,
  getEnvKey,
  // 向后兼容旧用法
  get useMock() { return getConfig().useMock },
  get baseURL() { return getConfig().baseURL },
  get timeout() { return getConfig().timeout }
}
