// utils/auth.js
// token 管理工具：统一读写登录令牌，供 request 层和页面使用。
const TOKEN_KEY = 'BG_TOKEN'
function getToken() { return wx.getStorageSync(TOKEN_KEY) || '' }
function setToken(token) { wx.setStorageSync(TOKEN_KEY, token || '') }
function clearToken() { wx.removeStorageSync(TOKEN_KEY) }
module.exports = { getToken, setToken, clearToken, TOKEN_KEY }
