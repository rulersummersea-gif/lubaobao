-- 炉保保 后端数据库初始化 SQL（MySQL 8）
-- 重点：企业、锅炉、检测包三主体 + 巡检业务闭环

CREATE DATABASE IF NOT EXISTS lubaobao DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lubaobao;

-- 企业
CREATE TABLE IF NOT EXISTS enterprise (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  code VARCHAR(64) NULL,
  contact_name VARCHAR(64) NULL,
  contact_phone VARCHAR(32) NULL,
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_enterprise_code (code)
) ENGINE=InnoDB;

-- 锅炉（12关键字段）
CREATE TABLE IF NOT EXISTS boiler (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  enterprise_id BIGINT NOT NULL,
  device_code VARCHAR(64) NOT NULL COMMENT '1设备代码',
  product_no VARCHAR(64) NOT NULL COMMENT '2产品编号/出厂编号',
  model VARCHAR(64) NOT NULL COMMENT '3锅炉型号',
  device_type VARCHAR(32) NOT NULL COMMENT '4设备类型',
  rated_capacity VARCHAR(64) NOT NULL COMMENT '5额定蒸发量/热功率',
  rated_pressure DECIMAL(8,3) NOT NULL COMMENT '6额定工作压力MPa',
  rated_steam_temp DECIMAL(8,2) NULL COMMENT '7额定蒸汽温度℃',
  fuel_type VARCHAR(64) NOT NULL COMMENT '8设计燃料类型',
  thermal_efficiency DECIMAL(5,2) NULL COMMENT '9热效率%',
  manufacturer VARCHAR(128) NOT NULL COMMENT '10制造单位',
  manufacture_date DATE NOT NULL COMMENT '11制造日期',
  license_no VARCHAR(64) NOT NULL COMMENT '12制造许可证编号',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_boiler_enterprise FOREIGN KEY (enterprise_id) REFERENCES enterprise(id),
  UNIQUE KEY uk_boiler_device_code (device_code),
  UNIQUE KEY uk_boiler_product_no (product_no),
  KEY idx_boiler_enterprise (enterprise_id)
) ENGINE=InnoDB;

-- 检测包（材料包）
CREATE TABLE IF NOT EXISTS detect_pack (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  enterprise_id BIGINT NOT NULL,
  pack_code VARCHAR(64) NOT NULL,
  batch_no VARCHAR(64) NULL,
  pack_type VARCHAR(32) NOT NULL DEFAULT '基础版',
  total_count INT NOT NULL DEFAULT 1,
  remain_count INT NOT NULL DEFAULT 1,
  expire_at DATE NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'unactivated' COMMENT 'unactivated/activated/in_use/exhausted/expired/invalid',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_pack_enterprise FOREIGN KEY (enterprise_id) REFERENCES enterprise(id),
  UNIQUE KEY uk_pack_code (pack_code),
  KEY idx_pack_enterprise (enterprise_id)
) ENGINE=InnoDB;

-- 后台用户与角色
CREATE TABLE IF NOT EXISTS admin_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(64) NOT NULL,
  role VARCHAR(32) NOT NULL COMMENT 'platform_admin/enterprise_admin/inspector',
  enterprise_id BIGINT NOT NULL,
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_admin_user_enterprise FOREIGN KEY (enterprise_id) REFERENCES enterprise(id),
  UNIQUE KEY uk_admin_user_username (username),
  KEY idx_admin_user_enterprise (enterprise_id),
  KEY idx_admin_user_role (role)
) ENGINE=InnoDB;

-- 锅炉-检测包绑定关系
CREATE TABLE IF NOT EXISTS boiler_pack_binding (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  enterprise_id BIGINT NOT NULL,
  boiler_id BIGINT NOT NULL,
  pack_id BIGINT NOT NULL,
  bind_rule VARCHAR(20) NOT NULL DEFAULT 'shared' COMMENT 'shared专企业共用 / exclusive专包专炉',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1生效 0失效',
  bind_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  unbind_time DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_binding_enterprise FOREIGN KEY (enterprise_id) REFERENCES enterprise(id),
  CONSTRAINT fk_binding_boiler FOREIGN KEY (boiler_id) REFERENCES boiler(id),
  CONSTRAINT fk_binding_pack FOREIGN KEY (pack_id) REFERENCES detect_pack(id),
  KEY idx_binding_enterprise (enterprise_id),
  KEY idx_binding_boiler (boiler_id),
  KEY idx_binding_pack (pack_id)
) ENGINE=InnoDB;

-- 巡检任务
CREATE TABLE IF NOT EXISTS inspection (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  enterprise_id BIGINT NOT NULL,
  boiler_id BIGINT NOT NULL,
  pack_id BIGINT NOT NULL,
  inspector_id BIGINT NULL,
  image_url VARCHAR(512) NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'created' COMMENT 'created/uploaded/recognizing/done/submitted/failed',
  risk_level VARCHAR(20) NULL COMMENT 'normal/warning/danger',
  health_score INT NULL,
  recognize_raw JSON NULL,
  remark VARCHAR(255) NULL,
  inspected_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_inspection_enterprise FOREIGN KEY (enterprise_id) REFERENCES enterprise(id),
  CONSTRAINT fk_inspection_boiler FOREIGN KEY (boiler_id) REFERENCES boiler(id),
  CONSTRAINT fk_inspection_pack FOREIGN KEY (pack_id) REFERENCES detect_pack(id),
  KEY idx_inspection_boiler_time (boiler_id, created_at),
  KEY idx_inspection_enterprise_time (enterprise_id, created_at)
) ENGINE=InnoDB;

-- 锅水检测项目模板（当前第一版 6 项）
CREATE TABLE IF NOT EXISTS water_test_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_code VARCHAR(64) NOT NULL,
  item_name VARCHAR(64) NOT NULL,
  priority INT NOT NULL,
  method VARCHAR(64) NULL,
  normal_range VARCHAR(64) NULL,
  meaning VARCHAR(255) NULL,
  maintenance VARCHAR(512) NULL,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_water_test_item_code (item_code),
  KEY idx_water_test_item_priority (priority)
) ENGINE=InnoDB;

-- 检测项明细
CREATE TABLE IF NOT EXISTS inspection_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  inspection_id BIGINT NOT NULL,
  item_code VARCHAR(64) NULL,
  item_name VARCHAR(64) NOT NULL,
  priority INT NULL,
  value_text VARCHAR(64) NOT NULL,
  unit VARCHAR(32) NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'normal',
  normal_range VARCHAR(64) NULL,
  method VARCHAR(64) NULL,
  meaning VARCHAR(255) NULL,
  maintenance VARCHAR(512) NULL,
  abnormal_flag TINYINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_item_inspection FOREIGN KEY (inspection_id) REFERENCES inspection(id),
  KEY idx_item_inspection (inspection_id)
) ENGINE=InnoDB;

-- 月报快照（锅炉级）
CREATE TABLE IF NOT EXISTS boiler_monthly_report (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  enterprise_id BIGINT NOT NULL,
  boiler_id BIGINT NOT NULL,
  report_month CHAR(7) NOT NULL COMMENT 'YYYY-MM',
  inspection_count INT NOT NULL DEFAULT 0,
  abnormal_count INT NOT NULL DEFAULT 0,
  avg_health_score DECIMAL(5,2) NULL,
  suggestions JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_boiler_month (boiler_id, report_month),
  KEY idx_report_enterprise_month (enterprise_id, report_month)
) ENGINE=InnoDB;
