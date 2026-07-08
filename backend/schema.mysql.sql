CREATE DATABASE IF NOT EXISTS lubaobao_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lubaobao_dev;

CREATE TABLE IF NOT EXISTS enterprises (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  code VARCHAR(64) NULL UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS boilers (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  enterprise_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL,
  device_code VARCHAR(64) NULL,
  product_no VARCHAR(64) NULL,
  model VARCHAR(64) NULL,
  device_type VARCHAR(32) NULL,
  rated_capacity VARCHAR(64) NULL,
  rated_pressure VARCHAR(64) NULL,
  rated_steam_temp VARCHAR(64) NULL,
  fuel_type VARCHAR(64) NULL,
  thermal_efficiency VARCHAR(64) NULL,
  manufacturer VARCHAR(128) NULL,
  manufacture_date VARCHAR(32) NULL,
  license_no VARCHAR(64) NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'normal',
  created_at DATETIME NOT NULL,
  KEY idx_boilers_enterprise (enterprise_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS material_packs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  enterprise_id BIGINT NOT NULL,
  code VARCHAR(64) NOT NULL UNIQUE,
  type VARCHAR(32) NOT NULL DEFAULT '基础版',
  status VARCHAR(20) NOT NULL DEFAULT 'unactivated',
  boiler_id BIGINT NULL,
  expire_at VARCHAR(32) NULL,
  created_at DATETIME NOT NULL,
  activated_at DATETIME NULL,
  KEY idx_packs_enterprise (enterprise_id),
  KEY idx_packs_boiler (boiler_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(64) NOT NULL,
  role VARCHAR(32) NOT NULL,
  enterprise_id BIGINT NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  KEY idx_users_enterprise (enterprise_id),
  KEY idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS water_test_items (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(64) NOT NULL UNIQUE,
  name VARCHAR(64) NOT NULL,
  priority INT NOT NULL,
  method VARCHAR(64) NULL,
  normal_range VARCHAR(64) NULL,
  meaning VARCHAR(255) NULL,
  maintenance VARCHAR(512) NULL,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL,
  KEY idx_water_items_priority (priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS inspections (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  enterprise_id BIGINT NOT NULL,
  boiler_id BIGINT NOT NULL,
  material_pack_id BIGINT NOT NULL,
  inspection_type VARCHAR(32) NOT NULL DEFAULT 'daily',
  image_url VARCHAR(512) NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'created',
  score INT NULL,
  summary VARCHAR(255) NULL,
  result_json JSON NULL,
  remark VARCHAR(255) NULL,
  created_at DATETIME NOT NULL,
  submitted_at DATETIME NULL,
  KEY idx_inspections_enterprise (enterprise_id),
  KEY idx_inspections_boiler (boiler_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS inspection_test_results (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  inspection_id BIGINT NOT NULL,
  item_code VARCHAR(64) NOT NULL,
  item_name VARCHAR(64) NOT NULL,
  priority INT NOT NULL,
  value_text VARCHAR(64) NULL,
  unit VARCHAR(32) NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'normal',
  normal_range VARCHAR(64) NULL,
  method VARCHAR(64) NULL,
  meaning VARCHAR(255) NULL,
  maintenance VARCHAR(512) NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uk_inspection_item (inspection_id, item_code),
  KEY idx_test_results_inspection (inspection_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO enterprises(id, name, code, created_at)
VALUES (1, '华能示范工厂', 'HN-DEMO', NOW());

INSERT IGNORE INTO boilers(
  id, enterprise_id, name, device_code, product_no, model, device_type,
  rated_capacity, rated_pressure, fuel_type, manufacturer, manufacture_date,
  license_no, created_at
) VALUES (
  1001, 1, '1号蒸汽锅炉', 'D-1001', 'P-1001', 'DZL6-1.25', '蒸汽锅炉',
  '6t/h', '1.25', '生物质颗粒', '青岛胜利锅炉有限公司', '2025-08-01',
  'TS2110709-2027', NOW()
);

INSERT IGNORE INTO material_packs(id, enterprise_id, code, type, status, boiler_id, expire_at, created_at, activated_at)
VALUES (9001, 1, 'PACK-001', '基础版', 'activated', 1001, '2027-12-31', NOW(), NOW());

INSERT INTO water_test_items(code, name, priority, method, normal_range, meaning, maintenance, enabled, created_at)
VALUES
  ('ph', 'pH', 1, 'pH试纸', '8.5-10.5', '判断锅水酸碱性，是腐蚀和加药控制的基础指标。', '偏低时易腐蚀，建议复测并适当补加碱性药剂；偏高时加强排污，避免碱腐蚀和汽水共腾。', 1, NOW()),
  ('phosphate', '磷酸根', 2, '磷酸根试纸', '10-30 mg/L', '判断防垢药剂余量，关系到钙镁离子能否形成可排出的泥渣。', '偏低说明防垢能力不足，建议补加磷酸盐药剂并观察排污泥渣；偏高则减少加药并加强排污。', 1, NOW()),
  ('sulfite', '亚硫酸根', 3, '亚硫酸根试纸', '10-30 mg/L', '判断除氧剂余量，用于控制残余溶解氧造成的氧腐蚀。', '偏低时检查除氧剂投加和除氧设备；偏高时减少投药，避免盐分增加和排污负担上升。', 1, NOW()),
  ('alkalinity', '总碱度', 4, '总碱度试纸', '6-26 mmol/L', '反映锅水碱性物质总量，影响防腐、防垢和蒸汽品质。', '偏低时保护性不足，偏高时易起泡和汽水共腾；根据结果调整加药量和排污频率。', 1, NOW()),
  ('chloride', '氯离子', 5, '氯离子试纸/滴定包', '≤300 mg/L', '用于判断浓缩程度和点蚀风险，氯离子过高会加剧局部腐蚀。', '偏高时优先加强排污，检查补水来源和软化/除盐设备，必要时缩短复测周期。', 1, NOW()),
  ('hardness', '硬度', 6, '硬度试纸', '≤0.03 mmol/L', '判断锅水中钙镁离子残留，直接反映结垢风险和软化处理效果。', '偏高时建议检查软水器、补水硬度和排污情况，必要时停炉检查受热面沉积。', 1, NOW())
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  priority = VALUES(priority),
  method = VALUES(method),
  normal_range = VALUES(normal_range),
  meaning = VALUES(meaning),
  maintenance = VALUES(maintenance),
  enabled = 1;

-- 后台用户由应用启动时自动写入，密码使用 PBKDF2-SHA256 加密保存。
