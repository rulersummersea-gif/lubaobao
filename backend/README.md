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

默认使用 SQLite：

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
docker build -t lubaobao-api .
docker run -p 18080:18080 -v /tmp/lubaobao-data:/data lubaobao-api
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
