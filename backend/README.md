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
GET  /material-packs
POST /material-packs
POST /material-packs/verify
POST /material-packs/activate
POST /inspections
POST /inspections/upload-image
POST /inspections/recognize
GET  /inspections/result
POST /inspections/submit
GET  /inspections
GET  /records/{id}
GET  /reports/monthly
```
