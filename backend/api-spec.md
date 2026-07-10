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
按企业查询锅炉列表。返回字段中预留 `status`，但当前阶段后台不提供启停操作。

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

### PUT `/boilers/{id}`
编辑锅炉档案资料，需要 `platform_admin` 或 `enterprise_admin`。
```json
{
  "enterpriseId": 1,
  "deviceCode": "110010709202500028",
  "productNo": "MQ251254007W",
  "model": "DZA4-1.25-SCI",
  "deviceType": "蒸汽锅炉",
  "ratedCapacity": "4t/h",
  "ratedPressure": "1.25",
  "ratedSteamTemp": "194",
  "fuelType": "生物质颗粒",
  "thermalEfficiency": "84.2",
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
激活/绑定时会校验材料包、锅炉属于同一企业；后台管理页已改为选择真实锅炉，不再固定绑定 `1001`。

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
{ "boilerId": 1001, "materialPackId": 5001, "inspectionType": "daily", "retestTaskId": null }
```
复测巡检时传 `inspectionType: "retest"` 和对应 `retestTaskId`，识别完成后会自动回填到原复测任务。

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
{
  "inspectionId": 9001,
  "values": {
    "ph": "8.2",
    "phosphate": "8",
    "sulfite": "18",
    "alkalinity": "22",
    "chloride": "320",
    "hardness": "0.05"
  }
}
```
灰测阶段支持人工录入 6 项试纸读数，后端按 `values` 直接生成诊断和复测任务；若未传 `values`，使用样例值兜底。照片上传仍保留，用于后续试纸照片识别算法训练和人工复核。
当前第一版锅水检测模板按优先级返回 6 项：
1. pH：pH试纸
2. 磷酸根：磷酸根试纸
3. 亚硫酸根：亚硫酸根试纸
4. 总碱度：总碱度试纸
5. 氯离子：氯离子试纸
6. 硬度：硬度试纸

每个检测项包含 `priority`、`method`、`normalRange`、`standardMin`、`standardMax`、`pressureSegment`、`ratedPressureMpa`、`standardMatched`、`standardSource`、`meaning`、`maintenance`，用于小程序和后台展示维护指导。
数据库同步维护 `water_test_items` 检测项目模板表、`water_quality_limits` 标准限值表，以及 `inspection_test_results` 单次检测结果明细表。
当前灰测标准来源标记为 `GB/T 1576 工业锅炉水质`，范围按工业蒸汽锅炉锅水/炉水压力段配置；识别时会读取锅炉额定压力并自动匹配对应压力段。正式上线前需结合锅炉额定压力、补给水处理方式和最新国标原文复核。
第一阶段产品坚持试纸优先，滴定、仪表或第三方检测只作为异常复核和高级能力，不作为日常小程序巡检的刚性流程。
当前版本只做锅水/炉水 6 项，不采集给水数据；数据库和标准表保留 `sample_type` 能力，后续可扩展给水/补给水。
识别结果会根据异常组合生成动态诊断，`diagnosis` 每项包含：
```json
{
  "riskCode": "scale",
  "riskType": "结垢风险",
  "level": "high",
  "title": "结垢风险预警",
  "reason": "硬度偏高且磷酸根偏低...",
  "advice": "检查软水器并补加防垢剂...",
  "fieldAction": "检查软水器盐箱、再生状态和加药泵；按现场药剂方案补加防垢剂/磷酸盐药剂，并安排一次排污。",
  "retestPlan": "处理后建议2小时内复测硬度、磷酸根和pH。",
  "supportNotice": "后台提醒：若连续两次出现硬度偏高且磷酸根偏低，服务支持人员需复核软水器状态、补水硬度和防垢药剂方案。",
  "relatedItems": ["hardness", "phosphate"],
  "relatedItemNames": "磷酸根、硬度"
}
```
现有组合规则：硬度高+磷酸根低、pH低+亚硫酸根低、氯离子高+总碱度高、磷酸根高+亚硫酸根高、pH高+总碱度高；未命中组合时按单项异常生成建议。
小程序端只展示 `fieldAction` 和 `retestPlan`，现场可执行动作限定为复测、排污、加药、药箱/加药泵/软水器基础检查。`supportNotice` 只在后台展示，由平台服务支持人员用于给出专业处理建议。

### GET `/water-quality-limits`
后台检测标准管理列表，需要 `platform_admin` 或 `enterprise_admin`。

### PUT `/water-quality-limits/{id}`
编辑检测标准上下限、单位、压力段、依据、备注或启停状态。
```json
{
  "minValue": 8.5,
  "maxValue": 10.5,
  "unit": "",
  "displayRange": "8.5-10.5",
  "pressureMinMpa": 0,
  "pressureMaxMpa": 3.8,
  "standardSource": "GB/T 1576 工业锅炉水质",
  "standardNote": "按现场锅炉压力段复核",
  "enabled": true
}
```

### POST `/water-quality-limits/reset`
恢复当前 6 项锅水检测默认灰测标准，需要后台管理员权限。

### GET `/inspections/result?inspectionId=9001`

### POST `/inspections/submit`
```json
{ "inspectionId": 9001, "remark": "补加药剂后复测" }
```

### GET `/retest-tasks?enterpriseId=1&status=pending`
查询待复测任务。识别结果中存在 `retestPlan` 的诊断项会自动生成复测任务。

响应示例：
```json
[
  {
    "id": 1,
    "inspectionId": 9001,
    "boilerName": "1号蒸汽锅炉",
    "riskType": "结垢风险",
    "title": "结垢风险预警",
    "desc": "处理后建议2小时内复测硬度、磷酸根和pH。",
    "fieldAction": "检查软水器盐箱、再生状态和加药泵...",
    "retestPlan": "处理后建议2小时内复测硬度、磷酸根和pH。",
    "supportNotice": "后台提醒：若连续两次出现硬度偏高且磷酸根偏低，服务支持人员需复核软水器状态、补水硬度和防垢药剂方案。",
    "relatedItemNames": "硬度、磷酸根",
    "status": "pending"
  }
]
```

### POST `/retest-tasks/{id}/complete`
标记复测任务已完成。小程序告警页使用该接口关闭待复测提醒。

### POST `/retest-tasks/{id}/resolve`
记录复测任务处理结果。处理逻辑不写死，可提交复测，也可不复测。
```json
{ "resolutionType": "no_retest", "note": "现场暂不复测，由后台继续跟进" }
```
提交复测结果时，创建巡检可传 `inspectionType: "retest"` 和 `retestTaskId`；识别完成后系统会自动回填 `retestInspectionId`，任务状态变为 `retested`。

### POST `/retest-tasks/{id}/service-advice`
后台服务支持人员保存专业处理意见，需要 `platform_admin` 或 `enterprise_admin`。
```json
{ "serviceAdvice": "已复核现场情况，建议先按排污制度执行一次定排，2小时后复测氯离子和总碱度。" }
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
