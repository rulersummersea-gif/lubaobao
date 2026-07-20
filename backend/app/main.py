import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel


DB_PATH = Path(os.getenv("LUBAOBAO_DB", "/tmp/lubaobao.sqlite3"))
UPLOAD_DIR = Path(os.getenv("LUBAOBAO_UPLOAD_DIR", "/tmp/lubaobao_uploads"))
DB_DRIVER = os.getenv("DB_DRIVER", "sqlite").lower()
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "lubaobao")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "lubaobao")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "lubaobao")
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-secret-change-me")
WX_APPID = os.getenv("WX_APPID", "")
WX_APPSECRET = os.getenv("WX_APPSECRET", "")
PASSWORD_ITERATIONS = 200000

app = FastAPI(title="Lubaobao API", version="0.5.0-complete-flow")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


class MySQLCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def __iter__(self):
        return iter(self.cursor.fetchall())


class MySQLConnection:
    def __init__(self, database: Optional[str] = None):
        import pymysql

        self.conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def execute(self, sql: str, params=()):
        cursor = self.conn.cursor()
        cursor.execute(sql.replace("?", "%s"), params)
        return MySQLCursor(cursor)

    def executescript(self, script: str):
        for statement in script.split(";"):
            statement = statement.strip()
            if statement:
                self.execute(statement)


def db():
    if DB_DRIVER == "mysql":
        return MySQLConnection(MYSQL_DATABASE)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return dict(row) if row else None


def is_integrity_error(exc: Exception) -> bool:
    return isinstance(exc, sqlite3.IntegrityError) or exc.__class__.__name__ == "IntegrityError"


WATER_TEST_ITEMS = [
    {
        "code": "ph",
        "name": "pH",
        "priority": 1,
        "method": "pH试纸",
        "normalRange": "8.5-10.5",
        "meaning": "判断锅水酸碱性，是腐蚀和加药控制的基础指标。",
        "maintenance": "偏低时易腐蚀，建议复测并适当补加碱性药剂；偏高时加强排污，避免碱腐蚀和汽水共腾。",
    },
    {
        "code": "phosphate",
        "name": "磷酸根",
        "priority": 2,
        "method": "磷酸根试纸",
        "normalRange": "10-30 mg/L",
        "meaning": "判断防垢药剂余量，关系到钙镁离子能否形成可排出的泥渣。",
        "maintenance": "偏低说明防垢能力不足，建议补加磷酸盐药剂并观察排污泥渣；偏高则减少加药并加强排污。",
    },
    {
        "code": "sulfite",
        "name": "亚硫酸根",
        "priority": 3,
        "method": "亚硫酸根试纸",
        "normalRange": "10-30 mg/L",
        "meaning": "判断除氧剂余量，用于控制残余溶解氧造成的氧腐蚀。",
        "maintenance": "偏低时检查除氧剂投加和除氧设备；偏高时减少投药，避免盐分增加和排污负担上升。",
    },
    {
        "code": "alkalinity",
        "name": "总碱度",
        "priority": 4,
        "method": "总碱度试纸",
        "normalRange": "6-26 mmol/L",
        "meaning": "反映锅水碱性物质总量，影响防腐、防垢和蒸汽品质。",
        "maintenance": "偏低时保护性不足，偏高时易起泡和汽水共腾；根据结果调整加药量和排污频率。",
    },
    {
        "code": "chloride",
        "name": "氯离子",
        "priority": 5,
        "method": "氯离子试纸",
        "normalRange": "≤300 mg/L",
        "meaning": "用于判断浓缩程度和点蚀风险，氯离子过高会加剧局部腐蚀。",
        "maintenance": "偏高时优先加强排污，检查补水来源和软化/除盐设备，必要时缩短复测周期。",
    },
    {
        "code": "hardness",
        "name": "硬度",
        "priority": 6,
        "method": "硬度试纸",
        "normalRange": "≤0.03 mmol/L",
        "meaning": "判断锅水中钙镁离子残留，直接反映结垢风险和软化处理效果。",
        "maintenance": "偏高时建议检查软水器、补水硬度和排污情况，必要时停炉检查受热面沉积。",
    },
]


PRESSURE_SEGMENTS = [
    {"minPressure": 0, "maxPressure": 1.0, "alkalinityMax": 26, "label": "P≤1.0MPa"},
    {"minPressure": 1.0, "maxPressure": 1.6, "alkalinityMax": 24, "label": "1.0<P≤1.6MPa"},
    {"minPressure": 1.6, "maxPressure": 2.5, "alkalinityMax": 16, "label": "1.6<P≤2.5MPa"},
    {"minPressure": 2.5, "maxPressure": 3.8, "alkalinityMax": 12, "label": "2.5<P<3.8MPa"},
]

BASE_WATER_QUALITY_LIMITS = [
    {"code": "ph", "min": 8.5, "max": 10.5, "unit": "", "range": "8.5-10.5"},
    {"code": "phosphate", "min": 10, "max": 30, "unit": "mg/L", "range": "10-30 mg/L"},
    {"code": "sulfite", "min": 10, "max": 30, "unit": "mg/L", "range": "10-30 mg/L"},
    {"code": "alkalinity", "min": 6, "max": None, "unit": "mmol/L", "range": ""},
    {"code": "chloride", "min": None, "max": 300, "unit": "mg/L", "range": "≤300 mg/L"},
    {"code": "hardness", "min": None, "max": 0.03, "unit": "mmol/L", "range": "≤0.03 mmol/L"},
]

WATER_QUALITY_LIMITS = []
for segment in PRESSURE_SEGMENTS:
    for limit in BASE_WATER_QUALITY_LIMITS:
        item = {**limit, "minPressure": segment["minPressure"], "maxPressure": segment["maxPressure"], "pressureLabel": segment["label"]}
        if item["code"] == "alkalinity":
            item["max"] = segment["alkalinityMax"]
            item["range"] = f"6-{segment['alkalinityMax']} mmol/L"
        WATER_QUALITY_LIMITS.append(item)

STANDARD_SOURCE = "GB/T 1576 工业锅炉水质"
STANDARD_NOTE = "工业蒸汽锅炉锅水/炉水，按压力段灰测配置；正式上线需按锅炉额定压力和现场水处理方式复核。"


def encode_token_part(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")


def decode_token_part(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def make_token(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    body = encode_token_part(raw)
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    return f"{body}.{encode_token_part(signature)}"


def parse_token(authorization: Optional[str]) -> dict:
    if not authorization:
        return {}
    token = authorization.replace("Bearer ", "").strip()
    try:
        if "." in token:
            body, signature = token.rsplit(".", 1)
            expected = hmac.new(AUTH_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
            actual = decode_token_part(signature)
            if not hmac.compare_digest(actual, expected):
                return {}
            return json.loads(decode_token_part(body))
        return json.loads(decode_token_part(token))
    except Exception:
        return {}


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
        return hmac.compare_digest(actual.hex(), digest)
    except Exception:
        return False


def get_current_user(authorization: Optional[str]) -> dict:
    user = parse_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return user


def require_roles(authorization: Optional[str], allowed_roles: tuple[str, ...]) -> dict:
    user = get_current_user(authorization)
    if user.get("role") not in allowed_roles:
        raise HTTPException(status_code=403, detail="无权限")
    return user


def ensure_enterprise_scope(user: dict, enterprise_id: int) -> None:
    if user.get("role") == "enterprise_admin" and user.get("enterpriseId") != enterprise_id:
        raise HTTPException(status_code=403, detail="无权管理其他企业数据")


def ensure_user_manage_scope(current_user: dict, role: str, enterprise_id: int) -> None:
    if role not in ("platform_admin", "enterprise_admin", "inspector"):
        raise HTTPException(status_code=400, detail="角色不合法")
    if current_user["role"] == "enterprise_admin":
        ensure_enterprise_scope(current_user, enterprise_id)
        if role == "platform_admin":
            raise HTTPException(status_code=403, detail="企业管理员不能创建或修改平台管理员")


def user_response(row) -> dict:
    user = row_to_dict(row)
    return {
        "id": user["id"],
        "username": user["username"],
        "name": user["name"],
        "role": user["role"],
        "enterpriseId": user["enterprise_id"],
        "status": user["status"],
    }


def seed_users(conn) -> None:
    users = [
        ("admin", "Admin@123", "平台管理员", "platform_admin", 1),
        ("entadmin", "Ent@123", "企业管理员", "enterprise_admin", 1),
        ("inspector", "Inspect@123", "巡检员", "inspector", 1),
        ("wx_user", "WxUser@Disabled", "微信用户", "inspector", 1),
        ("h5_user", "H5User@Disabled", "H5灰测用户", "inspector", 1),
    ]
    insert_sql = (
        """
        INSERT IGNORE INTO users(username, password_hash, name, role, enterprise_id, status, created_at)
        VALUES(?, ?, ?, ?, ?, 'active', ?)
        """
        if DB_DRIVER == "mysql"
        else """
        INSERT OR IGNORE INTO users(username, password_hash, name, role, enterprise_id, status, created_at)
        VALUES(?, ?, ?, ?, ?, 'active', ?)
        """
    )
    for username, password, name, role, enterprise_id in users:
        conn.execute(insert_sql, (username, password_hash(password), name, role, enterprise_id, now()))


def seed_water_test_items(conn) -> None:
    insert_sql = (
        """
        INSERT INTO water_test_items(code, name, priority, method, normal_range, meaning, maintenance, enabled, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, 1, ?)
        ON DUPLICATE KEY UPDATE
          name = VALUES(name),
          priority = VALUES(priority),
          method = VALUES(method),
          normal_range = VALUES(normal_range),
          meaning = VALUES(meaning),
          maintenance = VALUES(maintenance),
          enabled = 1
        """
        if DB_DRIVER == "mysql"
        else """
        INSERT INTO water_test_items(code, name, priority, method, normal_range, meaning, maintenance, enabled, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, 1, ?)
        ON CONFLICT(code) DO UPDATE SET
          name = excluded.name,
          priority = excluded.priority,
          method = excluded.method,
          normal_range = excluded.normal_range,
          meaning = excluded.meaning,
          maintenance = excluded.maintenance,
          enabled = 1
        """
    )
    for item in WATER_TEST_ITEMS:
        conn.execute(
            insert_sql,
            (
                item["code"],
                item["name"],
                item["priority"],
                item["method"],
                item["normalRange"],
                item["meaning"],
                item["maintenance"],
                now(),
            ),
        )


def seed_water_quality_limits(conn) -> None:
    insert_sql = (
        """
        INSERT INTO water_quality_limits(
          item_code, boiler_type, sample_type, pressure_min_mpa, pressure_max_mpa,
          min_value, max_value, unit, display_range, standard_source, standard_note, enabled, created_at
        ) VALUES(?, 'steam', 'boiler_water', ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ON DUPLICATE KEY UPDATE
          min_value = VALUES(min_value),
          max_value = VALUES(max_value),
          unit = VALUES(unit),
          display_range = VALUES(display_range),
          standard_source = VALUES(standard_source),
          standard_note = VALUES(standard_note),
          enabled = 1
        """
        if DB_DRIVER == "mysql"
        else """
        INSERT INTO water_quality_limits(
          item_code, boiler_type, sample_type, pressure_min_mpa, pressure_max_mpa,
          min_value, max_value, unit, display_range, standard_source, standard_note, enabled, created_at
        ) VALUES(?, 'steam', 'boiler_water', ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ON CONFLICT(item_code, boiler_type, sample_type, pressure_min_mpa, pressure_max_mpa) DO UPDATE SET
          min_value = excluded.min_value,
          max_value = excluded.max_value,
          unit = excluded.unit,
          display_range = excluded.display_range,
          standard_source = excluded.standard_source,
          standard_note = excluded.standard_note,
          enabled = 1
        """
    )
    for limit in WATER_QUALITY_LIMITS:
        conn.execute(
            insert_sql,
            (
                limit["code"],
                limit["minPressure"],
                limit["maxPressure"],
                limit["min"],
                limit["max"],
                limit["unit"],
                limit["range"],
                STANDARD_SOURCE,
                STANDARD_NOTE,
                now(),
            ),
        )


def retire_legacy_broad_limits(conn) -> None:
    legacy_ranges = {
        "ph": "8.5-10.5",
        "phosphate": "10-30 mg/L",
        "sulfite": "10-30 mg/L",
        "alkalinity": "6-26 mmol/L",
        "chloride": "≤300 mg/L",
        "hardness": "≤0.03 mmol/L",
    }
    for code, display_range in legacy_ranges.items():
        conn.execute(
            """
            UPDATE water_quality_limits
            SET enabled = 0
            WHERE item_code = ?
              AND boiler_type = 'steam'
              AND sample_type = 'boiler_water'
              AND pressure_min_mpa = 0
              AND pressure_max_mpa = 3.8
              AND display_range = ?
            """,
            (code, display_range),
        )


def ensure_column(conn, table: str, column: str, definition: str) -> None:
    try:
        if DB_DRIVER == "mysql":
            rows = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM information_schema.columns
                WHERE table_schema = ? AND table_name = ? AND column_name = ?
                """,
                (MYSQL_DATABASE, table, column),
            ).fetchone()
            exists = rows["c"] > 0
        else:
            exists = any(row["name"] == column for row in conn.execute(f"PRAGMA table_info({table})"))
        if not exists:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except Exception:
        pass


def ensure_onboarding_schema(conn) -> None:
    if DB_DRIVER == "mysql":
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_material_pack_bindings (
              id BIGINT PRIMARY KEY AUTO_INCREMENT,
              user_id BIGINT NOT NULL,
              enterprise_id BIGINT NOT NULL,
              boiler_id BIGINT NOT NULL,
              material_pack_id BIGINT NOT NULL,
              status VARCHAR(20) NOT NULL DEFAULT 'active',
              expire_at VARCHAR(32) NULL,
              bound_at DATETIME NOT NULL,
              unbound_at DATETIME NULL,
              created_at DATETIME NOT NULL,
              KEY idx_user_pack_bindings_user (user_id, status),
              KEY idx_user_pack_bindings_pack (material_pack_id),
              KEY idx_user_pack_bindings_boiler (boiler_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_material_pack_bindings (
              id INTEGER PRIMARY KEY,
              user_id INTEGER NOT NULL,
              enterprise_id INTEGER NOT NULL,
              boiler_id INTEGER NOT NULL,
              material_pack_id INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'active',
              expire_at TEXT,
              bound_at TEXT NOT NULL,
              unbound_at TEXT,
              created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_pack_bindings_user ON user_material_pack_bindings(user_id, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_pack_bindings_pack ON user_material_pack_bindings(material_pack_id)")


def ensure_schema_updates(conn) -> None:
    ensure_column(conn, "water_quality_limits", "updated_at", "DATETIME NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_column(conn, "water_quality_limits", "updated_by", "BIGINT NULL" if DB_DRIVER == "mysql" else "INTEGER")
    ensure_column(conn, "water_quality_limits", "updated_by_name", "VARCHAR(64) NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_column(conn, "retest_tasks", "support_notice", "VARCHAR(512) NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_column(conn, "retest_tasks", "service_advice", "VARCHAR(512) NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_column(conn, "retest_tasks", "service_by", "BIGINT NULL" if DB_DRIVER == "mysql" else "INTEGER")
    ensure_column(conn, "retest_tasks", "service_by_name", "VARCHAR(64) NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_column(conn, "retest_tasks", "service_at", "DATETIME NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_column(conn, "retest_tasks", "retest_inspection_id", "BIGINT NULL" if DB_DRIVER == "mysql" else "INTEGER")
    ensure_column(conn, "retest_tasks", "resolution_type", "VARCHAR(32) NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_column(conn, "retest_tasks", "resolution_note", "VARCHAR(512) NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_column(conn, "retest_tasks", "resolved_at", "DATETIME NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_column(conn, "inspections", "retest_task_id", "BIGINT NULL" if DB_DRIVER == "mysql" else "INTEGER")
    ensure_column(conn, "users", "wx_openid", "VARCHAR(128) NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_column(conn, "inspections", "inspector_user_id", "BIGINT NULL" if DB_DRIVER == "mysql" else "INTEGER")
    ensure_column(conn, "inspections", "inspector_name", "VARCHAR(64) NULL" if DB_DRIVER == "mysql" else "TEXT")
    ensure_onboarding_schema(conn)


def seed_data(conn) -> None:
    conn.execute(
        "INSERT IGNORE INTO enterprises(id, name, code, created_at) VALUES(1, '华能示范工厂', 'HN-DEMO', ?)"
        if DB_DRIVER == "mysql"
        else "INSERT OR IGNORE INTO enterprises(id, name, code, created_at) VALUES(1, '华能示范工厂', 'HN-DEMO', ?)",
        (now(),),
    )
    seed_users(conn)
    seed_water_test_items(conn)
    ensure_schema_updates(conn)
    seed_water_quality_limits(conn)
    retire_legacy_broad_limits(conn)
    conn.execute(
        """
        INSERT IGNORE INTO boilers(
          id, enterprise_id, name, device_code, product_no, model, device_type,
          rated_capacity, rated_pressure, fuel_type, manufacturer, manufacture_date,
          license_no, created_at
        ) VALUES(1001, 1, '1号蒸汽锅炉', 'D-1001', 'P-1001', 'DZL6-1.25', '蒸汽锅炉',
          '6t/h', '1.25', '生物质颗粒', '青岛胜利锅炉有限公司', '2025-08-01',
          'TS2110709-2027', ?)
        """
        if DB_DRIVER == "mysql"
        else """
        INSERT OR IGNORE INTO boilers(
          id, enterprise_id, name, device_code, product_no, model, device_type,
          rated_capacity, rated_pressure, fuel_type, manufacturer, manufacture_date,
          license_no, created_at
        ) VALUES(1001, 1, '1号蒸汽锅炉', 'D-1001', 'P-1001', 'DZL6-1.25', '蒸汽锅炉',
          '6t/h', '1.25', '生物质颗粒', '青岛胜利锅炉有限公司', '2025-08-01',
          'TS2110709-2027', ?)
        """,
        (now(),),
    )
    conn.execute(
        """
        INSERT IGNORE INTO material_packs(id, enterprise_id, code, type, status, boiler_id, expire_at, created_at, activated_at)
        VALUES(9001, 1, 'PACK-001', '基础版', 'activated', 1001, '2027-12-31', ?, ?)
        """
        if DB_DRIVER == "mysql"
        else """
        INSERT OR IGNORE INTO material_packs(id, enterprise_id, code, type, status, boiler_id, expire_at, created_at, activated_at)
        VALUES(9001, 1, 'PACK-001', '基础版', 'activated', 1001, '2027-12-31', ?, ?)
        """,
        (now(), now()),
    )


def init_sqlite() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS enterprises (
              id INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              code TEXT,
              status TEXT NOT NULL DEFAULT 'active',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS boilers (
              id INTEGER PRIMARY KEY,
              enterprise_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              device_code TEXT,
              product_no TEXT,
              model TEXT,
              device_type TEXT,
              rated_capacity TEXT,
              rated_pressure TEXT,
              rated_steam_temp TEXT,
              fuel_type TEXT,
              thermal_efficiency TEXT,
              manufacturer TEXT,
              manufacture_date TEXT,
              license_no TEXT,
              status TEXT NOT NULL DEFAULT 'normal',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS material_packs (
              id INTEGER PRIMARY KEY,
              enterprise_id INTEGER NOT NULL,
              code TEXT NOT NULL UNIQUE,
              type TEXT NOT NULL DEFAULT '基础版',
              status TEXT NOT NULL DEFAULT 'unactivated',
              boiler_id INTEGER,
              expire_at TEXT,
              created_at TEXT NOT NULL,
              activated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY,
              username TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              name TEXT NOT NULL,
              role TEXT NOT NULL,
              enterprise_id INTEGER NOT NULL DEFAULT 1,
              status TEXT NOT NULL DEFAULT 'active',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS water_test_items (
              id INTEGER PRIMARY KEY,
              code TEXT NOT NULL UNIQUE,
              name TEXT NOT NULL,
              priority INTEGER NOT NULL,
              method TEXT,
              normal_range TEXT,
              meaning TEXT,
              maintenance TEXT,
              enabled INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS water_quality_limits (
              id INTEGER PRIMARY KEY,
              item_code TEXT NOT NULL,
              boiler_type TEXT NOT NULL DEFAULT 'steam',
              sample_type TEXT NOT NULL DEFAULT 'boiler_water',
              pressure_min_mpa REAL,
              pressure_max_mpa REAL,
              min_value REAL,
              max_value REAL,
              unit TEXT,
              display_range TEXT,
              standard_source TEXT,
              standard_note TEXT,
              enabled INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT,
              updated_by INTEGER,
              updated_by_name TEXT,
              UNIQUE(item_code, boiler_type, sample_type, pressure_min_mpa, pressure_max_mpa)
            );
            CREATE TABLE IF NOT EXISTS inspections (
              id INTEGER PRIMARY KEY,
              enterprise_id INTEGER NOT NULL,
              boiler_id INTEGER NOT NULL,
              material_pack_id INTEGER NOT NULL,
              inspection_type TEXT NOT NULL DEFAULT 'daily',
              retest_task_id INTEGER,
              image_url TEXT,
              status TEXT NOT NULL DEFAULT 'created',
              score INTEGER,
              summary TEXT,
              result_json TEXT,
              remark TEXT,
              created_at TEXT NOT NULL,
              submitted_at TEXT
            );
            CREATE TABLE IF NOT EXISTS inspection_test_results (
              id INTEGER PRIMARY KEY,
              inspection_id INTEGER NOT NULL,
              item_code TEXT NOT NULL,
              item_name TEXT NOT NULL,
              priority INTEGER NOT NULL,
              value_text TEXT,
              unit TEXT,
              status TEXT NOT NULL DEFAULT 'normal',
              normal_range TEXT,
              method TEXT,
              meaning TEXT,
              maintenance TEXT,
              created_at TEXT NOT NULL,
              UNIQUE(inspection_id, item_code)
            );
            CREATE TABLE IF NOT EXISTS retest_tasks (
              id INTEGER PRIMARY KEY,
              enterprise_id INTEGER NOT NULL,
              inspection_id INTEGER NOT NULL,
              boiler_id INTEGER,
              boiler_name TEXT,
              risk_code TEXT NOT NULL,
              risk_type TEXT,
              level TEXT NOT NULL DEFAULT 'warning',
              title TEXT NOT NULL,
              description TEXT,
              field_action TEXT,
              retest_plan TEXT,
              support_notice TEXT,
              service_advice TEXT,
              service_by INTEGER,
              service_by_name TEXT,
              service_at TEXT,
              retest_inspection_id INTEGER,
              resolution_type TEXT,
              resolution_note TEXT,
              resolved_at TEXT,
              related_item_names TEXT,
              action_text TEXT,
              status TEXT NOT NULL DEFAULT 'pending',
              created_at TEXT NOT NULL,
              completed_at TEXT,
              UNIQUE(inspection_id, risk_code)
            );
            """
        )
        seed_data(conn)


def init_mysql() -> None:
    with MySQLConnection(None) as conn:
        conn.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    with db() as conn:
        conn.executescript(
            """
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
            CREATE TABLE IF NOT EXISTS water_quality_limits (
              id BIGINT PRIMARY KEY AUTO_INCREMENT,
              item_code VARCHAR(64) NOT NULL,
              boiler_type VARCHAR(32) NOT NULL DEFAULT 'steam',
              sample_type VARCHAR(32) NOT NULL DEFAULT 'boiler_water',
              pressure_min_mpa DECIMAL(8,3) NULL,
              pressure_max_mpa DECIMAL(8,3) NULL,
              min_value DECIMAL(12,4) NULL,
              max_value DECIMAL(12,4) NULL,
              unit VARCHAR(32) NULL,
              display_range VARCHAR(64) NULL,
              standard_source VARCHAR(128) NULL,
              standard_note VARCHAR(512) NULL,
              enabled TINYINT NOT NULL DEFAULT 1,
              created_at DATETIME NOT NULL,
              updated_at DATETIME NULL,
              updated_by BIGINT NULL,
              updated_by_name VARCHAR(64) NULL,
              UNIQUE KEY uk_water_limit_scope (item_code, boiler_type, sample_type, pressure_min_mpa, pressure_max_mpa),
              KEY idx_water_limits_item (item_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            CREATE TABLE IF NOT EXISTS inspections (
              id BIGINT PRIMARY KEY AUTO_INCREMENT,
              enterprise_id BIGINT NOT NULL,
              boiler_id BIGINT NOT NULL,
              material_pack_id BIGINT NOT NULL,
              inspection_type VARCHAR(32) NOT NULL DEFAULT 'daily',
              retest_task_id BIGINT NULL,
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
            CREATE TABLE IF NOT EXISTS retest_tasks (
              id BIGINT PRIMARY KEY AUTO_INCREMENT,
              enterprise_id BIGINT NOT NULL,
              inspection_id BIGINT NOT NULL,
              boiler_id BIGINT NULL,
              boiler_name VARCHAR(128) NULL,
              risk_code VARCHAR(64) NOT NULL,
              risk_type VARCHAR(64) NULL,
              level VARCHAR(20) NOT NULL DEFAULT 'warning',
              title VARCHAR(128) NOT NULL,
              description VARCHAR(512) NULL,
              field_action VARCHAR(512) NULL,
              retest_plan VARCHAR(512) NULL,
              support_notice VARCHAR(512) NULL,
              service_advice VARCHAR(512) NULL,
              service_by BIGINT NULL,
              service_by_name VARCHAR(64) NULL,
              service_at DATETIME NULL,
              retest_inspection_id BIGINT NULL,
              resolution_type VARCHAR(32) NULL,
              resolution_note VARCHAR(512) NULL,
              resolved_at DATETIME NULL,
              related_item_names VARCHAR(255) NULL,
              action_text TEXT NULL,
              status VARCHAR(20) NOT NULL DEFAULT 'pending',
              created_at DATETIME NOT NULL,
              completed_at DATETIME NULL,
              UNIQUE KEY uk_retest_inspection_risk (inspection_id, risk_code),
              KEY idx_retest_enterprise_status (enterprise_id, status),
              KEY idx_retest_inspection (inspection_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        seed_data(conn)


def init_db() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if DB_DRIVER == "mysql":
        init_mysql()
    else:
        init_sqlite()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


class WxLoginReq(BaseModel):
    code: str


class OnboardingBoilerReq(BaseModel):
    deviceCode: str
    productNo: str
    model: str
    deviceType: str = "蒸汽锅炉"
    ratedCapacity: Optional[str] = ""
    ratedPressure: Optional[str] = ""
    fuelType: Optional[str] = ""
    manufacturer: Optional[str] = ""


class OnboardingCompleteReq(BaseModel):
    packCode: str
    userName: str
    enterpriseName: Optional[str] = ""
    boiler: Optional[OnboardingBoilerReq] = None


class AdminLoginReq(BaseModel):
    username: str
    password: str


class UserCreateReq(BaseModel):
    username: str
    password: str
    name: str
    role: str = "inspector"
    enterpriseId: int = 1


class UserUpdateReq(BaseModel):
    password: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    enterpriseId: Optional[int] = None
    status: Optional[str] = None


class UserStatusReq(BaseModel):
    status: str


class EnterpriseCreateReq(BaseModel):
    name: str
    code: Optional[str] = None


class EnterpriseUpdateReq(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    status: Optional[str] = None


class EnterpriseStatusReq(BaseModel):
    status: str


class BoilerCreateReq(BaseModel):
    enterpriseId: int = 1
    deviceCode: str
    productNo: str
    model: str
    deviceType: str
    ratedCapacity: Optional[str] = ""
    ratedPressure: Optional[str] = ""
    ratedSteamTemp: Optional[str] = ""
    fuelType: Optional[str] = ""
    thermalEfficiency: Optional[str] = ""
    manufacturer: Optional[str] = ""
    manufactureDate: Optional[str] = ""
    licenseNo: Optional[str] = ""


class BoilerUpdateReq(BaseModel):
    enterpriseId: Optional[int] = None
    deviceCode: Optional[str] = None
    productNo: Optional[str] = None
    model: Optional[str] = None
    deviceType: Optional[str] = None
    ratedCapacity: Optional[str] = None
    ratedPressure: Optional[str] = None
    ratedSteamTemp: Optional[str] = None
    fuelType: Optional[str] = None
    thermalEfficiency: Optional[str] = None
    manufacturer: Optional[str] = None
    manufactureDate: Optional[str] = None
    licenseNo: Optional[str] = None
    status: Optional[str] = None


class PackCreateReq(BaseModel):
    code: str
    enterpriseId: int = 1
    type: str = "基础版"
    expireAt: Optional[str] = None


class PackVerifyReq(BaseModel):
    code: str


class PackActivateReq(BaseModel):
    code: str
    boilerId: Optional[int] = None
    enterpriseId: Optional[int] = 1


class PackCodeReq(BaseModel):
    code: str


class WaterQualityLimitUpdateReq(BaseModel):
    pressureMinMpa: Optional[float] = None
    pressureMaxMpa: Optional[float] = None
    minValue: Optional[float] = None
    maxValue: Optional[float] = None
    unit: Optional[str] = None
    displayRange: Optional[str] = None
    standardSource: Optional[str] = None
    standardNote: Optional[str] = None
    enabled: Optional[bool] = None


class InspectionCreateReq(BaseModel):
    boilerId: int
    materialPackId: int
    inspectionType: str = "daily"
    retestTaskId: Optional[int] = None


class RecognizeReq(BaseModel):
    inspectionId: int
    values: Optional[dict] = None


class SubmitReq(BaseModel):
    inspectionId: int
    remark: Optional[str] = ""


class CompleteRetestTaskReq(BaseModel):
    remark: Optional[str] = ""


class RetestServiceAdviceReq(BaseModel):
    serviceAdvice: str


class RetestResolutionReq(BaseModel):
    resolutionType: str
    note: Optional[str] = ""
    retestInspectionId: Optional[int] = None


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "lubaobao-api",
        "version": app.version,
        "rbac": True,
        "features": ["pack-management", "image-upload", "inspection-submit", "record-detail", "retest-tasks"],
    }


@app.get("/health")
def health():
    return {"ok": True, "service": "lubaobao-api"}


@app.get("/dashboard")
def dashboard(enterpriseId: int = 1):
    with db() as conn:
        boiler_count = conn.execute("SELECT COUNT(*) AS c FROM boilers WHERE enterprise_id = ?", (enterpriseId,)).fetchone()["c"]
        pack_count = conn.execute("SELECT COUNT(*) AS c FROM material_packs WHERE enterprise_id = ?", (enterpriseId,)).fetchone()["c"]
        inspection_count = conn.execute("SELECT COUNT(*) AS c FROM inspections WHERE enterprise_id = ?", (enterpriseId,)).fetchone()["c"]
        retest_rows = conn.execute(
            """
            SELECT title, retest_plan AS retestPlan, related_item_names AS relatedItemNames, level
            FROM retest_tasks
            WHERE enterprise_id = ? AND status = 'pending'
            ORDER BY id DESC LIMIT 3
            """,
            (enterpriseId,),
        ).fetchall()
        latest = row_to_dict(
            conn.execute(
                """
                SELECT score, summary, result_json AS resultJson, created_at AS createdAt
                FROM inspections
                WHERE enterprise_id = ? AND result_json IS NOT NULL
                ORDER BY id DESC LIMIT 1
                """,
                (enterpriseId,),
            ).fetchone()
        )
    alerts = [
        {
            "title": row["title"],
            "desc": row["retestPlan"] or "建议复测确认",
            "relatedItemNames": row["relatedItemNames"],
            "level": row["level"] or "warning",
        }
        for row in retest_rows
    ]
    if latest and latest.get("resultJson"):
        result = json.loads(latest["resultJson"])
        for item in result.get("items", []):
            if len(alerts) >= 3:
                break
            if item.get("status") == "warning":
                alerts.append(
                    {
                        "title": f"{item.get('name')}预警",
                        "desc": item.get("maintenance") or item.get("normalRange") or "建议复测确认",
                    }
                )
    if not alerts:
        alerts = [{"title": "锅水6项待复测", "desc": "建议按pH、磷酸根、亚硫酸根、总碱度、氯离子、硬度顺序完成检测。"}]
    return {
        "stats": [
            {"label": "锅炉数量", "value": boiler_count},
            {"label": "材料包", "value": pack_count},
            {"label": "巡检记录", "value": inspection_count},
            {"label": "健康评分", "value": latest["score"] if latest else 74},
        ],
        "alerts": alerts[:3],
        "latest": latest or {},
    }


def diagnosis_action_text(item: dict) -> str:
    return "\n".join(
        text
        for text in [
            item.get("title"),
            f"关联指标：{item.get('relatedItemNames')}" if item.get("relatedItemNames") else "",
            f"现场处置：{item.get('fieldAction')}" if item.get("fieldAction") else "",
            f"复测要求：{item.get('retestPlan')}" if item.get("retestPlan") else "",
        ]
        if text
    )


def create_retest_tasks_from_result(conn, result: dict) -> None:
    inspection_id = result.get("inspectionId")
    if not inspection_id:
        return
    inspection = row_to_dict(
        conn.execute(
            """
            SELECT i.enterprise_id AS enterpriseId, i.boiler_id AS boilerId, b.name AS boilerName
            FROM inspections i
            LEFT JOIN boilers b ON b.id = i.boiler_id
            WHERE i.id = ?
            """,
            (inspection_id,),
        ).fetchone()
    )
    if not inspection:
        return
    insert_sql = (
        """
        INSERT INTO retest_tasks(
          enterprise_id, inspection_id, boiler_id, boiler_name, risk_code, risk_type,
          level, title, description, field_action, retest_plan, support_notice,
          related_item_names, action_text, status, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        ON DUPLICATE KEY UPDATE
          risk_type = VALUES(risk_type),
          level = VALUES(level),
          title = VALUES(title),
          description = VALUES(description),
          field_action = VALUES(field_action),
          retest_plan = VALUES(retest_plan),
          support_notice = VALUES(support_notice),
          related_item_names = VALUES(related_item_names),
          action_text = VALUES(action_text),
          status = IF(status = 'done', status, 'pending')
        """
        if DB_DRIVER == "mysql"
        else """
        INSERT INTO retest_tasks(
          enterprise_id, inspection_id, boiler_id, boiler_name, risk_code, risk_type,
          level, title, description, field_action, retest_plan, support_notice,
          related_item_names, action_text, status, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        ON CONFLICT(inspection_id, risk_code) DO UPDATE SET
          risk_type = excluded.risk_type,
          level = excluded.level,
          title = excluded.title,
          description = excluded.description,
          field_action = excluded.field_action,
          retest_plan = excluded.retest_plan,
          support_notice = excluded.support_notice,
          related_item_names = excluded.related_item_names,
          action_text = excluded.action_text,
          status = CASE WHEN retest_tasks.status = 'done' THEN retest_tasks.status ELSE 'pending' END
        """
    )
    for index, item in enumerate(result.get("diagnosis", [])):
        if not item.get("retestPlan") or item.get("riskCode") == "normal":
            continue
        conn.execute(
            insert_sql,
            (
                inspection["enterpriseId"],
                inspection_id,
                inspection.get("boilerId") or result.get("boilerId"),
                inspection.get("boilerName") or result.get("boilerName"),
                item.get("riskCode") or f"risk_{index}",
                item.get("riskType") or "",
                item.get("level") or "warning",
                item.get("title") or "复测提醒",
                item.get("reason") or "",
                item.get("fieldAction") or item.get("advice") or "",
                item.get("retestPlan") or "",
                item.get("supportNotice") or "",
                item.get("relatedItemNames") or "",
                diagnosis_action_text(item),
                now(),
            ),
        )


def backfill_retest_result(conn, inspection_id: int) -> None:
    inspection = row_to_dict(conn.execute("SELECT retest_task_id FROM inspections WHERE id = ?", (inspection_id,)).fetchone())
    if not inspection or not inspection.get("retest_task_id"):
        return
    conn.execute(
        """
        UPDATE retest_tasks
        SET retest_inspection_id = ?, status = 'retested', resolution_type = 'retest',
            resolution_note = '已提交复测结果', resolved_at = ?
        WHERE id = ?
        """,
        (inspection_id, now(), inspection["retest_task_id"]),
    )


def retest_task_to_dict(row) -> dict:
    item = row_to_dict(row)
    return {
        "id": item["id"],
        "enterpriseId": item["enterprise_id"],
        "inspectionId": item["inspection_id"],
        "boilerId": item["boiler_id"],
        "boilerName": item["boiler_name"],
        "riskCode": item["risk_code"],
        "riskType": item["risk_type"],
        "level": item["level"],
        "title": item["title"],
        "desc": item["retest_plan"] or item["description"],
        "description": item["description"],
        "action": item["field_action"],
        "fieldAction": item["field_action"],
        "retestPlan": item["retest_plan"],
        "supportNotice": item.get("support_notice") or "",
        "serviceAdvice": item.get("service_advice") or "",
        "serviceBy": item.get("service_by"),
        "serviceByName": item.get("service_by_name") or "",
        "serviceAt": item.get("service_at"),
        "retestInspectionId": item.get("retest_inspection_id"),
        "resolutionType": item.get("resolution_type") or "",
        "resolutionNote": item.get("resolution_note") or "",
        "resolvedAt": item.get("resolved_at"),
        "relatedItemNames": item["related_item_names"],
        "actionText": item["action_text"],
        "status": item["status"],
        "createdAt": item["created_at"],
        "completedAt": item["completed_at"],
    }


def pack_is_expired(expire_at) -> bool:
    if not expire_at:
        return False
    try:
        return datetime.strptime(str(expire_at)[:10], "%Y-%m-%d").date() < datetime.utcnow().date()
    except ValueError:
        return False


def onboarding_status(conn, user_id: int) -> dict:
    binding = row_to_dict(
        conn.execute(
            """
            SELECT ub.id, ub.status AS binding_status, ub.enterprise_id, ub.boiler_id,
                   ub.material_pack_id, ub.bound_at, ub.expire_at AS binding_expire_at,
                   p.code AS pack_code, p.status AS pack_status, p.expire_at AS pack_expire_at,
                   b.name AS boiler_name, e.name AS enterprise_name
            FROM user_material_pack_bindings ub
            LEFT JOIN material_packs p ON p.id = ub.material_pack_id
            LEFT JOIN boilers b ON b.id = ub.boiler_id
            LEFT JOIN enterprises e ON e.id = ub.enterprise_id
            WHERE ub.user_id = ?
            ORDER BY ub.id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    )
    if not binding:
        return {
            "required": True,
            "canEnterHome": False,
            "canInspect": False,
            "replacementRequired": True,
            "reason": "first_login",
            "message": "首次登录，请扫描材料包并完成企业和锅炉绑定",
        }

    expired = pack_is_expired(binding.get("pack_expire_at") or binding.get("binding_expire_at"))
    invalid_status = binding.get("pack_status") in ("expired", "invalid", "exhausted")
    inactive = binding.get("binding_status") != "active"
    required = inactive
    can_inspect = not expired and not invalid_status and not inactive
    reason = "pack_expired" if expired or binding.get("pack_status") == "expired" else "pack_invalid" if invalid_status else "binding_inactive" if inactive else "active"
    return {
        "required": required,
        "canEnterHome": not required,
        "canInspect": can_inspect,
        "replacementRequired": not can_inspect,
        "reason": reason,
        "message": "材料包已过期，请更换材料包后再巡检" if reason == "pack_expired" else "材料包不可用，请更换材料包后再巡检" if invalid_status else "材料包绑定已解除，请重新扫描材料包" if inactive else "绑定有效",
        "binding": {
            "id": binding["id"],
            "enterpriseId": binding["enterprise_id"],
            "enterpriseName": binding.get("enterprise_name") or "",
            "boilerId": binding["boiler_id"],
            "boilerName": binding.get("boiler_name") or "",
            "materialPackId": binding["material_pack_id"],
            "packCode": binding.get("pack_code") or "",
            "expireAt": binding.get("pack_expire_at") or binding.get("binding_expire_at"),
            "status": binding.get("pack_status") or binding.get("binding_status"),
        },
    }


def resolve_wx_openid(code: str) -> Optional[str]:
    if not WX_APPID or not WX_APPSECRET:
        return None
    query = urllib.parse.urlencode(
        {
            "appid": WX_APPID,
            "secret": WX_APPSECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    try:
        with urllib.request.urlopen(f"https://api.weixin.qq.com/sns/jscode2session?{query}", timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="微信登录服务暂时不可用") from exc
    if payload.get("errcode") or not payload.get("openid"):
        raise HTTPException(status_code=401, detail=payload.get("errmsg") or "微信登录凭证无效")
    return payload["openid"]


def get_wx_user(conn, code: str):
    openid = resolve_wx_openid(code)
    if openid:
        row = conn.execute(
            "SELECT id, username, name, role, enterprise_id, status FROM users WHERE wx_openid = ?",
            (openid,),
        ).fetchone()
        if row:
            return row
        username = f"wx_{hashlib.sha256(openid.encode('utf-8')).hexdigest()[:20]}"
        cur = conn.execute(
            """
            INSERT INTO users(username, password_hash, name, role, enterprise_id, status, wx_openid, created_at)
            VALUES(?, ?, '微信用户', 'inspector', 1, 'active', ?, ?)
            """,
            (username, password_hash(secrets.token_urlsafe(24)), openid, now()),
        )
        return conn.execute(
            "SELECT id, username, name, role, enterprise_id, status FROM users WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()

    fallback_username = "h5_user" if code == "h5-pilot" else "wx_user"
    row = conn.execute(
        "SELECT id, username, name, role, enterprise_id, status FROM users WHERE username = ?",
        (fallback_username,),
    ).fetchone()
    if not row:
        seed_users(conn)
        row = conn.execute(
            "SELECT id, username, name, role, enterprise_id, status FROM users WHERE username = ?",
            (fallback_username,),
        ).fetchone()
    return row


@app.post("/auth/wx-login")
def wx_login(req: WxLoginReq):
    with db() as conn:
        user_row = get_wx_user(conn, req.code)
        user = user_response(user_row)
        enterprise_row = conn.execute(
            "SELECT id, name, code, status FROM enterprises WHERE id = ?",
            (user["enterpriseId"],),
        ).fetchone()
        status = onboarding_status(conn, user["id"])
        enterprise = enterprise_response(enterprise_row) if enterprise_row else None
    current_boiler = None
    if status.get("binding"):
        current_boiler = {
            "id": status["binding"]["boilerId"],
            "name": status["binding"]["boilerName"],
            "enterpriseId": status["binding"]["enterpriseId"],
        }
    return {"token": make_token(user), "user": user, "enterprise": enterprise, "currentBoiler": current_boiler, "onboarding": status}


@app.get("/auth/onboarding-status")
def get_onboarding_status(authorization: Optional[str] = Header(None)):
    current_user = get_current_user(authorization)
    with db() as conn:
        return onboarding_status(conn, current_user["id"])


@app.post("/auth/complete-onboarding")
def complete_onboarding(req: OnboardingCompleteReq, authorization: Optional[str] = Header(None)):
    current_user = get_current_user(authorization)
    pack_code = req.packCode.strip()
    user_name = req.userName.strip()
    if not pack_code or not user_name:
        raise HTTPException(status_code=400, detail="材料包编码和用户姓名不能为空")

    with db() as conn:
        pack = row_to_dict(conn.execute("SELECT * FROM material_packs WHERE code = ?", (pack_code,)).fetchone())
        if not pack:
            raise HTTPException(status_code=404, detail="材料包不存在")
        if pack["status"] in ("expired", "invalid", "exhausted") or pack_is_expired(pack.get("expire_at")):
            if pack_is_expired(pack.get("expire_at")):
                conn.execute("UPDATE material_packs SET status = 'expired' WHERE id = ?", (pack["id"],))
            raise HTTPException(status_code=400, detail="材料包已过期或不可用")

        previous = row_to_dict(
            conn.execute(
                "SELECT * FROM user_material_pack_bindings WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (current_user["id"],),
            ).fetchone()
        )
        boiler = row_to_dict(conn.execute("SELECT * FROM boilers WHERE id = ?", (pack["boiler_id"],)).fetchone()) if pack.get("boiler_id") else None

        if not boiler and previous:
            boiler = row_to_dict(conn.execute("SELECT * FROM boilers WHERE id = ?", (previous["boiler_id"],)).fetchone())

        if boiler:
            enterprise_id = boiler["enterprise_id"]
        else:
            enterprise_name = (req.enterpriseName or "").strip()
            if not enterprise_name or not req.boiler:
                raise HTTPException(status_code=400, detail="首次绑定请填写企业和锅炉信息")
            boiler_data = req.boiler
            required_boiler_values = [boiler_data.deviceCode, boiler_data.productNo, boiler_data.model, boiler_data.deviceType]
            if not all(str(value or "").strip() for value in required_boiler_values):
                raise HTTPException(status_code=400, detail="请填写完整锅炉基本信息")
            enterprise_code = f"WX-{current_user['id']}-{int(datetime.utcnow().timestamp())}"
            enterprise_cur = conn.execute(
                "INSERT INTO enterprises(name, code, status, created_at) VALUES(?, ?, 'active', ?)",
                (enterprise_name, enterprise_code, now()),
            )
            enterprise_id = enterprise_cur.lastrowid
            boiler_cur = conn.execute(
                """
                INSERT INTO boilers(
                  enterprise_id, name, device_code, product_no, model, device_type,
                  rated_capacity, rated_pressure, fuel_type, manufacturer, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    enterprise_id,
                    boiler_data.model.strip(),
                    boiler_data.deviceCode.strip(),
                    boiler_data.productNo.strip(),
                    boiler_data.model.strip(),
                    boiler_data.deviceType.strip(),
                    (boiler_data.ratedCapacity or "").strip(),
                    (boiler_data.ratedPressure or "").strip(),
                    (boiler_data.fuelType or "").strip(),
                    (boiler_data.manufacturer or "").strip(),
                    now(),
                ),
            )
            boiler = {"id": boiler_cur.lastrowid, "enterprise_id": enterprise_id, "name": boiler_data.model.strip()}

        conn.execute(
            "UPDATE material_packs SET enterprise_id = ?, boiler_id = ?, status = 'activated', activated_at = ? WHERE id = ?",
            (enterprise_id, boiler["id"], now(), pack["id"]),
        )
        conn.execute(
            "UPDATE user_material_pack_bindings SET status = 'inactive', unbound_at = ? WHERE user_id = ? AND status = 'active'",
            (now(), current_user["id"]),
        )
        binding_cur = conn.execute(
            """
            INSERT INTO user_material_pack_bindings(
              user_id, enterprise_id, boiler_id, material_pack_id, status, expire_at, bound_at, created_at
            ) VALUES(?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (current_user["id"], enterprise_id, boiler["id"], pack["id"], pack.get("expire_at"), now(), now()),
        )
        binding_id = binding_cur.lastrowid
        conn.execute(
            "UPDATE users SET name = ?, enterprise_id = ? WHERE id = ?",
            (user_name, enterprise_id, current_user["id"]),
        )
        user_row = conn.execute(
            "SELECT id, username, name, role, enterprise_id, status FROM users WHERE id = ?",
            (current_user["id"],),
        ).fetchone()
        enterprise_row = conn.execute(
            "SELECT id, name, code, status FROM enterprises WHERE id = ?",
            (enterprise_id,),
        ).fetchone()
        user = user_response(user_row)
        enterprise = enterprise_response(enterprise_row)

    return {
        "token": make_token(user),
        "user": user,
        "enterprise": enterprise,
        "currentBoiler": {"id": boiler["id"], "name": boiler["name"], "enterpriseId": enterprise_id},
        "binding": {"id": binding_id, "materialPackId": pack["id"], "packCode": pack_code, "expireAt": pack.get("expire_at"), "status": "active"},
        "onboarding": {"required": False, "canEnterHome": True, "canInspect": True, "replacementRequired": False, "reason": "active", "message": "绑定成功"},
    }


@app.post("/auth/admin-login")
def admin_login(req: AdminLoginReq):
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, username, password_hash, name, role, enterprise_id, status
            FROM users WHERE username = ?
            """,
            (req.username,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user_row = row_to_dict(row)
    if user_row["status"] != "active" or not verify_password(req.password, user_row["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user = user_response(row)
    return {"token": make_token(user), "user": user}


@app.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(None)):
    return {"user": get_current_user(authorization)}


@app.get("/users")
def users(authorization: Optional[str] = Header(None)):
    current_user = require_roles(authorization, ("platform_admin", "enterprise_admin"))
    filters = []
    params = []
    if current_user["role"] == "enterprise_admin":
        filters.append("enterprise_id = ?")
        params.append(current_user["enterpriseId"])
    where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""
    with db() as conn:
        rows = conn.execute(
            f"""
            SELECT id, username, name, role, enterprise_id, status
            FROM users {where_clause} ORDER BY id
            """,
            tuple(params),
        )
        return [user_response(row) for row in rows]


def enterprise_response(row) -> dict:
    enterprise = row_to_dict(row)
    return {
        "id": enterprise["id"],
        "name": enterprise["name"],
        "code": enterprise["code"],
        "status": enterprise["status"],
    }


@app.post("/users")
def create_user(req: UserCreateReq, authorization: Optional[str] = Header(None)):
    current_user = require_roles(authorization, ("platform_admin", "enterprise_admin"))
    username = req.username.strip()
    name = req.name.strip()
    if not username or not name or not req.password:
        raise HTTPException(status_code=400, detail="账号、姓名和密码不能为空")
    ensure_user_manage_scope(current_user, req.role, req.enterpriseId)
    with db() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO users(username, password_hash, name, role, enterprise_id, status, created_at)
                VALUES(?, ?, ?, ?, ?, 'active', ?)
                """,
                (username, password_hash(req.password), name, req.role, req.enterpriseId, now()),
            )
        except Exception as exc:
            if not is_integrity_error(exc):
                raise
            raise HTTPException(status_code=409, detail="账号已存在")
        row = conn.execute(
            "SELECT id, username, name, role, enterprise_id, status FROM users WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return user_response(row)


@app.put("/users/{user_id}")
def update_user(user_id: int, req: UserUpdateReq, authorization: Optional[str] = Header(None)):
    current_user = require_roles(authorization, ("platform_admin", "enterprise_admin"))
    with db() as conn:
        existing = row_to_dict(
            conn.execute(
                "SELECT id, username, name, role, enterprise_id, status FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        )
        if not existing:
            raise HTTPException(status_code=404, detail="用户不存在")
        target_role = req.role or existing["role"]
        target_enterprise_id = req.enterpriseId if req.enterpriseId is not None else existing["enterprise_id"]
        ensure_user_manage_scope(current_user, target_role, target_enterprise_id)
        if current_user["role"] == "enterprise_admin":
            ensure_user_manage_scope(current_user, existing["role"], existing["enterprise_id"])
        updates = []
        params = []
        if req.name is not None:
            if not req.name.strip():
                raise HTTPException(status_code=400, detail="姓名不能为空")
            updates.append("name = ?")
            params.append(req.name.strip())
        if req.role is not None:
            updates.append("role = ?")
            params.append(req.role)
        if req.enterpriseId is not None:
            updates.append("enterprise_id = ?")
            params.append(req.enterpriseId)
        if req.status is not None:
            if req.status not in ("active", "disabled"):
                raise HTTPException(status_code=400, detail="状态不合法")
            if req.status == "disabled" and current_user.get("id") == user_id:
                raise HTTPException(status_code=400, detail="不能禁用当前登录用户")
            updates.append("status = ?")
            params.append(req.status)
        if req.role is not None and current_user.get("id") == user_id and req.role != current_user.get("role"):
            raise HTTPException(status_code=400, detail="不能修改当前登录用户角色")
        if req.password:
            updates.append("password_hash = ?")
            params.append(password_hash(req.password))
        if updates:
            params.append(user_id)
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
        row = conn.execute(
            "SELECT id, username, name, role, enterprise_id, status FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return user_response(row)


@app.patch("/users/{user_id}/status")
def update_user_status(user_id: int, req: UserStatusReq, authorization: Optional[str] = Header(None)):
    if req.status not in ("active", "disabled"):
        raise HTTPException(status_code=400, detail="状态不合法")
    return update_user(user_id, UserUpdateReq(status=req.status), authorization)


@app.get("/enterprises")
def enterprises():
    with db() as conn:
        return [enterprise_response(row) for row in conn.execute("SELECT id, name, code, status FROM enterprises ORDER BY id")]


@app.post("/enterprises")
def create_enterprise(req: EnterpriseCreateReq, authorization: Optional[str] = Header(None)):
    require_roles(authorization, ("platform_admin",))
    name = req.name.strip()
    code = req.code.strip() if req.code else None
    if not name:
        raise HTTPException(status_code=400, detail="企业名称不能为空")
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO enterprises(name, code, status, created_at) VALUES(?, ?, 'active', ?)",
                (name, code, now()),
            )
        except Exception as exc:
            if not is_integrity_error(exc):
                raise
            raise HTTPException(status_code=409, detail="企业编码已存在")
        row = conn.execute("SELECT id, name, code, status FROM enterprises WHERE id = ?", (cur.lastrowid,)).fetchone()
        return enterprise_response(row)


@app.put("/enterprises/{enterprise_id}")
def update_enterprise(enterprise_id: int, req: EnterpriseUpdateReq, authorization: Optional[str] = Header(None)):
    require_roles(authorization, ("platform_admin",))
    with db() as conn:
        existing = conn.execute("SELECT id, name, code, status FROM enterprises WHERE id = ?", (enterprise_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="企业不存在")
        updates = []
        params = []
        if req.name is not None:
            if not req.name.strip():
                raise HTTPException(status_code=400, detail="企业名称不能为空")
            updates.append("name = ?")
            params.append(req.name.strip())
        if req.code is not None:
            updates.append("code = ?")
            params.append(req.code.strip() or None)
        if req.status is not None:
            if req.status not in ("active", "disabled"):
                raise HTTPException(status_code=400, detail="状态不合法")
            updates.append("status = ?")
            params.append(req.status)
        if updates:
            params.append(enterprise_id)
            try:
                conn.execute(f"UPDATE enterprises SET {', '.join(updates)} WHERE id = ?", tuple(params))
            except Exception as exc:
                if not is_integrity_error(exc):
                    raise
                raise HTTPException(status_code=409, detail="企业编码已存在")
        row = conn.execute("SELECT id, name, code, status FROM enterprises WHERE id = ?", (enterprise_id,)).fetchone()
        return enterprise_response(row)


@app.patch("/enterprises/{enterprise_id}/status")
def update_enterprise_status(enterprise_id: int, req: EnterpriseStatusReq, authorization: Optional[str] = Header(None)):
    if req.status not in ("active", "disabled"):
        raise HTTPException(status_code=400, detail="状态不合法")
    return update_enterprise(enterprise_id, EnterpriseUpdateReq(status=req.status), authorization)


@app.get("/boilers")
def boilers(enterpriseId: int = 1):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, enterprise_id AS enterpriseId, name, device_code AS deviceCode,
                   product_no AS productNo, model, device_type AS deviceType,
                   rated_capacity AS ratedCapacity, rated_pressure AS ratedPressure,
                   rated_steam_temp AS ratedSteamTemp, fuel_type AS fuelType,
                   thermal_efficiency AS thermalEfficiency, manufacturer, manufacture_date AS manufactureDate,
                   license_no AS licenseNo, status
            FROM boilers WHERE enterprise_id = ? ORDER BY id
            """,
            (enterpriseId,),
        )
        return [row_to_dict(row) for row in rows]


@app.post("/boilers")
def create_boiler(req: BoilerCreateReq, authorization: Optional[str] = Header(None)):
    current_user = require_roles(authorization, ("platform_admin", "enterprise_admin"))
    ensure_enterprise_scope(current_user, req.enterpriseId)
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO boilers(
              enterprise_id, name, device_code, product_no, model, device_type, rated_capacity,
              rated_pressure, rated_steam_temp, fuel_type, thermal_efficiency, manufacturer,
              manufacture_date, license_no, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req.enterpriseId,
                req.model,
                req.deviceCode,
                req.productNo,
                req.model,
                req.deviceType,
                req.ratedCapacity,
                req.ratedPressure,
                req.ratedSteamTemp,
                req.fuelType,
                req.thermalEfficiency,
                req.manufacturer,
                req.manufactureDate,
                req.licenseNo,
                now(),
            ),
        )
        return {"id": cur.lastrowid, "name": req.model, "enterpriseId": req.enterpriseId}


@app.put("/boilers/{boiler_id}")
def update_boiler(boiler_id: int, req: BoilerUpdateReq, authorization: Optional[str] = Header(None)):
    current_user = require_roles(authorization, ("platform_admin", "enterprise_admin"))
    field_map = {
        "enterpriseId": "enterprise_id",
        "deviceCode": "device_code",
        "productNo": "product_no",
        "model": "model",
        "deviceType": "device_type",
        "ratedCapacity": "rated_capacity",
        "ratedPressure": "rated_pressure",
        "ratedSteamTemp": "rated_steam_temp",
        "fuelType": "fuel_type",
        "thermalEfficiency": "thermal_efficiency",
        "manufacturer": "manufacturer",
        "manufactureDate": "manufacture_date",
        "licenseNo": "license_no",
        "status": "status",
    }
    with db() as conn:
        existing = row_to_dict(conn.execute("SELECT * FROM boilers WHERE id = ?", (boiler_id,)).fetchone())
        if not existing:
            raise HTTPException(status_code=404, detail="锅炉不存在")
        target_enterprise_id = req.enterpriseId if req.enterpriseId is not None else existing["enterprise_id"]
        ensure_enterprise_scope(current_user, target_enterprise_id)
        if current_user["role"] == "enterprise_admin":
            ensure_enterprise_scope(current_user, existing["enterprise_id"])
        updates = []
        params = []
        payload = req.dict(exclude_unset=True)
        if payload.get("status") is not None and payload["status"] not in ("normal", "archived"):
            raise HTTPException(status_code=400, detail="状态不合法")
        for key, column in field_map.items():
            if key not in payload:
                continue
            value = payload[key]
            if isinstance(value, str):
                value = value.strip()
            if key in ("deviceCode", "productNo", "model", "deviceType") and not value:
                raise HTTPException(status_code=400, detail="设备代码、产品编号、型号和设备类型不能为空")
            updates.append(f"{column} = ?")
            params.append(value)
        if "model" in payload:
            updates.append("name = ?")
            params.append(payload["model"].strip())
        if updates:
            params.append(boiler_id)
            conn.execute(f"UPDATE boilers SET {', '.join(updates)} WHERE id = ?", tuple(params))
        row = conn.execute(
            """
            SELECT id, enterprise_id AS enterpriseId, name, device_code AS deviceCode,
                   product_no AS productNo, model, device_type AS deviceType,
                   rated_capacity AS ratedCapacity, rated_pressure AS ratedPressure,
                   rated_steam_temp AS ratedSteamTemp, fuel_type AS fuelType,
                   thermal_efficiency AS thermalEfficiency, manufacturer, manufacture_date AS manufactureDate,
                   license_no AS licenseNo, status
            FROM boilers WHERE id = ?
            """,
            (boiler_id,),
        ).fetchone()
        return row_to_dict(row)


@app.get("/material-packs")
def list_packs(enterpriseId: int = 1):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.enterprise_id AS enterpriseId, p.code, p.type, p.status,
                   p.boiler_id AS boilerId, b.name AS boilerName, p.expire_at AS expireAt
            FROM material_packs p
            LEFT JOIN boilers b ON b.id = p.boiler_id
            WHERE p.enterprise_id = ? ORDER BY p.id DESC
            """,
            (enterpriseId,),
        )
        return [row_to_dict(row) for row in rows]


@app.post("/material-packs")
def create_pack(req: PackCreateReq, authorization: Optional[str] = Header(None)):
    current_user = require_roles(authorization, ("platform_admin", "enterprise_admin"))
    ensure_enterprise_scope(current_user, req.enterpriseId)
    with db() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO material_packs(enterprise_id, code, type, status, expire_at, created_at)
                VALUES(?, ?, ?, 'unactivated', ?, ?)
                """,
                (req.enterpriseId, req.code, req.type, req.expireAt, now()),
            )
        except Exception as exc:
            if not is_integrity_error(exc):
                raise
            raise HTTPException(status_code=409, detail="检测包编码已存在")
        return {"id": cur.lastrowid, "code": req.code, "enterpriseId": req.enterpriseId, "status": "unactivated"}


@app.post("/material-packs/verify")
def verify_pack(req: PackVerifyReq):
    with db() as conn:
        pack = row_to_dict(
            conn.execute(
                """
                SELECT p.*, b.name AS boiler_name
                FROM material_packs p
                LEFT JOIN boilers b ON b.id = p.boiler_id
                WHERE p.code = ?
                """,
                (req.code,),
            ).fetchone()
        )
    if not pack:
        raise HTTPException(status_code=404, detail="检测包不存在")
    if pack["status"] in ("expired", "invalid", "exhausted"):
        raise HTTPException(status_code=400, detail="检测包不可用")
    return {
        "valid": True,
        "pack": {
            "id": pack["id"],
            "code": pack["code"],
            "enterpriseId": pack["enterprise_id"],
            "boilerId": pack["boiler_id"],
            "boilerName": pack.get("boiler_name") or "",
            "status": pack["status"],
            "type": pack["type"],
            "expireAt": pack["expire_at"],
        },
    }


@app.post("/material-packs/activate")
def activate_pack(req: PackActivateReq):
    with db() as conn:
        pack = row_to_dict(conn.execute("SELECT * FROM material_packs WHERE code = ?", (req.code,)).fetchone())
        if not pack:
            raise HTTPException(status_code=404, detail="检测包不存在")
        enterprise_id = req.enterpriseId or pack["enterprise_id"]
        if req.boilerId:
            boiler = row_to_dict(conn.execute("SELECT * FROM boilers WHERE id = ?", (req.boilerId,)).fetchone())
            if not boiler:
                raise HTTPException(status_code=404, detail="锅炉不存在")
            if boiler["enterprise_id"] != enterprise_id or pack["enterprise_id"] != enterprise_id:
                raise HTTPException(status_code=400, detail="材料包和锅炉不属于同一企业")
        conn.execute(
            """
            UPDATE material_packs
            SET status = 'activated', boiler_id = COALESCE(?, boiler_id), enterprise_id = COALESCE(?, enterprise_id), activated_at = ?
            WHERE code = ?
            """,
            (req.boilerId, enterprise_id, now(), req.code),
        )
        updated = row_to_dict(conn.execute("SELECT * FROM material_packs WHERE code = ?", (req.code,)).fetchone())
    return {
        "id": updated["id"],
        "code": updated["code"],
        "enterpriseId": updated["enterprise_id"],
        "boilerId": updated["boiler_id"],
        "status": updated["status"],
    }


@app.post("/material-packs/invalidate")
def invalidate_pack(req: PackCodeReq, authorization: Optional[str] = Header(None)):
    require_roles(authorization, ("platform_admin", "enterprise_admin"))
    with db() as conn:
        cur = conn.execute("UPDATE material_packs SET status = 'invalid' WHERE code = ?", (req.code,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="检测包不存在")
    return {"code": req.code, "status": "invalid"}


@app.post("/material-packs/unbind")
def unbind_pack(req: PackCodeReq, authorization: Optional[str] = Header(None)):
    require_roles(authorization, ("platform_admin", "enterprise_admin"))
    with db() as conn:
        cur = conn.execute(
            "UPDATE material_packs SET boiler_id = NULL, status = 'activated' WHERE code = ?",
            (req.code,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="检测包不存在")
    return {"code": req.code, "status": "activated", "boilerId": None}


def water_quality_limit_response(row) -> dict:
    limit = row_to_dict(row)
    if not limit:
        return {}
    return {
        "id": limit["id"],
        "itemCode": limit["item_code"],
        "itemName": limit.get("item_name") or limit["item_code"],
        "priority": limit.get("priority"),
        "boilerType": limit["boiler_type"],
        "sampleType": limit["sample_type"],
        "pressureMinMpa": decimal_to_number(limit["pressure_min_mpa"]),
        "pressureMaxMpa": decimal_to_number(limit["pressure_max_mpa"]),
        "minValue": decimal_to_number(limit["min_value"]),
        "maxValue": decimal_to_number(limit["max_value"]),
        "unit": limit["unit"] or "",
        "displayRange": limit["display_range"] or "",
        "standardSource": limit["standard_source"] or "",
        "standardNote": limit["standard_note"] or "",
        "enabled": bool(limit["enabled"]),
        "createdAt": limit["created_at"],
        "updatedAt": limit.get("updated_at"),
        "updatedBy": limit.get("updated_by"),
        "updatedByName": limit.get("updated_by_name"),
    }


def load_water_quality_limits(conn):
    rows = conn.execute(
        """
        SELECT l.*, i.name AS item_name, i.priority
        FROM water_quality_limits l
        LEFT JOIN water_test_items i ON i.code = l.item_code
        ORDER BY COALESCE(i.priority, 999), l.id
        """
    )
    return [water_quality_limit_response(row) for row in rows]


@app.get("/water-quality-limits")
def list_water_quality_limits(authorization: Optional[str] = Header(None)):
    require_roles(authorization, ("platform_admin", "enterprise_admin"))
    with db() as conn:
        ensure_schema_updates(conn)
        return load_water_quality_limits(conn)


@app.put("/water-quality-limits/{limit_id}")
def update_water_quality_limit(limit_id: int, req: WaterQualityLimitUpdateReq, authorization: Optional[str] = Header(None)):
    current_user = require_roles(authorization, ("platform_admin", "enterprise_admin"))
    if req.minValue is not None and req.maxValue is not None and req.minValue > req.maxValue:
        raise HTTPException(status_code=400, detail="下限不能大于上限")
    if req.pressureMinMpa is not None and req.pressureMaxMpa is not None and req.pressureMinMpa > req.pressureMaxMpa:
        raise HTTPException(status_code=400, detail="压力下限不能大于压力上限")
    field_map = {
        "pressureMinMpa": "pressure_min_mpa",
        "pressureMaxMpa": "pressure_max_mpa",
        "minValue": "min_value",
        "maxValue": "max_value",
        "unit": "unit",
        "displayRange": "display_range",
        "standardSource": "standard_source",
        "standardNote": "standard_note",
        "enabled": "enabled",
    }
    payload = req.dict(exclude_unset=True)
    with db() as conn:
        ensure_schema_updates(conn)
        existing = row_to_dict(conn.execute("SELECT * FROM water_quality_limits WHERE id = ?", (limit_id,)).fetchone())
        if not existing:
            raise HTTPException(status_code=404, detail="检测标准不存在")
        target_min = payload.get("minValue", existing["min_value"])
        target_max = payload.get("maxValue", existing["max_value"])
        if target_min is not None and target_max is not None and float(target_min) > float(target_max):
            raise HTTPException(status_code=400, detail="下限不能大于上限")
        target_pressure_min = payload.get("pressureMinMpa", existing["pressure_min_mpa"])
        target_pressure_max = payload.get("pressureMaxMpa", existing["pressure_max_mpa"])
        if target_pressure_min is not None and target_pressure_max is not None and float(target_pressure_min) > float(target_pressure_max):
            raise HTTPException(status_code=400, detail="压力下限不能大于压力上限")
        updates = []
        params = []
        for key, column in field_map.items():
            if key not in payload:
                continue
            value = payload[key]
            if isinstance(value, str):
                value = value.strip()
            if key == "enabled":
                value = 1 if value else 0
            updates.append(f"{column} = ?")
            params.append(value)
        if updates:
            updates.extend(["updated_at = ?", "updated_by = ?", "updated_by_name = ?"])
            params.extend([now(), current_user.get("id"), current_user.get("name") or current_user.get("username")])
            params.append(limit_id)
            conn.execute(f"UPDATE water_quality_limits SET {', '.join(updates)} WHERE id = ?", tuple(params))
        row = conn.execute(
            """
            SELECT l.*, i.name AS item_name, i.priority
            FROM water_quality_limits l
            LEFT JOIN water_test_items i ON i.code = l.item_code
            WHERE l.id = ?
            """,
            (limit_id,),
        ).fetchone()
        return water_quality_limit_response(row)


@app.post("/water-quality-limits/reset")
def reset_water_quality_limits(authorization: Optional[str] = Header(None)):
    current_user = require_roles(authorization, ("platform_admin", "enterprise_admin"))
    with db() as conn:
        ensure_schema_updates(conn)
        seed_water_quality_limits(conn)
        retire_legacy_broad_limits(conn)
        conn.execute(
            "UPDATE water_quality_limits SET updated_at = ?, updated_by = ?, updated_by_name = ? WHERE boiler_type = 'steam' AND sample_type = 'boiler_water'",
            (now(), current_user.get("id"), current_user.get("name") or current_user.get("username")),
        )
        return load_water_quality_limits(conn)


def parse_number(value: str) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def pressure_segment_text(pressure_min, pressure_max) -> str:
    pressure_min = decimal_to_number(pressure_min)
    pressure_max = decimal_to_number(pressure_max)
    if pressure_min is None and pressure_max is None:
        return ""
    if pressure_min is None:
        return f"≤{pressure_max:g} MPa"
    if pressure_max is None:
        return f"P>{pressure_min:g} MPa"
    if pressure_min == 0:
        return f"P≤{pressure_max:g} MPa"
    return f"{pressure_min:g}<P≤{pressure_max:g} MPa"


def get_inspection_boiler_context(conn, inspection_id: int) -> dict:
    row = row_to_dict(
        conn.execute(
            """
            SELECT i.id AS inspectionId, i.boiler_id AS boilerId, b.name AS boilerName,
                   b.rated_pressure AS ratedPressure
            FROM inspections i
            LEFT JOIN boilers b ON b.id = i.boiler_id
            WHERE i.id = ?
            """,
            (inspection_id,),
        ).fetchone()
    )
    if not row:
        raise HTTPException(status_code=404, detail="inspection not found")
    pressure = parse_number(str(row.get("ratedPressure") or ""))
    return {
        "inspectionId": row["inspectionId"],
        "boilerId": row["boilerId"],
        "boilerName": row.get("boilerName") or "",
        "ratedPressure": row.get("ratedPressure") or "",
        "ratedPressureMpa": pressure,
    }


def get_water_test_templates(conn, rated_pressure_mpa: Optional[float]) -> list[dict]:
    rows = conn.execute(
        """
        SELECT i.code, i.name, i.priority, i.method, i.meaning, i.maintenance,
               l.min_value AS standardMin, l.max_value AS standardMax, l.unit,
               l.display_range AS normalRange, l.standard_source AS standardSource,
               l.standard_note AS standardNote, l.pressure_min_mpa AS pressureMinMpa,
               l.pressure_max_mpa AS pressureMaxMpa
        FROM water_test_items i
        LEFT JOIN water_quality_limits l ON l.id = (
          SELECT l2.id
          FROM water_quality_limits l2
          WHERE l2.item_code = i.code
            AND l2.boiler_type = 'steam'
            AND l2.sample_type = 'boiler_water'
            AND l2.enabled = 1
            AND ? IS NOT NULL
            AND (
              l2.pressure_min_mpa IS NULL
              OR (l2.pressure_min_mpa = 0 AND l2.pressure_min_mpa <= ?)
              OR l2.pressure_min_mpa < ?
            )
            AND (l2.pressure_max_mpa IS NULL OR l2.pressure_max_mpa >= ?)
          ORDER BY COALESCE(l2.pressure_min_mpa, -999999) DESC,
                   COALESCE(l2.pressure_max_mpa, 999999) ASC,
                   l2.id ASC
          LIMIT 1
        )
        WHERE i.enabled = 1
        ORDER BY i.priority
        """,
        (rated_pressure_mpa, rated_pressure_mpa, rated_pressure_mpa, rated_pressure_mpa),
    )
    return [row_to_dict(row) for row in rows]


def judge_item_status(value: str, standard_min, standard_max) -> str:
    number = parse_number(value)
    if number is None:
        return "warning"
    if standard_min is not None and number < float(standard_min):
        return "warning"
    if standard_max is not None and number > float(standard_max):
        return "warning"
    return "normal"


def decimal_to_number(value):
    return float(value) if value is not None else None


def item_number(item: dict) -> Optional[float]:
    return parse_number(str(item.get("value", "")))


def item_low(item: dict) -> bool:
    value = item_number(item)
    standard_min = item.get("standardMin")
    return value is not None and standard_min is not None and value < float(standard_min)


def item_high(item: dict) -> bool:
    value = item_number(item)
    standard_max = item.get("standardMax")
    return value is not None and standard_max is not None and value > float(standard_max)


def related_item_names(item_map: dict, codes: list[str]) -> str:
    return "、".join(item_map[code]["name"] for code in codes if code in item_map)


def build_diagnosis_item(
    risk_code: str,
    risk_type: str,
    level: str,
    title: str,
    reason: str,
    advice: str,
    field_action: str,
    retest_plan: str,
    support_notice: str,
    related_items: list[str],
    item_map: dict,
) -> dict:
    return {
        "riskCode": risk_code,
        "riskType": risk_type,
        "level": level,
        "title": title,
        "reason": reason,
        "advice": advice,
        "fieldAction": field_action,
        "retestPlan": retest_plan,
        "supportNotice": support_notice,
        "relatedItems": related_items,
        "relatedItemNames": related_item_names(item_map, related_items),
    }


def build_boiler_water_diagnosis(items: list[dict], standard_warnings: list[str]) -> tuple[int, str, str, list[dict]]:
    item_map = {item["code"]: item for item in items}
    diagnosis = []
    covered = set()

    def has(codes: list[str], direction: str) -> bool:
        checker = item_high if direction == "high" else item_low
        return all(code in item_map and checker(item_map[code]) for code in codes)

    combo_rules = [
        {
            "codes": ["hardness", "phosphate"],
            "direction": ["high", "low"],
            "riskCode": "scale",
            "riskType": "结垢风险",
            "level": "high",
            "title": "结垢风险预警",
            "reason": "硬度偏高且磷酸根偏低，说明钙镁离子残留增加，同时防垢药剂余量不足。",
            "fieldAction": "检查软水器盐箱、再生状态和加药泵；按现场药剂方案补加防垢剂/磷酸盐药剂，并安排一次排污。",
            "retestPlan": "处理后建议2小时内复测硬度、磷酸根和pH。",
            "supportNotice": "后台提醒：若连续两次出现硬度偏高且磷酸根偏低，服务支持人员需复核软水器状态、补水硬度和防垢药剂方案。",
        },
        {
            "codes": ["ph", "sulfite"],
            "direction": ["low", "low"],
            "riskCode": "corrosion",
            "riskType": "腐蚀风险",
            "level": "high",
            "title": "腐蚀风险预警",
            "reason": "pH偏低且亚硫酸根偏低，锅水保护性下降，氧腐蚀和酸性腐蚀风险上升。",
            "fieldAction": "检查碱性药剂、除氧剂药箱液位和加药泵运行状态；按现场方案补加碱性药剂和除氧剂。",
            "retestPlan": "处理后建议2小时内复测pH、亚硫酸根和总碱度。",
            "supportNotice": "后台提醒：若pH和亚硫酸根持续偏低，服务支持人员需复核加药配方、加药泵流量和除氧管理。",
        },
        {
            "codes": ["chloride", "alkalinity"],
            "direction": ["high", "high"],
            "riskCode": "concentration",
            "riskType": "浓缩/排污风险",
            "level": "warning",
            "title": "排污不足预警",
            "reason": "氯离子和总碱度同时偏高，提示锅水浓缩倍数偏高，可能存在排污不足。",
            "fieldAction": "加强连续排污或安排一次定期排污；排污过程中注意按现场规程操作。",
            "retestPlan": "排污后建议2小时内复测氯离子、总碱度和pH。",
            "supportNotice": "后台提醒：若氯离子和总碱度持续偏高，服务支持人员需复核排污制度、补水水质和浓缩倍数。",
        },
        {
            "codes": ["phosphate", "sulfite"],
            "direction": ["high", "high"],
            "riskCode": "overfeed",
            "riskType": "加药过量风险",
            "level": "warning",
            "title": "加药过量预警",
            "reason": "磷酸根和亚硫酸根同时偏高，说明药剂余量偏多，盐分和排污负担可能上升。",
            "fieldAction": "暂缓或减少防垢剂、除氧剂投加，并安排一次适量排污。",
            "retestPlan": "调整后建议2小时内复测磷酸根、亚硫酸根和氯离子。",
            "supportNotice": "后台提醒：若药剂余量持续偏高，服务支持人员需复核加药泵频率、药液浓度和班次加药记录。",
        },
        {
            "codes": ["ph", "alkalinity"],
            "direction": ["high", "high"],
            "riskCode": "foaming",
            "riskType": "汽水共腾风险",
            "level": "warning",
            "title": "汽水共腾风险预警",
            "reason": "pH和总碱度同时偏高，锅水起泡和蒸汽携水风险增加。",
            "fieldAction": "加强排污，暂缓或减少碱性药剂投加，并检查药箱浓度。",
            "retestPlan": "排污和调整加药后建议2小时内复测pH、总碱度和氯离子。",
            "supportNotice": "后台提醒：若pH和总碱度持续偏高，服务支持人员需复核排污制度、碱性药剂方案和现场运行反馈。",
        },
    ]

    for rule in combo_rules:
        if all(has([code], direction) for code, direction in zip(rule["codes"], rule["direction"])):
            diagnosis.append(
                build_diagnosis_item(
                    rule["riskCode"],
                    rule["riskType"],
                    rule["level"],
                    rule["title"],
                    rule["reason"],
                    rule["fieldAction"],
                    rule["fieldAction"],
                    rule["retestPlan"],
                    rule["supportNotice"],
                    rule["codes"],
                    item_map,
                )
            )
            covered.update(rule["codes"])

    single_rules = {
        ("ph", "low"): ("酸碱度偏低", "腐蚀风险", "pH偏低，锅水碱性保护不足。", "检查碱性药剂药箱液位和加药泵运行状态，按现场方案补加碱性药剂。", "建议2小时内复测pH和总碱度。", "后台提醒：若pH连续偏低，需复核碱性药剂方案和加药泵流量。"),
        ("ph", "high"): ("酸碱度偏高", "碱腐蚀/共腾风险", "pH偏高，可能增加碱腐蚀和汽水共腾风险。", "加强排污，暂缓或减少碱性药剂投加，并检查药箱浓度。", "建议2小时内复测pH、总碱度和氯离子。", "后台提醒：若pH连续偏高，需复核排污制度和碱性药剂投加量。"),
        ("phosphate", "low"): ("磷酸根偏低", "结垢风险", "磷酸根偏低，防垢药剂余量不足。", "检查防垢剂药箱液位和加药泵，按现场方案补加防垢剂/磷酸盐药剂。", "建议2小时内复测磷酸根和pH。", "后台提醒：若磷酸根连续偏低，需复核防垢剂浓度、泵量和加药频次。"),
        ("phosphate", "high"): ("磷酸根偏高", "加药过量风险", "磷酸根偏高，可能存在防垢剂过量。", "暂缓或减少防垢剂投加，并安排一次适量排污。", "建议2小时内复测磷酸根和氯离子。", "后台提醒：若磷酸根连续偏高，需复核防垢剂投加方案。"),
        ("sulfite", "low"): ("亚硫酸根偏低", "腐蚀风险", "亚硫酸根偏低，除氧剂余量不足。", "检查除氧剂药箱液位和加药泵，按现场方案补加除氧剂。", "建议2小时内复测亚硫酸根和pH。", "后台提醒：若亚硫酸根连续偏低，需复核除氧剂浓度、泵量和除氧管理。"),
        ("sulfite", "high"): ("亚硫酸根偏高", "加药过量风险", "亚硫酸根偏高，可能增加盐分和排污负担。", "暂缓或减少除氧剂投加，并安排一次适量排污。", "建议2小时内复测亚硫酸根和氯离子。", "后台提醒：若亚硫酸根连续偏高，需复核除氧剂投加方案。"),
        ("alkalinity", "low"): ("总碱度偏低", "保护不足风险", "总碱度偏低，锅水缓冲和防腐保护不足。", "检查碱性药剂药箱液位和加药泵，按现场方案补加碱性药剂。", "建议2小时内复测总碱度和pH。", "后台提醒：若总碱度连续偏低，需复核碱性药剂方案。"),
        ("alkalinity", "high"): ("总碱度偏高", "汽水共腾风险", "总碱度偏高，起泡和汽水共腾风险上升。", "加强排污，暂缓或减少碱性药剂投加。", "建议2小时内复测总碱度、pH和氯离子。", "后台提醒：若总碱度连续偏高，需复核排污制度和碱性药剂方案。"),
        ("chloride", "high"): ("氯离子偏高", "浓缩/点蚀风险", "氯离子偏高，提示浓缩程度偏高且点蚀风险增加。", "加强连续排污或安排一次定期排污。", "排污后建议2小时内复测氯离子、总碱度和pH。", "后台提醒：若氯离子连续偏高，需复核排污制度和补水水质。"),
        ("hardness", "high"): ("硬度偏高", "结垢风险", "硬度偏高，说明钙镁离子残留偏多。", "检查软水器盐箱、再生状态和旁通阀状态，并确认防垢剂投加正常。", "建议2小时内复测硬度和磷酸根。", "后台提醒：若硬度连续偏高，需复核软水器运行、补水硬度和水处理方案。"),
    }
    for item in items:
        if item["code"] in covered or item.get("status") != "warning":
            continue
        direction = "low" if item_low(item) else "high" if item_high(item) else "warning"
        title, risk_type, reason, field_action, retest_plan, support_notice = single_rules.get(
            (item["code"], direction),
            (
                f"{item['name']}异常",
                "单项异常",
                f"{item['name']}检测结果超出当前压力段建议范围。",
                "换新试纸重新取样复测，并检查相关药剂、排污或软水器基础状态。",
                f"建议2小时内复测{item['name']}。",
                f"后台提醒：{item['name']}连续异常时，服务支持人员需复核现场处理记录。",
            ),
        )
        diagnosis.append(
            build_diagnosis_item(
                f"{item['code']}_{direction}",
                risk_type,
                "warning",
                title,
                reason,
                field_action,
                field_action,
                retest_plan,
                support_notice,
                [item["code"]],
                item_map,
            )
        )

    if not diagnosis and not standard_warnings:
        diagnosis.append(
            build_diagnosis_item(
                "normal",
                "正常",
                "normal",
                "锅水状态正常",
                "6项炉水/锅水试纸检测均在当前压力段建议范围内。",
                "按计划继续巡检，保持现有加药、排污和软化水管理节奏。",
                "按计划继续巡检，保持现有加药、排污和软化水管理节奏。",
                "按计划进行下一次常规检测。",
                "后台提醒：当前无需人工介入，继续观察趋势即可。",
                [],
                item_map,
            )
        )

    warning_items = [item for item in items if item.get("status") == "warning"]
    unknown_items = [item for item in items if item.get("status") == "unknown"]
    high_risk_count = sum(1 for item in diagnosis if item.get("level") == "high")
    score = max(60, 100 - len(warning_items) * 6 - len(unknown_items) * 4 - high_risk_count * 8)
    risk_level = "warning" if warning_items or unknown_items or standard_warnings else "normal"
    risk_types = []
    for item in diagnosis:
        risk_type = item.get("riskType")
        if risk_type and risk_type != "正常" and risk_type not in risk_types:
            risk_types.append(risk_type)
    if warning_items:
        summary = f"锅水检测发现{'、'.join(item['name'] for item in warning_items)} {len(warning_items)}项预警"
        if risk_types:
            summary += f"，主要风险：{'、'.join(risk_types)}"
        summary += "。"
    elif unknown_items or standard_warnings:
        summary = "锅水检测已完成，但部分项目未匹配到适用压力段标准，建议先完善锅炉额定压力和检测标准配置。"
    else:
        summary = "锅水6项试纸检测均在当前压力段建议范围内，建议按计划继续巡检。"
    return score, risk_level, summary, diagnosis


def inspection_result_payload(inspection_id: int, conn=None, input_values: Optional[dict] = None) -> dict:
    sample_values = {
        "ph": "8.2",
        "phosphate": "8",
        "sulfite": "18",
        "alkalinity": "22",
        "chloride": "320",
        "hardness": "0.05",
    }
    source_values = input_values or sample_values
    recognition_source = "manual_gray" if input_values else "sample_fallback"
    context = get_inspection_boiler_context(conn, inspection_id) if conn else {
        "inspectionId": inspection_id,
        "boilerId": None,
        "boilerName": "",
        "ratedPressure": "",
        "ratedPressureMpa": 1.25,
    }
    templates = get_water_test_templates(conn, context["ratedPressureMpa"]) if conn else [
        {
            **item,
            "standardMin": next((limit["min"] for limit in WATER_QUALITY_LIMITS if limit["code"] == item["code"]), None),
            "standardMax": next((limit["max"] for limit in WATER_QUALITY_LIMITS if limit["code"] == item["code"]), None),
            "unit": next((limit["unit"] for limit in WATER_QUALITY_LIMITS if limit["code"] == item["code"]), ""),
            "normalRange": item["normalRange"],
            "standardSource": STANDARD_SOURCE,
            "standardNote": STANDARD_NOTE,
            "pressureMinMpa": 0,
            "pressureMaxMpa": 3.8,
        }
        for item in WATER_TEST_ITEMS
    ]
    items = []
    for template in templates:
        value = str(source_values.get(template["code"], sample_values[template["code"]])).strip()
        standard_min = decimal_to_number(template.get("standardMin"))
        standard_max = decimal_to_number(template.get("standardMax"))
        standard_missing = context["ratedPressureMpa"] is None or (standard_min is None and standard_max is None)
        status = "unknown" if standard_missing else judge_item_status(value, standard_min, standard_max)
        segment = pressure_segment_text(template.get("pressureMinMpa"), template.get("pressureMaxMpa"))
        items.append(
            {
                "code": template["code"],
                "name": template["name"],
                "value": value,
                "confidence": 1 if input_values else 0.72,
                "recognitionSource": recognition_source,
                "reviewRequired": False if input_values else True,
                "unit": template.get("unit") or "",
                "priority": template["priority"],
                "method": template["method"],
                "status": status,
                "normalRange": template.get("normalRange") or "未配置标准",
                "standardMin": standard_min,
                "standardMax": standard_max,
                "standardSource": "" if standard_missing else (template.get("standardSource") or STANDARD_SOURCE),
                "standardNote": "未匹配到适用压力段标准" if standard_missing else (template.get("standardNote") or STANDARD_NOTE),
                "pressureMinMpa": decimal_to_number(template.get("pressureMinMpa")),
                "pressureMaxMpa": decimal_to_number(template.get("pressureMaxMpa")),
                "pressureSegment": segment,
                "ratedPressureMpa": context["ratedPressureMpa"],
                "standardMatched": not standard_missing,
                "meaning": template["meaning"],
                "maintenance": template["maintenance"],
            }
        )
    unmatched = [item["name"] for item in items if not item["standardMatched"]]
    standard_warnings = []
    if context["ratedPressureMpa"] is None:
        standard_warnings.append("锅炉档案未填写额定压力，无法自动匹配压力段标准。")
    if unmatched:
        standard_warnings.append(f"{'、'.join(unmatched)}未匹配到适用压力段标准。")
    score, risk_level, summary, diagnosis = build_boiler_water_diagnosis(items, standard_warnings)
    return {
        "inspectionId": inspection_id,
        "boilerId": context["boilerId"],
        "boilerName": context["boilerName"],
        "ratedPressure": context["ratedPressure"],
        "ratedPressureMpa": context["ratedPressureMpa"],
        "score": score,
        "status": "done",
        "riskLevel": risk_level,
        "recognitionSource": recognition_source,
        "summary": summary,
        "standardWarnings": standard_warnings,
        "items": items,
        "diagnosis": diagnosis,
    }


def save_inspection_test_results(conn, inspection_id: int, items: list[dict]) -> None:
    conn.execute("DELETE FROM inspection_test_results WHERE inspection_id = ?", (inspection_id,))
    for item in items:
        conn.execute(
            """
            INSERT INTO inspection_test_results(
              inspection_id, item_code, item_name, priority, value_text, unit, status,
              normal_range, method, meaning, maintenance, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inspection_id,
                item["code"],
                item["name"],
                item["priority"],
                item["value"],
                item.get("unit", ""),
                item["status"],
                item["normalRange"],
                item["method"],
                item["meaning"],
                item["maintenance"],
                now(),
            ),
        )


@app.post("/inspections")
def create_inspection(req: InspectionCreateReq, authorization: Optional[str] = Header(None)):
    current_user = get_current_user(authorization)
    with db() as conn:
        user_onboarding = onboarding_status(conn, current_user["id"])
        if user_onboarding["required"]:
            raise HTTPException(status_code=403, detail=user_onboarding["message"])
        if not user_onboarding.get("canInspect", False):
            raise HTTPException(status_code=403, detail=user_onboarding["message"])
        active_binding = user_onboarding.get("binding") or {}
        if int(active_binding.get("boilerId") or 0) != int(req.boilerId) or int(active_binding.get("materialPackId") or 0) != int(req.materialPackId):
            raise HTTPException(status_code=403, detail="当前用户未绑定所选锅炉和材料包")
        boiler = row_to_dict(conn.execute("SELECT * FROM boilers WHERE id = ?", (req.boilerId,)).fetchone())
        if not boiler:
            raise HTTPException(status_code=404, detail="锅炉不存在")
        pack = row_to_dict(conn.execute("SELECT * FROM material_packs WHERE id = ?", (req.materialPackId,)).fetchone())
        if not pack:
            raise HTTPException(status_code=404, detail="检测包不存在")
        if pack["status"] != "activated":
            raise HTTPException(status_code=400, detail="检测包尚未激活或已不可用")
        if int(pack["enterprise_id"]) != int(boiler["enterprise_id"]):
            raise HTTPException(status_code=400, detail="检测包和锅炉不属于同一企业")
        if not pack["boiler_id"]:
            raise HTTPException(status_code=400, detail="检测包尚未绑定锅炉")
        if int(pack["boiler_id"]) != int(req.boilerId):
            raise HTTPException(status_code=400, detail="检测包未绑定当前锅炉")
        if req.retestTaskId:
            task = row_to_dict(conn.execute("SELECT * FROM retest_tasks WHERE id = ?", (req.retestTaskId,)).fetchone())
            if not task:
                raise HTTPException(status_code=404, detail="复测任务不存在")
            if task["boiler_id"] and int(task["boiler_id"]) != int(req.boilerId):
                raise HTTPException(status_code=400, detail="复测任务与所选锅炉不一致")
        cur = conn.execute(
            """
            INSERT INTO inspections(
              enterprise_id, boiler_id, material_pack_id, inspection_type, retest_task_id,
              inspector_user_id, inspector_name, status, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, 'created', ?)
            """,
            (
                boiler["enterprise_id"],
                req.boilerId,
                req.materialPackId,
                req.inspectionType,
                req.retestTaskId,
                current_user.get("id"),
                current_user.get("name") or current_user.get("username"),
                now(),
            ),
        )
        return {"inspectionId": cur.lastrowid, "boilerId": req.boilerId, "materialPackId": req.materialPackId, "status": "created"}


@app.post("/inspections/create")
def create_inspection_alias(req: InspectionCreateReq, authorization: Optional[str] = Header(None)):
    return create_inspection(req, authorization)


@app.post("/inspections/{inspection_id}/upload")
async def upload_by_path(inspection_id: int, file: UploadFile = File(...)):
    return await save_upload(inspection_id, file)


@app.post("/inspections/upload-image")
async def upload_image(inspectionId: int = Form(...), file: UploadFile = File(...)):
    return await save_upload(inspectionId, file)


async def save_upload(inspection_id: int, file: UploadFile):
    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"
    target = UPLOAD_DIR / f"inspection-{inspection_id}-{int(datetime.utcnow().timestamp())}{suffix}"
    content = await file.read()
    target.write_bytes(content)
    image_url = f"/uploads/{target.name}"
    with db() as conn:
        cur = conn.execute(
            "UPDATE inspections SET image_url = ?, status = 'uploaded' WHERE id = ?",
            (image_url, inspection_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="inspection not found")
    return {"success": True, "inspectionId": inspection_id, "imageUrl": image_url}


@app.get("/uploads/{filename}")
def get_upload(filename: str):
    path = UPLOAD_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path)


@app.post("/inspections/recognize")
def recognize(req: RecognizeReq):
    with db() as conn:
        result = inspection_result_payload(req.inspectionId, conn, req.values)
        cur = conn.execute(
            """
            UPDATE inspections
            SET status = 'done', score = ?, summary = ?, result_json = ?
            WHERE id = ?
            """,
            (result["score"], result["summary"], json.dumps(result, ensure_ascii=False), req.inspectionId),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="inspection not found")
        save_inspection_test_results(conn, req.inspectionId, result["items"])
        create_retest_tasks_from_result(conn, result)
        backfill_retest_result(conn, req.inspectionId)
    return {"inspectionId": req.inspectionId, "status": "done", "result": result}


@app.get("/inspections/result")
def get_result(inspectionId: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM inspections WHERE id = ?", (inspectionId,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="inspection not found")
    if row["result_json"]:
        payload = json.loads(row["result_json"])
    else:
        payload = {"inspectionId": inspectionId, "status": row["status"], "items": [], "diagnosis": []}
    payload["imageUrl"] = row["image_url"]
    payload["remark"] = row["remark"]
    payload["submittedAt"] = row["submitted_at"]
    payload["inspectorUserId"] = row["inspector_user_id"]
    payload["inspectorName"] = row["inspector_name"]
    return payload


@app.post("/inspections/submit")
def submit_inspection(req: SubmitReq):
    with db() as conn:
        cur = conn.execute(
            "UPDATE inspections SET status = 'submitted', remark = ?, submitted_at = ? WHERE id = ?",
            (req.remark or "", now(), req.inspectionId),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="inspection not found")
    return {"inspectionId": req.inspectionId, "status": "submitted"}


@app.get("/retest-tasks")
def list_retest_tasks(enterpriseId: int = 1, status: str = "pending"):
    with db() as conn:
        filters = ["enterprise_id = ?"]
        params = [enterpriseId]
        if status and status != "all":
            filters.append("status = ?")
            params.append(status)
        rows = conn.execute(
            f"""
            SELECT *
            FROM retest_tasks
            WHERE {' AND '.join(filters)}
            ORDER BY id DESC
            """,
            tuple(params),
        )
        return [retest_task_to_dict(row) for row in rows]


@app.post("/retest-tasks/{task_id}/complete")
def complete_retest_task(task_id: int, req: CompleteRetestTaskReq = CompleteRetestTaskReq()):
    with db() as conn:
        cur = conn.execute(
            """
            UPDATE retest_tasks
            SET status = 'done', resolution_type = COALESCE(resolution_type, 'manual_complete'),
                resolution_note = ?, resolved_at = COALESCE(resolved_at, ?), completed_at = ?
            WHERE id = ?
            """,
            (req.remark or "人工标记完成", now(), now(), task_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="retest task not found")
    return {"id": task_id, "status": "done"}


@app.post("/retest-tasks/{task_id}/resolve")
def resolve_retest_task(task_id: int, req: RetestResolutionReq):
    allowed = {"retest", "no_retest", "manual_complete"}
    if req.resolutionType not in allowed:
        raise HTTPException(status_code=400, detail="resolutionType不合法")
    status = "retested" if req.resolutionType == "retest" else "no_retest" if req.resolutionType == "no_retest" else "done"
    with db() as conn:
        cur = conn.execute(
            """
            UPDATE retest_tasks
            SET status = ?, resolution_type = ?, resolution_note = ?, retest_inspection_id = ?,
                resolved_at = ?, completed_at = CASE WHEN ? IN ('no_retest', 'manual_complete') THEN ? ELSE completed_at END
            WHERE id = ?
            """,
            (status, req.resolutionType, req.note or "", req.retestInspectionId, now(), req.resolutionType, now(), task_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="retest task not found")
    return {"id": task_id, "status": status, "resolutionType": req.resolutionType}


@app.post("/retest-tasks/{task_id}/service-advice")
def save_retest_service_advice(task_id: int, req: RetestServiceAdviceReq, authorization: Optional[str] = Header(None)):
    current_user = require_roles(authorization, ("platform_admin", "enterprise_admin"))
    with db() as conn:
        row = row_to_dict(conn.execute("SELECT enterprise_id FROM retest_tasks WHERE id = ?", (task_id,)).fetchone())
        if not row:
            raise HTTPException(status_code=404, detail="retest task not found")
        ensure_enterprise_scope(current_user, row["enterprise_id"])
        cur = conn.execute(
            """
            UPDATE retest_tasks
            SET service_advice = ?, service_by = ?, service_by_name = ?, service_at = ?
            WHERE id = ?
            """,
            (req.serviceAdvice.strip(), current_user.get("id"), current_user.get("name") or current_user.get("username"), now(), task_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="retest task not found")
    return {"id": task_id, "serviceAdvice": req.serviceAdvice.strip(), "serviceByName": current_user.get("name") or current_user.get("username")}


@app.get("/inspections")
def list_inspections(status: Optional[str] = None, boilerId: Optional[int] = None):
    with db() as conn:
        filters = []
        params = []
        if status:
            filters.append("i.status = ?")
            params.append(status)
        if boilerId:
            filters.append("i.boiler_id = ?")
            params.append(boilerId)
        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""
        rows = conn.execute(
            f"""
            SELECT i.id AS inspectionId, i.boiler_id AS boilerId, b.name AS boilerName,
                   i.material_pack_id AS materialPackId, i.status, i.score, i.summary,
                   i.image_url AS imageUrl, i.result_json AS resultJson, i.created_at AS createdAt,
                   i.inspector_user_id AS inspectorUserId, i.inspector_name AS inspectorName
            FROM inspections i
            LEFT JOIN boilers b ON b.id = i.boiler_id
            {where_clause}
            ORDER BY i.id DESC
            """,
            tuple(params),
        )
        result = []
        for row in rows:
            item = row_to_dict(row)
            item["result"] = json.loads(item.pop("resultJson")) if item.get("resultJson") else {}
            result.append(item)
        return result


@app.get("/records/{inspection_id}")
def record_detail(inspection_id: int):
    return get_result(inspection_id)


@app.get("/record-detail")
def record_detail_alias(id: int):
    return get_result(id)


@app.get("/reports/monthly")
def monthly_report(enterpriseId: int = 1, month: str = "2026-07"):
    with db() as conn:
        rows = conn.execute("SELECT status, score FROM inspections WHERE enterprise_id = ?", (enterpriseId,)).fetchall()
        boiler_count = conn.execute("SELECT COUNT(*) AS c FROM boilers WHERE enterprise_id = ?", (enterpriseId,)).fetchone()["c"]
    total = len(rows)
    abnormal = sum(1 for row in rows if (row["score"] or 100) < 90)
    avg = round(sum((row["score"] or 86) for row in rows) / total) if total else 86
    return {
        "enterpriseId": enterpriseId,
        "month": month,
        "score": avg,
        "inspectionCount": total,
        "abnormalCount": abnormal,
        "boilerCount": boiler_count,
    }
