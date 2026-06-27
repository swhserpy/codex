"""Server Console — Backend API"""

import datetime
import json
import os
import platform
import subprocess
import time
from pathlib import Path

import httpx
import psutil
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from config import (
    SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES,
    ADMIN_USERNAME, ADMIN_PASSWORD,
    LOG_FILES, TASK_SCRIPTS,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
)

# ── App ──────────────────────────────────────────────
app = FastAPI(title="Server Console", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ── Auth ──────────────────────────────────────────────
def create_token():
    from jose import jwt
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": ADMIN_USERNAME, "exp": expire}, SECRET_KEY, algorithm="HS256")

def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=["HS256"])
        if payload.get("sub") != ADMIN_USERNAME:
            raise HTTPException(401, "Invalid token")
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid token")

# ── Models ───────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str

class TaskRunRequest(BaseModel):
    task_key: str

class LogRequest(BaseModel):
    log_key: str

class TelegramNotifyRequest(BaseModel):
    message: str

# ── Routes ──────────────────────────────────────────

@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    if req.username != ADMIN_USERNAME or req.password != ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid credentials")
    return LoginResponse(token=create_token())


@app.get("/api/system")
def system(_=Depends(verify_token)):
    boot_ts = psutil.boot_time()
    disk = psutil.disk_usage("/")
    mem = psutil.virtual_memory()
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_count": psutil.cpu_count(),
        "memory_total": mem.total,
        "memory_used": mem.used,
        "memory_percent": round(mem.percent, 1),
        "disk_total": disk.total,
        "disk_used": disk.used,
        "disk_percent": disk.percent,
        "uptime_seconds": int(time.time() - boot_ts),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "load_1m": round(load[0], 2),
        "load_5m": round(load[1], 2),
        "load_15m": round(load[2], 2),
        "timestamp": datetime.datetime.now().isoformat(),
    }


@app.get("/api/services")
def services(_=Depends(verify_token)):
    try:
        r = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=15,
        )
        lines = [json.loads(l) for l in r.stdout.strip().split("\n") if l.strip()]
        return {"containers": lines}
    except FileNotFoundError:
        return {"containers": [], "error": "Docker not installed"}
    except Exception as e:
        return {"containers": [], "error": str(e)}


@app.get("/api/logs")
def logs(log_key: str, _=Depends(verify_token)):
    path_str = LOG_FILES.get(log_key)
    if not path_str:
        raise HTTPException(400, f"Invalid log key. Available: {list(LOG_FILES.keys())}")
    
    path = Path(path_str)
    if not path.exists():
        raise HTTPException(404, f"Log file not found: {path_str}")
    
    try:
        r = subprocess.run(
            ["tail", "-n", "100", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        lines = r.stdout.split("\n")
        return {"file": path_str, "lines": lines, "total": len(lines)}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/tasks")
def list_tasks(_=Depends(verify_token)):
    available = {}
    for key, path in TASK_SCRIPTS.items():
        p = Path(path)
        available[key] = {
            "path": str(p),
            "exists": p.exists(),
            "executable": os.access(p, os.X_OK) if p.exists() else False,
        }
    return {"tasks": available}


@app.post("/api/tasks/run")
def run_task(req: TaskRunRequest, _=Depends(verify_token)):
    path_str = TASK_SCRIPTS.get(req.task_key)
    if not path_str:
        raise HTTPException(400, f"Unknown task. Available: {list(TASK_SCRIPTS.keys())}")
    
    path = Path(path_str)
    if not path.exists():
        raise HTTPException(404, f"Script not found: {path_str}")
    if not os.access(path, os.X_OK):
        raise HTTPException(400, f"Script not executable: {path_str}")
    
    try:
        r = subprocess.run(
            ["bash", str(path)],
            capture_output=True, text=True, timeout=120,
        )
        return {
            "task": req.task_key,
            "script": path_str,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "return_code": r.returncode,
            "success": r.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Script execution timed out")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/telegram/test")
def telegram_test(req: TelegramNotifyRequest, _=Depends(verify_token)):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise HTTPException(400, "Telegram not configured (missing token or chat_id)")
    
    try:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"🔔 Server Console Test\n\n{req.message}",
            "parse_mode": "Markdown",
        }
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload)
        return {"ok": resp.status_code == 200, "response": resp.json()}
    except Exception as e:
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
