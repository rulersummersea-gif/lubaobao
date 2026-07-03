# 炉保保智能小程序原型 / 可开发骨架

## 当前能力
- 登录页（Mock）
- 首页工作台
- 锅炉选择
- 材料包校验与激活
- 巡检发起（Mock识别）
- 巡检结果页
- 巡检记录列表/详情
- 报告页
- 本地状态存储
- API/Mock 服务分层

## 目录结构
- `api/` 请求入口
- `config/` 配置
- `services/` mock服务
- `store/` 本地状态
- `pages/` 页面
- `utils/` mock数据

## 导入
微信开发者工具直接导入本目录。

## 切换真实后端
1. 修改 `config/index.js` 中 `useMock=false`
2. 设置 `baseURL`
3. 按 `api/index.js` 路由替换为真实接口
