import base64
import json
import os
import sqlite3
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


def make_token(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def parse_token(authorization: Optional[str]) -> dict:
    if not authorization:
        return {}
    token = authorization.replace("Bearer ", "").strip()
    try:
        padded = token + "=" * (-len(token) % 4)
        return json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")))
    except Exception:
        return {}


def seed_data(conn) -> None:
    conn.execute(
        "INSERT IGNORE INTO enterprises(id, name, code, created_at) VALUES(1, '华能示范工厂', 'HN-DEMO', ?)"
        if DB_DRIVER == "mysql"
        else "INSERT OR IGNORE INTO enterprises(id, name, code, created_at) VALUES(1, '华能示范工厂', 'HN-DEMO', ?)",
        (now(),),
    )
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
            CREATE TABLE IF NOT EXISTS inspections (
              id INTEGER PRIMARY KEY,
              enterprise_id INTEGER NOT NULL,
              boiler_id INTEGER NOT NULL,
              material_pack_id INTEGER NOT NULL,
              inspection_type TEXT NOT NULL DEFAULT 'daily',
              image_url TEXT,
              status TEXT NOT NULL DEFAULT 'created',
              score INTEGER,
              summary TEXT,
              result_json TEXT,
              remark TEXT,
              created_at TEXT NOT NULL,
              submitted_at TEXT
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


class AdminLoginReq(BaseModel):
    username: str
    password: str


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


class InspectionCreateReq(BaseModel):
    boilerId: int
    materialPackId: int
    inspectionType: str = "daily"


class RecognizeReq(BaseModel):
    inspectionId: int


class SubmitReq(BaseModel):
    inspectionId: int
    remark: Optional[str] = ""


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "lubaobao-api",
        "version": app.version,
        "rbac": True,
        "features": ["pack-management", "image-upload", "inspection-submit", "record-detail"],
    }


@app.get("/health")
def health():
    return {"ok": True, "service": "lubaobao-api"}


@app.post("/auth/wx-login")
def wx_login(req: WxLoginReq):
    user = {"id": 1, "username": "wx_user", "name": "测试用户", "role": "inspector", "enterpriseId": 1}
    enterprise = {"id": 1, "name": "华能示范工厂"}
    return {"token": make_token(user), "user": user, "enterprise": enterprise}


@app.post("/auth/admin-login")
def admin_login(req: AdminLoginReq):
    accounts = {
        "admin": ("Admin@123", "platform_admin", "平台管理员"),
        "entadmin": ("Ent@123", "enterprise_admin", "企业管理员"),
        "inspector": ("Inspect@123", "inspector", "巡检员"),
    }
    matched = accounts.get(req.username)
    if not matched or matched[0] != req.password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user = {"id": 7477, "username": req.username, "name": matched[2], "role": matched[1], "enterpriseId": 1}
    return {"token": make_token(user), "user": user}


@app.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(None)):
    user = parse_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return {"user": user}


@app.get("/users")
def users():
    return [
        {"id": 7477, "username": "admin", "name": "平台管理员", "role": "platform_admin", "enterpriseId": 1},
        {"id": 7478, "username": "entadmin", "name": "企业管理员", "role": "enterprise_admin", "enterpriseId": 1},
        {"id": 7479, "username": "inspector", "name": "巡检员", "role": "inspector", "enterpriseId": 1},
    ]


@app.get("/enterprises")
def enterprises():
    with db() as conn:
        return [row_to_dict(row) for row in conn.execute("SELECT id, name, code, status FROM enterprises ORDER BY id")]


@app.get("/boilers")
def boilers(enterpriseId: int = 1):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, enterprise_id AS enterpriseId, name, device_code AS deviceCode,
                   product_no AS productNo, model, device_type AS deviceType, status
            FROM boilers WHERE enterprise_id = ? ORDER BY id
            """,
            (enterpriseId,),
        )
        return [row_to_dict(row) for row in rows]


@app.post("/boilers")
def create_boiler(req: BoilerCreateReq):
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


@app.get("/material-packs")
def list_packs(enterpriseId: int = 1):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, enterprise_id AS enterpriseId, code, type, status, boiler_id AS boilerId, expire_at AS expireAt
            FROM material_packs WHERE enterprise_id = ? ORDER BY id DESC
            """,
            (enterpriseId,),
        )
        return [row_to_dict(row) for row in rows]


@app.post("/material-packs")
def create_pack(req: PackCreateReq):
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
        pack = row_to_dict(conn.execute("SELECT * FROM material_packs WHERE code = ?", (req.code,)).fetchone())
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
            "status": pack["status"],
            "type": pack["type"],
            "expireAt": pack["expire_at"],
        },
    }


@app.post("/material-packs/activate")
def activate_pack(req: PackActivateReq):
    with db() as conn:
        pack = conn.execute("SELECT * FROM material_packs WHERE code = ?", (req.code,)).fetchone()
        if not pack:
            raise HTTPException(status_code=404, detail="检测包不存在")
        conn.execute(
            """
            UPDATE material_packs
            SET status = 'activated', boiler_id = COALESCE(?, boiler_id), enterprise_id = COALESCE(?, enterprise_id), activated_at = ?
            WHERE code = ?
            """,
            (req.boilerId, req.enterpriseId, now(), req.code),
        )
        updated = row_to_dict(conn.execute("SELECT * FROM material_packs WHERE code = ?", (req.code,)).fetchone())
    return {"id": updated["id"], "code": updated["code"], "enterpriseId": updated["enterprise_id"], "status": updated["status"]}


@app.post("/material-packs/invalidate")
def invalidate_pack(req: PackCodeReq):
    with db() as conn:
        cur = conn.execute("UPDATE material_packs SET status = 'invalid' WHERE code = ?", (req.code,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="检测包不存在")
    return {"code": req.code, "status": "invalid"}


@app.post("/material-packs/unbind")
def unbind_pack(req: PackCodeReq):
    with db() as conn:
        cur = conn.execute(
            "UPDATE material_packs SET boiler_id = NULL, status = 'activated' WHERE code = ?",
            (req.code,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="检测包不存在")
    return {"code": req.code, "status": "activated", "boilerId": None}


def inspection_result_payload(inspection_id: int) -> dict:
    items = [
        {"name": "pH", "value": "8.1", "status": "warning", "normalRange": "8.5-10.5"},
        {"name": "硬度", "value": "0.05", "status": "normal", "normalRange": "≤0.03"},
    ]
    return {
        "inspectionId": inspection_id,
        "score": 86,
        "status": "done",
        "summary": "pH偏低，建议补加药剂",
        "items": items,
        "diagnosis": ["补加药剂", "复测确认"],
    }


@app.post("/inspections")
def create_inspection(req: InspectionCreateReq):
    with db() as conn:
        boiler = conn.execute("SELECT * FROM boilers WHERE id = ?", (req.boilerId,)).fetchone()
        if not boiler:
            raise HTTPException(status_code=404, detail="锅炉不存在")
        pack = conn.execute("SELECT * FROM material_packs WHERE id = ?", (req.materialPackId,)).fetchone()
        if not pack:
            raise HTTPException(status_code=404, detail="检测包不存在")
        cur = conn.execute(
            """
            INSERT INTO inspections(enterprise_id, boiler_id, material_pack_id, inspection_type, status, created_at)
            VALUES(?, ?, ?, ?, 'created', ?)
            """,
            (boiler["enterprise_id"], req.boilerId, req.materialPackId, req.inspectionType, now()),
        )
        return {"inspectionId": cur.lastrowid, "boilerId": req.boilerId, "materialPackId": req.materialPackId, "status": "created"}


@app.post("/inspections/create")
def create_inspection_alias(req: InspectionCreateReq):
    return create_inspection(req)


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
    result = inspection_result_payload(req.inspectionId)
    with db() as conn:
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
                   i.image_url AS imageUrl, i.result_json AS resultJson, i.created_at AS createdAt
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
