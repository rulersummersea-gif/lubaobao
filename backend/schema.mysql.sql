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

-- 后台用户由应用启动时自动写入，密码使用 PBKDF2-SHA256 加密保存。
