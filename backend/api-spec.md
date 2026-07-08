# 炉保保后端接口联调文档（V1）

## 通用规范
- Base URL: `http://49.232.174.76:18080`
- 认证：`Authorization: Bearer <token>`
- 返回：
```json
{ "code": 0, "message": "ok", "data": {} }
```

---

## 1. 登录
### POST `/auth/wx-login`
请求：
```json
{ "code": "wx.login返回code" }
```
响应：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "token": "jwt",
    "user": { "id": 1, "name": "张三", "role": "inspector", "enterpriseId": 1 },
    "enterprise": { "id": 1, "name": "华能蒸汽示范工厂" }
  }
}
```

## 2. 企业与锅炉
### GET `/enterprises`
查询企业列表。

### POST `/enterprises`
新增企业，需要 `platform_admin`。
```json
{ "name": "华能示范工厂", "code": "HN-DEMO" }
```

### PUT `/enterprises/{id}`
编辑企业名称、编码或状态，需要 `platform_admin`。
```json
{ "name": "华能示范工厂", "code": "HN-DEMO", "status": "active" }
```

### PATCH `/enterprises/{id}/status`
启用或停用企业，需要 `platform_admin`。
```json
{ "status": "disabled" }
```

### GET `/boilers?enterpriseId=1`
### POST `/boilers`
锅炉入参（12字段）：
```json
{
  "enterpriseId": 1,
  "deviceCode": "110010709202500028",
  "productNo": "MQ251254007W",
  "model": "DZA4-1.25-SCI",
  "deviceType": "蒸汽锅炉",
  "ratedCapacity": "4t/h",
  "ratedPressure": 1.25,
  "ratedSteamTemp": 194,
  "fuelType": "生物质颗粒",
  "thermalEfficiency": 84.2,
  "manufacturer": "青岛胜利锅炉有限公司",
  "manufactureDate": "2025-08-01",
  "licenseNo": "TS2110709-2027"
}
```

## 3. 检测包
### GET `/material-packs?enterpriseId=1`
查询企业检测包列表。

### POST `/material-packs`
```json
{ "code": "PACK-002", "enterpriseId": 1, "type": "基础版", "expireAt": "2027-12-31" }
```

### POST `/material-packs/verify`
```json
{ "code": "PACK-001" }
```

### POST `/material-packs/activate`
```json
{ "code": "PACK-001", "enterpriseId": 1, "boilerId": 1001 }
```

### POST `/material-packs/unbind`
```json
{ "code": "PACK-001" }
```

### POST `/material-packs/invalidate`
```json
{ "code": "PACK-001" }
```

## 4. 巡检
### POST `/inspections`
```json
{ "boilerId": 1001, "materialPackId": 5001, "inspectionType": "daily" }
```

### POST `/inspections/create`
同 `/inspections`，作为当前灰测兼容别名。

### POST `/inspections/upload-image`
微信小程序上传图片接口：
- `multipart/form-data`
- `file`: 图片文件
- `inspectionId`: 巡检ID

### POST `/inspections/:id/upload`
同上，REST 风格上传别名。

### POST `/inspections/recognize`
```json
{ "inspectionId": 9001 }
```

### GET `/inspections/result?inspectionId=9001`

### POST `/inspections/submit`
```json
{ "inspectionId": 9001, "remark": "补加药剂后复测" }
```

## 5. 记录与报告
### GET `/inspections`
支持筛选：
```text
/inspections?status=submitted&boilerId=1001
```
### GET `/records/:id`
### GET `/record-detail?id=9001`
### GET `/reports/monthly?enterpriseId=1&month=2026-07`

## 6. 用户权限
### POST `/auth/admin-login`
后台账号登录，账号来自数据库 `users` 表，密码使用 PBKDF2-SHA256 加密保存。

灰测默认账号：
- 平台管理员：`admin / Admin@123`
- 企业管理员：`entadmin / Ent@123`
- 巡检员：`inspector / Inspect@123`

### GET `/users`
返回数据库用户列表，需要 `platform_admin` 或 `enterprise_admin`。

### POST `/users`
新增后台用户，需要 `platform_admin` 或 `enterprise_admin`。
```json
{ "username": "worker01", "password": "Init@123", "name": "巡检员A", "role": "inspector", "enterpriseId": 1 }
```

### PUT `/users/{id}`
编辑用户姓名、角色、企业、状态或密码。密码为空时不修改密码。
```json
{ "name": "巡检员A", "role": "inspector", "enterpriseId": 1, "status": "active", "password": "New@123" }
```

### PATCH `/users/{id}/status`
启用或禁用用户。
```json
{ "status": "disabled" }
```

### 当前角色权限
- `platform_admin`：可查看用户、创建锅炉、创建/作废/解绑检测包。
- `enterprise_admin`：可管理本企业用户、创建本企业锅炉、创建/作废/解绑本企业检测包；不能创建或修改平台管理员。
- `inspector`：保留小程序巡检流程权限，可登录、选锅炉、校验/激活检测包、创建巡检、上传图片、识别、提交和查看记录。

---

## 状态机约束
- inspection: `created -> uploaded -> recognizing -> done -> submitted`
- pack: `unactivated -> activated -> in_use -> exhausted/expired/invalid`
- bind: 只能绑定同企业内 `boiler` 与 `pack`
