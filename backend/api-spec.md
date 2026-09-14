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

登录响应同时返回 `onboarding.required` 和 `onboarding.canInspect`。首次登录且从未绑定材料包时 `required=true`，必须进入扫码页；材料包过期时仍可进入首页，但 `canInspect=false`，更换材料包后才能巡检。

### GET `/auth/onboarding-status`
读取当前用户上次选择锅炉的材料包、企业和锅炉绑定状态。

### POST `/auth/current-boiler`
```json
{ "boilerId": 1001 }
```
保存当前用户最后选择的锅炉。选择结果保存在服务器，用户更换设备或重新登录后仍会恢复；响应同时返回该锅炉最新的 `onboarding` 状态。

### POST `/auth/complete-onboarding`
```json
{
  "packCode": "PACK-001",
  "userName": "张三",
  "boilerId": 1001,
  "enterpriseName": "示范企业",
  "boiler": {
    "deviceCode": "D-1001",
    "productNo": "P-1001",
    "model": "DZL6-1.25",
    "deviceType": "蒸汽锅炉",
    "ratedCapacity": "6t/h",
    "ratedPressure": "1.25"
  }
}
```
已有锅炉档案时传 `boilerId`，未绑定材料包会绑定到该锅炉；首次登记新锅炉时传 `boiler`。同一用户可以为不同锅炉分别绑定有效材料包，绑定新包不会停用其他锅炉的材料包。

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

## 3. 客户账户
客户账户与企业一一对应。业务流程为：创建待付款订单、登记收款、生成服务周期、执行季度发包。试用账户为 1 个月、1 个材料包；订阅订单按季度拆分，每季度 3 个材料包，同一季度材料包使用相同到期日。

### GET `/customers`
查询客户账户、当前服务周期和已分配材料包数量，需要后台管理权限。

### POST `/customers`
建立客户账户并创建待付款订阅订单，需要 `platform_admin`。此时不会生成服务周期或材料包。
```json
{
  "enterpriseId": 1,
  "accountType": "subscription",
  "startDate": "2026-07-21",
  "termQuarters": 4,
  "amountDue": 12000,
  "contractNo": "HT-2026-001",
  "salesOwner": "销售A",
  "contactName": "张经理",
  "contactPhone": "13800000000",
  "notes": "季度订阅"
}
```
`accountType` 支持 `trial` 和 `subscription`。

新客户也可以不传 `enterpriseId`，改为提交 `enterpriseName` 和可选的 `enterpriseCode`。后端会在同一事务中创建企业档案、客户账户和待付款订单；同名企业已存在时会要求选择已有企业，避免重复档案。

### POST `/customers/{id}/renew`
创建续费待付款订单，或创建试用转订阅订单。未传 `startDate` 时，新订单接在当前服务期限之后。
```json
{ "accountType": "subscription", "termQuarters": 1, "amountDue": 3000 }
```

### GET `/subscription-orders`
查询订阅订单、应收、实收和付款状态。

### POST `/subscription-orders/{id}/confirm-payment`
登记一次收款，支持分次收款。累计实收达到应收金额后，订单转为已付款并自动拆分服务周期；此时仍不创建材料包。
```json
{
  "amount": 3000,
  "paidAt": "2026-07-21 10:00:00",
  "paymentMethod": "bank_transfer",
  "transactionNo": "BANK-20260721-001"
}
```

### GET `/subscription-orders/{id}/payments`
查询订单的全部收款记录。

### POST `/subscription-orders/{id}/cancel`
取消尚未收款的待付款订单，需要平台管理员权限。已有部分收款的订单不能直接取消。
```json
{ "reason": "客户暂缓采购" }
```

### POST `/subscription-orders/{id}/refund`
退回订单的全部已收金额并关闭订单，需要平台管理员权限；支持部分收款订单和已付款订单。接口会撤销已生成的服务周期，并将该订单下未激活的材料包回收作废；存在已激活或已绑定用户的材料包时会拒绝退款，需先完成解绑和作废。
```json
{ "reason": "合同终止，双方确认退款" }
```

### GET `/subscription-orders/{id}/events`
查询订单取消、退款等异常操作流水，包括原因、金额、操作人与时间。

### GET `/customers/{id}/periods`
查询该客户历次服务周期、季度发包状态及材料包数量。

### GET `/customers/{id}/detail`
返回客户账户概况以及近期订阅订单、服务周期、材料包、锅炉、巡检和待处理服务任务。材料包、锅炉、巡检和服务任务按客户企业归集；企业管理员只能查看本企业客户。

### POST `/customer-periods/{id}/allocate-packs`
对已付款订单生成的季度发包任务执行材料包分配。试用周期生成 1 包，订阅季度生成 3 包，材料包统一使用该周期结束日期；未来周期材料包在周期开始前不能扫码使用。

### PATCH `/customers/{id}/status`
启用或停用客户账户。停用后，该客户周期内的材料包不能扫码、激活或巡检。
```json
{ "status": "disabled" }
```

## 4. 检测包
### GET `/material-packs?enterpriseId=1`
查询企业检测包列表。

### POST `/material-packs`
```json
{
  "code": null,
  "enterpriseId": 1,
  "type": "基础版",
  "expireAt": "2027-12-31",
  "batchNo": "202607-A",
  "salesOrderNo": "SO-202607-001",
  "warehouseLocation": "A库-01",
  "productionDate": "2026-07-20"
}
```
`code` 留空时由服务端生成唯一编码，同时生成独立二维码令牌。

### POST `/material-packs/batch`
```json
{
  "enterpriseId": 1,
  "quantity": 50,
  "codePrefix": "LB",
  "type": "基础版",
  "expireAt": "2027-12-31",
  "batchNo": "202607-A",
  "salesOrderNo": "SO-202607-001",
  "warehouseLocation": "A库-01",
  "productionDate": "2026-07-20"
}
```
一次最多入库 `200` 个材料包，批量操作在同一事务中完成。

### GET `/material-packs/{id}/qr`
返回材料包编码和二维码载荷。

### GET `/material-packs/{id}/qr.png`
返回可下载、打印的 PNG 二维码。

### GET `/material-packs/{id}/mini-code`
返回小程序码生成状态、入口页面、场景码和微信版本。配置 `WX_APPID`、`WX_APPSECRET` 后 `codeType=miniprogram`；未配置时返回 `fallback_qr`。

### GET `/material-packs/{id}/mini-code.png`
返回可打印的微信小程序码。正式码扫描后直达材料包绑定页；未配置微信凭证时返回普通二维码用于灰测。

### POST `/material-packs/{id}/mark-printed`
记录二维码最近打印时间。

### POST `/material-packs/verify`
```json
{ "code": "PACK-001", "qrToken": "二维码中的令牌，可选" }
```
校验成功后返回材料包的 `boilerId`、`boilerName`、`status` 和有效期，巡检端据此确认材料包与当前锅炉一致。

### GET `/material-packs/active?boilerId=1001`
查询当前用户指定锅炉的有效材料包。有效时返回 `available=true` 和材料包；未绑定、已过期或不可用时返回 `available=false`、原因和引导文案，小程序据此拦截巡检并进入扫码绑定页。

### POST `/material-packs/resolve-scene`
```json
{ "scene": "小程序码中的场景令牌" }
```
小程序扫码进入后用场景令牌还原材料包。未登录用户先登录并保留该令牌；老用户确认绑定当前锅炉，新用户继续登记企业和锅炉。

### GET `/material-pack-binding-events`
后台查询材料包扫码与绑定审计流水。支持 `enterpriseId`、`eventType`、`status`、`keyword` 和 `limit` 筛选；企业管理员只能查看本企业记录。

事件动作包括扫码识别、首次绑定、更换材料包、解除绑定和作废材料包；记录材料包、用户、企业、锅炉、来源、结果、说明与发生时间。未知随机二维码不写入审计表。

### POST `/material-packs/activate`
```json
{ "code": "PACK-001", "enterpriseId": 1, "boilerId": 1001 }
```
激活/绑定时会校验材料包、锅炉属于同一企业；后台管理页已改为选择真实锅炉，不再固定绑定 `1001`。

### POST `/material-packs/unbind`
```json
{ "code": "PACK-001" }
```
解绑会同步结束该材料包当前有效的用户绑定，并将材料包恢复为未激活状态。

### POST `/material-packs/invalidate`
```json
{ "code": "PACK-001" }
```
作废会同步结束该材料包当前有效的用户绑定。

## 5. 巡检
### POST `/inspections`
```json
{ "boilerId": 1001, "materialPackId": 5001, "inspectionType": "daily", "sampleType": "combined", "retestTaskId": null }
```
创建时会校验材料包已激活、已绑定当前锅炉，并且材料包和锅炉属于同一企业。
新巡检默认使用 `combined`：一张照片同时包含软化水2项与炉水6项。`softened_water` 和 `boiler_water` 仅用于兼容历史单水样记录。
复测巡检时传 `inspectionType: "retest"` 和对应 `retestTaskId`，识别完成后会自动回填到原复测任务。

### POST `/inspections/create`
同 `/inspections`，作为当前灰测兼容别名。

### POST `/inspections/upload-image`
微信小程序上传图片接口：
- `multipart/form-data`
- `file`: 图片文件
- `inspectionId`: 巡检ID
- `file`: JPG、PNG或WebP图片，最大12MB

上传后返回图片尺寸、大小、亮度、对比度、清晰度、质量评分、质量状态和问题列表。`qualityStatus` 支持 `pass`、`review`、`reject`；同时返回 `qualitySummary`、`canProceed` 和 `nextAction`。`review` 可继续灰测但后台需重点复核，`reject` 必须重拍且不能进入识别。严重亮度、对比度、清晰度、压缩或分辨率问题均会判为 `reject`。

### POST `/inspections/:id/upload`
同上，REST 风格上传别名。

### POST `/inspections/recognize`
```json
{
  "inspectionId": 9001,
  "values": {
    "softened_ph": "7.0",
    "softened_hardness": "0.02",
    "ph": "8.2",
    "phosphate": "8",
    "sulfite": "18",
    "alkalinity": "22",
    "chloride": "320",
    "hardness": "0.05"
  }
}
```
灰测阶段一次录入8个读数：软化水pH、软化水硬度及炉水六项。未来AI模块只输出读数、置信度和算法版本，不判断合格状态、不生成诊断；后端规则引擎按两组独立标准完成判断、诊断和复测任务。识别前必须上传照片，质量状态为 `reject` 时拒绝继续。照片、质量指标和读数会写入检测样本，供后续算法训练和人工复核。
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
当前版本使用统一入口和统一照片，但结果仍按水样分组：软化器出口软化水检测pH和硬度，不按锅炉压力段匹配；炉水检测原有6项并按额定压力匹配标准。软化水限值需在后台按现场方案确认，未配置时结果标记为 `unknown`，不会套用炉水标准。
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

### GET `/inspection-samples`
后台识别样本列表，需要 `platform_admin` 或 `enterprise_admin`。支持 `qualityStatus` 和 `labelStatus` 筛选，返回照片质量、人工值、AI值、确认值和审核信息。

### PUT `/inspection-samples/{inspectionId}/review`
审核检测样本。组合检测通过时必须提交完整8项确认值；历史单水样记录仍按软化水2项或炉水6项审核。剔除时可以只提交原因。
```json
{
  "labelStatus": "approved",
  "confirmedValues": {
    "ph": "8.2",
    "phosphate": "8",
    "sulfite": "18",
    "alkalinity": "22",
    "chloride": "320",
    "hardness": "0.05"
  },
  "note": "照片与人工读数一致"
}
```

### GET `/retest-tasks?enterpriseId=1&status=pending&boilerId=1001`
查询异常服务与复测任务。识别结果中存在 `retestPlan` 的诊断项会自动生成任务；小程序传 `boilerId` 后只返回当前锅炉任务。后台还支持：

- `inspectionId`：查询某次巡检关联的全部异常任务。
- `adviceStatus=pending_advice|advised`：筛选待填写或已填写专业意见。
- `level=critical|high|warning`：筛选风险等级。
- `keyword`：搜索锅炉名称、风险、标题或关联指标。

响应中的 `serviceStatus` 为 `pending_advice` 或 `advised`。

### GET `/retest-tasks/summary?enterpriseId=1`
返回待处理异常数、待填写专业意见数、已填写意见数和高风险待办数，用于后台异常服务工作台。

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
意见长度为5-500字。保存后小程序首页显示“已给出专业意见”，异常提醒页和巡检详情页同步显示意见内容、服务人员和保存时间；系统现场建议与服务人员专业意见分开展示。

## 6. 记录与报告
### GET `/inspections`
支持筛选，传 `boilerId` 后只返回当前锅炉记录：
```text
/inspections?status=submitted&boilerId=1001
```
### GET `/records/:id`
### GET `/record-detail?id=9001`
### GET `/reports/monthly?enterpriseId=1&month=2026-07`

月报按传入的自然月统计，只纳入状态为 `submitted` 的正式巡检记录。`month`
为空时使用服务器当前月份，格式错误时返回 400。返回平均健康评分、正式巡检数、
异常巡检数、锅炉数和本月建议；当月无记录时评分为 0，并提示完成计划巡检。

## 7. 用户权限
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
