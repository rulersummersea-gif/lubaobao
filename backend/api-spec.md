# 炉保保后端接口联调文档（V1）

## 通用规范
- Base URL: `/api/v1`
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
### GET `/enterprises/:id`
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
### POST `/packs`
### POST `/packs/activate`
```json
{ "packId": 5001 }
```
### POST `/packs/bind`
```json
{ "enterpriseId": 1, "boilerId": 1001, "packId": 5001, "bindRule": "shared" }
```
### GET `/packs?enterpriseId=1`

## 4. 巡检
### POST `/inspections`
```json
{ "enterpriseId": 1, "boilerId": 1001, "packId": 5001, "inspectionType": "daily" }
```
### POST `/inspections/:id/upload`
- form-data: `file`

### POST `/inspections/:id/recognize`
### GET `/inspections/:id/result`

### POST `/inspections/:id/submit`
```json
{ "remark": "补加药剂后复测" }
```

## 5. 记录与报告
### GET `/records?enterpriseId=1&boilerId=1001&page=1&pageSize=20`
### GET `/records/:id`
### GET `/reports/monthly?enterpriseId=1&month=2026-07`
### GET `/reports/monthly/boiler?boilerId=1001&month=2026-07`

---

## 状态机约束
- inspection: `created -> uploaded -> recognizing -> done -> submitted`
- pack: `unactivated -> activated -> in_use -> exhausted/expired/invalid`
- bind: 只能绑定同企业内 `boiler` 与 `pack`
