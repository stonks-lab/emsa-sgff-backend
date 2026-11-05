import hashlib, datetime, os, json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import jwt

SECRET_KEY = os.getenv("JWT_SECRET", "tablero-emsa-key-2024")
ALGORITHM  = "HS256"
EXPIRY_HRS = 8

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer()

USERS_PATH = Path(__file__).resolve().parent.parent.parent / "users.json"


def _load_users() -> list[dict]:
    if not USERS_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="No existe users.json en la raíz del backend. Ver README, sección Usuarios.",
        )
    with open(USERS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: list[dict]) -> None:
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _decode_token(credentials: HTTPAuthorizationCredentials) -> dict:
    try:
        return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    payload = _decode_token(credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    return payload


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(req: LoginRequest):
    users = _load_users()
    user  = next((u for u in users if u["username"] == req.username), None)
    if not user or user["password_hash"] != _hash(req.password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=EXPIRY_HRS)
    token = jwt.encode(
        {"sub": user["username"], "name": user["name"], "role": user["role"], "exp": exp},
        SECRET_KEY, algorithm=ALGORITHM,
    )
    return {
        "token": token,
        "user":  {"username": user["username"], "name": user["name"], "role": user["role"]},
    }


@router.get("/me")
def me(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    payload = _decode_token(credentials)
    return {"username": payload["sub"], "name": payload["name"], "role": payload["role"]}


# ── CRUD usuarios (solo admin) ────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    name: str
    role: str
    password: str


class UserUpdate(BaseModel):
    name:     Optional[str] = None
    role:     Optional[str] = None
    password: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.put("/password")
def change_password(
    body: ChangePasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    payload  = _decode_token(credentials)
    username = payload["sub"]
    users    = _load_users()
    user     = next((u for u in users if u["username"] == username), None)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user["password_hash"] != _hash(body.current_password):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    user["password_hash"] = _hash(body.new_password)
    _save_users(users)
    return {"ok": True}


@router.get("/users")
def list_users(_: dict = Depends(_require_admin)):
    users = _load_users()
    return [{"username": u["username"], "name": u["name"], "role": u["role"]} for u in users]


@router.post("/users", status_code=201)
def create_user(body: UserCreate, _: dict = Depends(_require_admin)):
    users = _load_users()
    if any(u["username"] == body.username for u in users):
        raise HTTPException(status_code=409, detail="El usuario ya existe")
    users.append({
        "username":      body.username,
        "name":          body.name,
        "role":          body.role,
        "password_hash": _hash(body.password),
    })
    _save_users(users)
    return {"username": body.username, "name": body.name, "role": body.role}


@router.put("/users/{username}")
def update_user(username: str, body: UserUpdate, _: dict = Depends(_require_admin)):
    users = _load_users()
    user  = next((u for u in users if u["username"] == username), None)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if body.name     is not None: user["name"]          = body.name
    if body.role     is not None: user["role"]          = body.role
    if body.password is not None: user["password_hash"] = _hash(body.password)
    _save_users(users)
    return {"username": user["username"], "name": user["name"], "role": user["role"]}


@router.delete("/users/{username}", status_code=204)
def delete_user(username: str, admin: dict = Depends(_require_admin)):
    if username == admin["sub"]:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    users = _load_users()
    new   = [u for u in users if u["username"] != username]
    if len(new) == len(users):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    _save_users(new)
