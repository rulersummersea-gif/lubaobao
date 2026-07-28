# 炉保保后端服务

这是用于正式化联调的 FastAPI 后端骨架，补齐当前小程序上线前的关键缺口：

- 材料包入库、查询、校验、激活
- 巡检创建
- 巡检图片上传
- 识别结果生成
- 巡检提交
- 巡检记录列表与详情
- 月报汇总

## 本地启动

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 18080 --reload
```

本地直接运行默认使用 SQLite：

```text
/tmp/lubaobao.sqlite3
/tmp/lubaobao_uploads
```

可通过环境变量修改：

```bash
export LUBAOBAO_DB=/data/lubaobao.sqlite3
export LUBAOBAO_UPLOAD_DIR=/data/uploads
```

## Docker 启动

```bash
cd backend
docker compose up -d --build
```

Docker Compose 会同时启动：

```text
lubaobao-api
lubaobao-mysql
```

MySQL 只在 Docker 内部网络开放，不暴露公网端口。默认联调库：

```text
MYSQL_DATABASE=lubaobao_dev
MYSQL_USER=lubaobao
MYSQL_PASSWORD=lubaobao_dev_password
```

如果只想用 SQLite 跑 API，可以不用 compose，直接执行本地启动命令。

## 本地后台测试环境

从项目根目录启动本地测试环境：

```bash
docker compose -f docker-compose.local.yml up -d --build
```

这套环境使用独立容器名、端口和数据卷：

```text
后台：http://127.0.0.1:28081/
API：http://127.0.0.1:28080
API 文档：http://127.0.0.1:28080/docs
MySQL：127.0.0.1:23306
```

后台页面默认 API 基地址是 `/api`，由本地 Nginx 代理到 `lubaobao-local-api`，所以不需要手动改成云主机地址。
本地 API 镜像使用 `Dockerfile.local`，不影响云服务器部署使用的 `Dockerfile`。

上线前安全要求：

```text
不要把 MySQL 3306/13306 暴露到公网。
API 通过 Docker 内部网络访问 lubaobao-mysql。
旧的公网 MySQL 容器如仍存在，应保持停止状态或备份后删除。
```

## 云服务器部署

登录服务器后执行：

```bash
curl -fsSL https://raw.githubusercontent.com/rulersummersea-gif/lubaobao/main/backend/deploy_server.sh -o /tmp/deploy_lubaobao.sh
chmod +x /tmp/deploy_lubaobao.sh
/tmp/deploy_lubaobao.sh
```

部署完成后验证：

```bash
curl http://127.0.0.1:18080/health
curl http://127.0.0.1:18080/
curl http://127.0.0.1:18080/material-packs?enterpriseId=1
```

## 默认测试数据

```text
企业：1 华能示范工厂
锅炉：1001 1号蒸汽锅炉
材料包：9001 PACK-001
```

## 关键接口

```text
GET  /health
POST /auth/wx-login
GET  /boilers
GET  /customers
POST /customers
POST /customers/{id}/renew
GET  /subscription-orders
POST /subscription-orders/{id}/confirm-payment
GET  /subscription-orders/{id}/payments
GET  /customers/{id}/periods
GET  /customers/{id}/detail
POST /customer-periods/{id}/allocate-packs
PATCH /customers/{id}/status
GET  /material-packs
POST /material-packs
POST /material-packs/batch
GET  /material-packs/{id}/qr
GET  /material-packs/{id}/qr.png
GET  /material-packs/{id}/mini-code
GET  /material-packs/{id}/mini-code.png
POST /material-packs/{id}/mark-printed
POST /material-packs/verify
POST /material-packs/resolve-scene
POST /material-packs/activate
GET  /material-pack-binding-events
POST /inspections
POST /inspections/upload-image
POST /inspections/recognize
GET  /inspections/result
POST /inspections/submit
GET  /inspections
GET  /records/{id}
GET  /reports/monthly
```

正式微信登录及小程序码需配置环境变量 `WX_APPID` 和 `WX_APPSECRET`。小程序码默认进入 `pages/onboarding/onboarding`，可通过 `MINIPROGRAM_BIND_PAGE` 调整；`WX_CODE_ENV_VERSION` 支持 `release`、`trial`、`develop`。未配置微信凭证时，后台生成普通二维码供本地灰测；配置后生成可直接打开小程序绑定页的正式小程序码。

## 灰测闭环验收

本地环境启动后，可运行：

```bash
sh backend/gray_acceptance.sh
```

脚本会依次验证登录与绑定、材料包校验、照片上传、六项人工读数、异常诊断、
后台专业意见、正常复测回填、历史详情、识别样本和自然月月报，并在本地库中
保留本次异常巡检与复测记录。
