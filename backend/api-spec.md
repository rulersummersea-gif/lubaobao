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
### POST `/material-packs/verify`
```json
{ "code": "BW-202607-000128" }
```
### POST `/material-packs/activate`
```json
{ "code": "BW-202607-000128", "enterpriseId": 1, "boilerId": 1001 }
```

## 4. 巡检
### POST `/inspections`
```json
{ "boilerId": 1001, "materialPackId": 5001, "inspectionType": "daily" }
```

### POST `/inspections/create`
同 `/inspections`，作为当前灰测兼容别名。

### POST `/inspections/recognize`
```json
{ "inspectionId": 9001 }
```

### GET `/inspections/result?inspectionId=9001`

## 5. 记录与报告
### GET `/inspections`
### GET `/reports/monthly?enterpriseId=1&month=2026-07`

---

## 状态机约束
- inspection: `created -> uploaded -> recognizing -> done -> submitted`
- pack: `unactivated -> activated -> in_use -> exhausted/expired/invalid`
- bind: 只能绑定同企业内 `boiler` 与 `pack`
