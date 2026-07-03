// config/index.js
// 环境配置：默认仍可使用 mock；切到真实后端时，把 useMock 改为 false，并配置 baseURL。
module.exports = {
  useMock: true,
  baseURL: 'https://api.example.com',
  timeout: 15000
}
