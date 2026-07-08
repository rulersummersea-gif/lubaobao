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

## 本地后台测试环境

本地后台、API、MySQL 使用独立端口和独立数据卷，不影响云主机环境。
本地 API 使用 `backend/Dockerfile.local` 构建，这是专门给本机测试用的镜像配置；云主机仍使用 `backend/Dockerfile`。

```bash
docker compose -f docker-compose.local.yml up -d --build
```

启动后访问：

```text
后台测试页：http://127.0.0.1:28081/
API 测试地址：http://127.0.0.1:28080
API 文档：http://127.0.0.1:28080/docs
本地 MySQL：127.0.0.1:23306
```

后台默认账号：

```text
admin / Admin@123
entadmin / Ent@123
inspector / Inspect@123
```

停止本地环境：

```bash
docker compose -f docker-compose.local.yml down
```

如需清空本地测试库：

```bash
docker compose -f docker-compose.local.yml down -v
```

## 切换真实后端
1. 修改 `config/index.js` 中 `useMock=false`
2. 设置 `baseURL`
3. 按 `api/index.js` 路由替换为真实接口
