from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import QueuePool
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta, date
from passlib.context import CryptContext
from jose import JWTError, jwt
import httpx
import aiofiles
from PIL import Image
import asyncio
import json
import enum
from zoneinfo import ZoneInfo

# Sri Lanka timezone (Asia/Colombo = UTC+5:30)
SL_TZ = ZoneInfo("Asia/Colombo")

def now_sl():
    """Get current time in Sri Lanka timezone, returned as naive datetime for MySQL storage."""
    return datetime.now(SL_TZ).replace(tzinfo=None)

def to_sl_naive(dt) -> datetime:
    """
    Convert any datetime to a naive SL datetime suitable for MySQL storage.
    - If dt is timezone-aware (e.g. UTC+00:00 from frontend), convert to SL time then strip tz.
    - If dt is already naive, assume it is already in SL time and return as-is.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert from whatever timezone (typically UTC from frontend) to SL, then strip
        return dt.astimezone(SL_TZ).replace(tzinfo=None)
    # Already naive, assume SL time
    return dt

def to_sl_iso(dt):
    """Convert a naive datetime (assumed SL time) to ISO string."""
    if dt is None:
        return None
    return dt.isoformat()

import subprocess

ROOT_DIR = Path(__file__).parent

# Load environment-specific .env file.
# Set ENV=production in your shell or system environment on the server.
# Locally, ENV defaults to "development".
_env = os.environ.get("ENV", "development")
_env_file = ROOT_DIR / f".env.{_env}"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv(ROOT_DIR / ".env")


# MySQL Configuration
MYSQL_URL = os.environ.get('MYSQL_URL', 'mysql+pymysql://root:Qwerty123@localhost/zomoto_tasks?unix_socket=/run/mysqld/mysqld.sock')
engine = create_engine(MYSQL_URL, pool_size=10, max_overflow=20, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'zomoto-tasks-secret-key-2024')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# notify.lk Configuration
NOTIFY_LK_USER_ID = os.environ.get('NOTIFY_LK_USER_ID', '28528')
NOTIFY_LK_API_KEY = os.environ.get('NOTIFY_LK_API_KEY', 'JeP7ACSaYTSwOY5eCl6S')
NOTIFY_LK_SENDER_ID = os.environ.get('NOTIFY_LK_SENDER_ID', 'Zeeha HLD')

# FCM Configuration
FCM_SERVER_KEY = os.environ.get('FCM_SERVER_KEY')

async def send_fcm_notification(token: str, title: str, body: str):
    if not token:
        return
    try:
        import google.auth.transport.requests
        import google.oauth2.service_account
        
        SERVICE_ACCOUNT_FILE = ROOT_DIR / "firebase-service-account.json"
        SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]
        
        credentials = google.oauth2.service_account.Credentials.from_service_account_file(
            str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
        )
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        access_token = credentials.token
        
        # Get project ID from service account file
        with open(SERVICE_ACCOUNT_FILE) as f:
            sa_data = json.load(f)
        project_id = sa_data["project_id"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "message": {
                        "token": token,
                        "notification": {
                            "title": title,
                            "body": body
                        },
                        "webpush": {
                            "notification": {
                                "icon": "/logo192.png",
                                "click_action": "https://task.zomoto.lk"
                            }
                        }
                    }
                }
            )
            logger.info(f"FCM response: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"FCM notification error: {e}")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI(title="Zomoto Tasks API", version="3.0.0")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===================== ENUMS ====================
class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    SUPERVISOR = "SUPERVISOR"
    STAFF = "STAFF"

class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NOT_COMPLETED = "NOT_COMPLETED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class TaskPriority(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class TaskType(str, enum.Enum):
    INSTANT = "INSTANT"
    RECURRING = "RECURRING"

class TimeUnit(str, enum.Enum):
    MINUTES = "MINUTES"
    HOURS = "HOURS"

# ===================== SQLAlchemy MODELS =====================
class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50))
    role = Column(String(20), default="STAFF")
    status = Column(String(20), default="ACTIVE")
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=now_sl)
    updated_at = Column(DateTime, default=now_sl, onupdate=now_sl)

class Category(Base):
    __tablename__ = "categories"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    color = Column(String(50), default="#6B7280")
    created_at = Column(DateTime, default=now_sl)

class TaskTemplate(Base):
    __tablename__ = "task_templates"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(255))
    priority = Column(String(20), default="MEDIUM")
    time_interval = Column(Integer, default=30)
    time_unit = Column(String(20), default="MINUTES")
    is_recurring = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    day_intervals = Column(String(255))
    allocated_time = Column(String(10))  # "HH:MM" in SL time
    assigned_to = Column(String(36), ForeignKey("users.id"))
    assigned_to_name = Column(String(255))
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=now_sl)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(255))
    priority = Column(String(20), default="MEDIUM")
    status = Column(String(20), default="PENDING", index=True)
    task_type = Column(String(20), default="INSTANT")
    time_interval = Column(Integer, default=30)
    time_unit = Column(String(20), default="MINUTES")
    allocated_datetime = Column(DateTime)   # naive SL time
    deadline = Column(DateTime)             # naive SL time
    recurrence_pattern = Column(String(50))
    recurrence_intervals = Column(JSON)
    proof_photos = Column(JSON, default=list)
    attachments = Column(JSON, default=list)
    assigned_to = Column(String(36), ForeignKey("users.id"), index=True)
    assigned_to_name = Column(String(255))
    created_by = Column(String(36), ForeignKey("users.id"))
    created_by_name = Column(String(255))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    verified_at = Column(DateTime)
    supervisor_verified_at    = Column(DateTime(timezone=True), nullable=True)
    supervisor_verified_by    = Column(String, ForeignKey("users.id"), nullable=True)
    verified_by               = Column(String, ForeignKey("users.id"), nullable=True)
    is_deleted = Column(Boolean, default=False, index=True)
    is_overdue = Column(Boolean, default=False)
    is_notified = Column(Boolean, default=False)
    rejection_reason = Column(Text, nullable=True)
    is_late = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False, index=True)
    archived_at = Column(DateTime)
    actual_time_taken = Column(Integer)
    parent_task_id = Column(String(36))
    template_id = Column(String(36))
    created_at = Column(DateTime, default=now_sl, index=True)
    updated_at = Column(DateTime, default=now_sl, onupdate=now_sl)

class TaskComment(Base):
    __tablename__ = "task_comments"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    user_name = Column(String(255))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now_sl)

class TaskActivityLog(Base):
    __tablename__ = "task_activity_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    user_name = Column(String(255))
    action = Column(String(100), nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, default=now_sl)

class FCMToken(Base):
    __tablename__ = "fcm_tokens"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    token = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now_sl)
    updated_at = Column(DateTime, default=now_sl, onupdate=now_sl)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    task_id = Column(String(36))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now_sl)

Base.metadata.create_all(bind=engine)

# ===================== PYDANTIC SCHEMAS =====================
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = "STAFF"
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "Other"
    priority: str = "MEDIUM"
    task_type: str = "INSTANT"
    time_interval: int = 30
    time_unit: str = "MINUTES"
    allocated_datetime: Optional[datetime] = None
    recurrence_pattern: Optional[str] = None
    recurrence_intervals: Optional[List[int]] = None
    assigned_to: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    time_interval: Optional[int] = None
    time_unit: Optional[str] = None
    allocated_datetime: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    status: str
    task_type: str
    time_interval: int
    time_unit: str
    allocated_datetime: Optional[datetime] = None
    deadline: Optional[datetime] = None
    recurrence_pattern: Optional[str] = None
    recurrence_intervals: Optional[List[int]] = None
    proof_photos: List[str] = []
    attachments: List[str] = []
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class CategoryCreate(BaseModel):
    name: str
    color: str = "#6B7280"

class CategoryResponse(BaseModel):
    id: str
    name: str
    color: str
    created_at: datetime
    class Config:
        from_attributes = True

class TemplateCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "Other"
    priority: str = "MEDIUM"
    time_interval: int = 30
    time_unit: str = "MINUTES"
    is_recurring: bool = False
    day_intervals: Optional[str] = None
    allocated_time: Optional[str] = None  # "HH:MM" in SL time
    assigned_to: Optional[str] = None

class TemplateUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    time_interval: Optional[int] = None
    time_unit: Optional[str] = None
    is_recurring: Optional[bool] = None
    is_active: Optional[bool] = None
    day_intervals: Optional[str] = None
    allocated_time: Optional[str] = None
    assigned_to: Optional[str] = None

class TemplateResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    time_interval: int
    time_unit: str
    is_recurring: bool = False
    is_active: bool = True
    day_intervals: Optional[str] = None
    allocated_time: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    content: str

class BulkDeleteRequest(BaseModel):
    task_ids: List[str]

class CommentResponse(BaseModel):
    id: str
    task_id: str
    user_id: str
    user_name: str
    content: str
    created_at: datetime
    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: Optional[str] = None
    task_id: Optional[str] = None
    is_read: bool
    created_at: datetime
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_tasks: int
    in_progress: int
    completed: int
    verified: int
    tasks_to_assign: int
    tasks_to_verify: int
    staff_count: int

# ===================== DATABASE DEPENDENCY =====================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===================== WEBSOCKET MANAGER =====================
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast_to_user(self, user_id: str, message: dict):
        if user_id not in self.active_connections:
            return False
        connections = self.active_connections[user_id][:]
        sent_count = 0
        dead_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send to user {user_id}: {e}")
                dead_connections.append(connection)
        for dead in dead_connections:
            if dead in self.active_connections.get(user_id, []):
                self.active_connections[user_id].remove(dead)
        if user_id in self.active_connections and not self.active_connections[user_id]:
            del self.active_connections[user_id]
        return sent_count > 0

    async def broadcast_to_all(self, message: dict):
        total_sent = 0
        dead_connections = []
        for user_id, connections in list(self.active_connections.items()):
            for connection in connections[:]:
                try:
                    await connection.send_json(message)
                    total_sent += 1
                except Exception as e:
                    logger.error(f"Failed to broadcast to user {user_id}: {e}")
                    dead_connections.append((user_id, connection))
        for user_id, dead in dead_connections:
            if dead in self.active_connections.get(user_id, []):
                self.active_connections[user_id].remove(dead)
        for user_id in list(self.active_connections.keys()):
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"Broadcast to all: sent to {total_sent} connections")

manager = ConnectionManager()

# ===================== HELPER FUNCTIONS =====================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = now_sl() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def calculate_deadline(allocated_dt: datetime, time_interval: int, time_unit: str) -> datetime:
    """Calculate deadline. Both input and output are naive SL datetimes."""
    unit = (time_unit or "MINUTES").upper()
    if unit == "HOURS":
        return allocated_dt + timedelta(hours=time_interval)
    return allocated_dt + timedelta(minutes=time_interval)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

async def create_notification(db: Session, user_id: str, type: str, title: str, message: str, task_id: str = None):
    notification = Notification(user_id=user_id, type=type, title=title, message=message, task_id=task_id)
    db.add(notification)
    db.commit()
    await manager.broadcast_to_user(user_id, {
        "type": "notification",
        "data": {
            "id": notification.id,
            "type": type,
            "title": title,
            "message": message,
            "task_id": task_id,
            "is_read": False,
            "created_at": notification.created_at.isoformat()
        }
    })

def create_activity_log(db: Session, task_id: str, user_id: str, user_name: str, action: str, details: str = None):
    log = TaskActivityLog(task_id=task_id, user_id=user_id, user_name=user_name, action=action, details=details)
    db.add(log)
    db.commit()

# ===================== AUTH ENDPOINTS =====================
@api_router.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Account is inactive")
    access_token = create_access_token(data={"sub": user.id, "role": user.role})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(id=user.id, name=user.name, email=user.email, phone=user.phone,
                          role=user.role, status=user.status, created_at=user.created_at)
    )

@api_router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=current_user.id, name=current_user.name, email=current_user.email,
                        phone=current_user.phone, role=current_user.role, status=current_user.status,
                        created_at=current_user.created_at)

# ===================== USER ENDPOINTS =====================
@api_router.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    users = db.query(User).all()
    return [UserResponse(id=u.id, name=u.name, email=u.email, phone=u.phone,
                         role=u.role, status=u.status, created_at=u.created_at) for u in users]

@api_router.get("/users/staff", response_model=List[UserResponse])
def get_staff(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).filter(User.role.in_(["STAFF", "MANAGER", "SUPERVISOR"]), User.status == "ACTIVE").all()
    return [UserResponse(id=u.id, name=u.name, email=u.email, phone=u.phone,
                         role=u.role, status=u.status, created_at=u.created_at) for u in users]

@api_router.post("/users", response_model=UserResponse)
def create_user(user_data: UserCreate, db: Session = Depends(get_db),
                current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(name=user_data.name, email=user_data.email, phone=user_data.phone,
                role=user_data.role, hashed_password=get_password_hash(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(id=user.id, name=user.name, email=user.email, phone=user.phone,
                        role=user.role, status=user.status, created_at=user.created_at)

@api_router.get("/users/subtask-staff", response_model=List[UserResponse])
def get_subtask_staff(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).filter(User.role.in_(["STAFF"]), User.status == "ACTIVE").all()
    return [UserResponse(id=u.id, name=u.name, email=u.email, phone=u.phone,
                         role=u.role, status=u.status, created_at=u.created_at) for u in users]

@api_router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: str, name: str = None, phone: str = None, role: str = None, status: str = None,
                db: Session = Depends(get_db), current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if name: user.name = name
    if phone: user.phone = phone
    if role: user.role = role
    if status: user.status = status
    db.commit()
    db.refresh(user)
    return UserResponse(id=user.id, name=user.name, email=user.email, phone=user.phone,
                        role=user.role, status=user.status, created_at=user.created_at)

@api_router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, new_password: str = "123456", db: Session = Depends(get_db),
                   current_user: User = Depends(require_roles(["OWNER"]))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"message": "Password reset successfully"}

# ===================== CATEGORY ENDPOINTS =====================
@api_router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    categories = db.query(Category).all()
    return [CategoryResponse(id=c.id, name=c.name, color=c.color, created_at=c.created_at) for c in categories]

@api_router.post("/categories", response_model=CategoryResponse)
def create_category(category_data: CategoryCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    category = Category(name=category_data.name, color=category_data.color)
    db.add(category)
    db.commit()
    db.refresh(category)
    return CategoryResponse(id=category.id, name=category.name, color=category.color, created_at=category.created_at)

@api_router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: str, name: str = None, color: str = None, db: Session = Depends(get_db),
                    current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if name: category.name = name
    if color: category.color = color
    db.commit()
    db.refresh(category)
    return CategoryResponse(id=category.id, name=category.name, color=category.color, created_at=category.created_at)

@api_router.delete("/categories/{category_id}")
def delete_category(category_id: str, db: Session = Depends(get_db),
                    current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.commit()
    return {"message": "Category deleted"}

# ===================== TASK TEMPLATE ENDPOINTS =====================
def template_to_response(t: TaskTemplate) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "category": t.category or "Other",
        "priority": t.priority or "MEDIUM",
        "time_interval": t.time_interval or 30,
        "time_unit": t.time_unit or "MINUTES",
        "is_recurring": t.is_recurring or False,
        "is_active": t.is_active if t.is_active is not None else True,
        "day_intervals": t.day_intervals,
        "allocated_time": t.allocated_time,
        "assigned_to": t.assigned_to,
        "assigned_to_name": t.assigned_to_name,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }

@api_router.get("/task-templates")
def get_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    templates = db.query(TaskTemplate).all()
    return [template_to_response(t) for t in templates]

@api_router.post("/task-templates")
def create_template(template_data: TemplateCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    assigned_to_name = None
    if template_data.assigned_to:
        staff = db.query(User).filter(User.id == template_data.assigned_to).first()
        if staff:
            assigned_to_name = staff.name
    template = TaskTemplate(
        title=template_data.title, description=template_data.description,
        category=template_data.category, priority=template_data.priority,
        time_interval=template_data.time_interval, time_unit=template_data.time_unit,
        is_recurring=template_data.is_recurring, day_intervals=template_data.day_intervals,
        allocated_time=template_data.allocated_time,  # stored as "HH:MM" SL time
        assigned_to=template_data.assigned_to, assigned_to_name=assigned_to_name,
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template_to_response(template)

@api_router.put("/task-templates/{template_id}")
def update_template(template_id: str, template_data: TemplateUpdate, db: Session = Depends(get_db),
                    current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    update_fields = template_data.dict(exclude_unset=True)
    if "assigned_to" in update_fields and update_fields["assigned_to"]:
        staff = db.query(User).filter(User.id == update_fields["assigned_to"]).first()
        if staff:
            template.assigned_to_name = staff.name
    for key, value in update_fields.items():
        if value is not None:
            setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return template_to_response(template)

@api_router.delete("/task-templates/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db),
                    current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return {"message": "Template deleted"}

def _build_task_from_template(tmpl: TaskTemplate, today, now: datetime) -> Task:
    """Helper: build a Task from a recurring template for today. All times are naive SL."""
    # allocated_time is "HH:MM" in SL time — combine with today's date
    if tmpl.allocated_time:
        try:
            hour, minute = map(int, tmpl.allocated_time.split(":"))
            allocated_dt = datetime.combine(today, datetime.min.time()).replace(hour=hour, minute=minute)
        except ValueError:
            allocated_dt = now
    else:
        allocated_dt = now

    interval = tmpl.time_interval or 30
    unit = (tmpl.time_unit or "MINUTES").upper()
    deadline = calculate_deadline(allocated_dt, interval, unit)

    date_str = today.strftime("%b %d")
    time_str = ""
    if tmpl.allocated_time:
        try:
            t = datetime.strptime(tmpl.allocated_time, "%H:%M")
            time_str = " " + t.strftime("%I:%M %p")
        except ValueError:
            pass
    task_title = f"{tmpl.title} ({date_str}{time_str})"

    return Task(
        title=task_title, description=tmpl.description, category=tmpl.category,
        priority=(tmpl.priority or "MEDIUM").upper(), status="PENDING",
        task_type="RECURRING", time_interval=interval, time_unit=unit,
        allocated_datetime=allocated_dt, deadline=deadline,
        assigned_to=tmpl.assigned_to, assigned_to_name=tmpl.assigned_to_name,
        created_by=tmpl.created_by, created_by_name="System", template_id=tmpl.id,
	is_notified=False,
    )

@api_router.post("/task-templates/generate-now")
async def generate_recurring_now(db: Session = Depends(get_db),
                                  current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    """Manually trigger recurring task generation for today."""
    now = now_sl()
    today = now.date()
    today_day = today.day
    generated = 0

    templates = db.query(TaskTemplate).filter(
        TaskTemplate.is_recurring == True,
        TaskTemplate.is_active == True
    ).all()

    for tmpl in templates:
        scheduled_days = parse_day_intervals(tmpl.day_intervals)
        if not scheduled_days or today_day not in scheduled_days:
            continue
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        existing = db.query(Task).filter(
            Task.template_id == tmpl.id,
            Task.created_at >= today_start,
            Task.created_at <= today_end,
            Task.is_deleted == False
        ).first()
        if existing:
            continue
        task = _build_task_from_template(tmpl, today, now)
        db.add(task)
        generated += 1

    db.commit()
    return {"message": f"Generated {generated} recurring tasks for today"}

# ===================== TASK ENDPOINTS =====================
def task_to_response(task: Task) -> dict:
    def fmt(dt):
        return dt.isoformat() if dt else None
    return {
        "id": task.id, "title": task.title, "description": task.description,
        "category": task.category, "priority": (task.priority or "MEDIUM").upper(),
        "status": (task.status or "PENDING").upper(), "task_type": (task.task_type or "INSTANT").upper(),
        "time_interval": task.time_interval or 0, "time_unit": (task.time_unit or "MINUTES").upper(),
        # These are naive SL datetimes — returned as ISO strings (no tz suffix).
        # Frontend should treat them as local SL time.
        "allocated_datetime": fmt(task.allocated_datetime),
        "deadline": fmt(task.deadline),
        "recurrence_pattern": task.recurrence_pattern,
        "recurrence_intervals": task.recurrence_intervals or [],
        "proof_photos": task.proof_photos or [], "attachments": task.attachments or [],
        "assigned_to": task.assigned_to, "assigned_to_name": task.assigned_to_name,
        "created_by": task.created_by, "created_by_name": task.created_by_name,
        "started_at": fmt(task.started_at), "completed_at": fmt(task.completed_at),
        "verified_at": fmt(task.verified_at),
        "supervisor_verified_at": fmt(task.supervisor_verified_at),
        "supervisor_verified_by": task.supervisor_verified_by,
        "is_overdue": task.is_overdue, "is_late": task.is_late or False,
        "is_archived": task.is_archived or False,
        "archived_at": fmt(task.archived_at) if hasattr(task, 'archived_at') else None,
        "actual_time_taken": task.actual_time_taken, "template_id": task.template_id,
        "parent_task_id": task.parent_task_id,
        "rejection_reason": task.rejection_reason,
        "created_at": fmt(task.created_at), "updated_at": fmt(task.updated_at)
    }

@api_router.get("/tasks")
def get_tasks(status: str = None, category: str = None, priority: str = None, assigned_to: str = None,
              limit: int = 20, offset: int = 0,
              db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Task).filter(Task.is_deleted == False, Task.is_archived == False)
    if current_user.role == "STAFF":
        query = query.filter(Task.assigned_to == current_user.id)
    elif current_user.role == "SUPERVISOR":
        # Supervisor sees only tasks assigned to them (parent tasks), excluding VERIFIED ones.
        # Sub-task info is embedded inside the parent task response — no separate sub-task cards.
        from sqlalchemy import and_
        query = query.filter(
            and_(Task.assigned_to == current_user.id, Task.status != "VERIFIED")
        )
    else:
        # MANAGER / OWNER: see all parent tasks only — sub-tasks are embedded in the parent card.
        query = query.filter(Task.parent_task_id == None)
    if status:
        query = query.filter(Task.status == status)
    if category:
        query = query.filter(Task.category == category)
    if priority:
        query = query.filter(Task.priority == priority)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)

    # now_sl() is naive SL time — same reference frame as stored DB datetimes
    now = now_sl()
    today = now.day

    tasks = query.order_by(Task.created_at.asc()).all()

    # Batch query: fetch active (non-VERIFIED) sub-task for each parent task in one query
    all_task_ids = [t.id for t in tasks]
    active_subtask_map = {}  # parent_task_id -> Task object
    if all_task_ids:
        active_subtask_rows = db.query(Task).filter(
            Task.parent_task_id.in_(all_task_ids),
            Task.is_deleted == False,
            Task.status != "VERIFIED"
        ).all()
        for sub in active_subtask_rows:
            active_subtask_map[sub.parent_task_id] = sub  # latest active sub-task per parent

    result = []
    for task in tasks:
        # For recurring tasks: check today is in schedule and allocated time has passed
        if task.task_type == "RECURRING" and task.recurrence_intervals:
            if today not in task.recurrence_intervals:
                continue
            if task.allocated_datetime and task.allocated_datetime > now:
                continue
        t_resp = task_to_response(task)
        active_sub = active_subtask_map.get(task.id)
        if active_sub:
            t_resp["has_active_subtask"] = True
            t_resp["active_subtask"] = {
                "id": active_sub.id,
                "status": (active_sub.status or "PENDING").upper(),
                "proof_photos": active_sub.proof_photos or [],
                "rejection_reason": active_sub.rejection_reason,
                "supervisor_verified_at": active_sub.supervisor_verified_at.isoformat() if active_sub.supervisor_verified_at else None,
                "assigned_to": active_sub.assigned_to,
                "assigned_to_name": active_sub.assigned_to_name,
            }
        else:
            t_resp["has_active_subtask"] = False
            t_resp["active_subtask"] = None
        result.append(t_resp)
    total = len(result)
    paginated = result[offset:offset + limit]
    return {"tasks": paginated, "total": total, "limit": limit, "offset": offset, "has_more": offset + limit < total}

@api_router.post("/tasks")
async def create_task(task_data: TaskCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    assigned_to_name = None
    if task_data.assigned_to:
        assigned_user = db.query(User).filter(User.id == task_data.assigned_to).first()
        if assigned_user:
            assigned_to_name = assigned_user.name

    # KEY FIX: Convert incoming datetime to naive SL time.
    # Frontend typically sends UTC ISO string (e.g. "2026-03-01T10:30:00+00:00").
    # to_sl_naive converts it to SL time (UTC+5:30) then strips timezone for MySQL.
    if task_data.allocated_datetime:
        allocated_datetime = to_sl_naive(task_data.allocated_datetime)
    else:
        allocated_datetime = now_sl()

    deadline = calculate_deadline(allocated_datetime, task_data.time_interval, task_data.time_unit)

    task = Task(
        title=task_data.title, description=task_data.description, category=task_data.category,
        priority=(task_data.priority or "MEDIUM").upper(), task_type=(task_data.task_type or "INSTANT").upper(),
        status="PENDING", time_interval=task_data.time_interval, time_unit=task_data.time_unit,
        allocated_datetime=allocated_datetime, deadline=deadline,
        recurrence_pattern=task_data.recurrence_pattern, recurrence_intervals=task_data.recurrence_intervals,
        assigned_to=task_data.assigned_to, assigned_to_name=assigned_to_name,
        created_by=current_user.id, created_by_name=current_user.name
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    create_activity_log(db, task.id, current_user.id, current_user.name, "CREATED", f"Task created: {task.title}")

    if task.assigned_to:
        await create_notification(db, task.assigned_to, "Task Starting Now",
                                   f"{task.title}", task.id)
    await manager.broadcast_to_all({"type": "task_created", "data": task_to_response(task)})
    return task_to_response(task)

# ===================== BULK DELETE =====================
@api_router.post("/tasks/bulk-delete")
@api_router.delete("/tasks/bulk-delete")
async def bulk_delete_tasks(request: BulkDeleteRequest, db: Session = Depends(get_db),
                            current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    task_ids = request.task_ids
    db.query(Task).filter(Task.id.in_(task_ids)).update({"is_deleted": True}, synchronize_session=False)
    db.commit()
    await manager.broadcast_to_all({"type": "tasks_deleted", "data": {"ids": task_ids}})
    return {"message": f"Deleted {len(task_ids)} tasks"}

@api_router.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_response(task)

@api_router.put("/tasks/{task_id}")
async def update_task(task_id: str, task_data: TaskUpdate, db: Session = Depends(get_db),
                      current_user: User = Depends(require_roles(["OWNER", "MANAGER", "SUPERVISOR"]))):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Supervisor can only update tasks they created
    if current_user.role == "SUPERVISOR" and task.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update tasks you created")

    update_fields = task_data.dict(exclude_unset=True)

    if "assigned_to" in update_fields and update_fields["assigned_to"]:
        assigned_user = db.query(User).filter(User.id == update_fields["assigned_to"]).first()
        if assigned_user:
            task.assigned_to_name = assigned_user.name

    # KEY FIX: Convert incoming allocated_datetime to naive SL time
    if "allocated_datetime" in update_fields and update_fields["allocated_datetime"]:
        update_fields["allocated_datetime"] = to_sl_naive(update_fields["allocated_datetime"])

    # Recalculate deadline if any time-related field changed
    if any(k in update_fields for k in ("time_interval", "time_unit", "allocated_datetime")):
        allocated = update_fields.get("allocated_datetime", task.allocated_datetime)
        interval = update_fields.get("time_interval", task.time_interval)
        unit = update_fields.get("time_unit", task.time_unit)
        task.deadline = calculate_deadline(allocated, interval, unit)

    for key, value in update_fields.items():
        if value is not None:
            setattr(task, key, value)

    db.commit()
    db.refresh(task)
    create_activity_log(db, task.id, current_user.id, current_user.name, "UPDATED", "Task updated")
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(task)})
    return task_to_response(task)

@api_router.post("/tasks/{task_id}/start")
async def start_task(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "PENDING":
        raise HTTPException(status_code=400, detail="Task can only be started from PENDING status")
    if task.assigned_to and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this task")
    task.status = "IN_PROGRESS"
    task.started_at = now_sl()
    db.commit()
    db.refresh(task)
    create_activity_log(db, task.id, current_user.id, current_user.name, "STARTED", "Task started")
    # If this is a sub-task, update parent task status to IN_PROGRESS
    if task.parent_task_id:
        parent_task = db.query(Task).filter(Task.id == task.parent_task_id, Task.is_deleted == False).first()
        if parent_task and parent_task.status == "PENDING":
            parent_task.status = "IN_PROGRESS"
            parent_task.started_at = now_sl()
            db.commit()
            await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(parent_task)})
        if parent_task and parent_task.assigned_to:
            await create_notification(db, parent_task.assigned_to, "TASK_UPDATED", "Sub-task Started",
                                      f"Sub-task '{task.title}' has been started", task.id)
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(task)})
    return task_to_response(task)
@api_router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("IN_PROGRESS", "NOT_COMPLETED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Task can only be completed from IN_PROGRESS, NOT_COMPLETED or REJECTED status")
    if not task.proof_photos or len(task.proof_photos) == 0:
        raise HTTPException(status_code=400, detail="Proof photo required before completing")

    now = now_sl()
    is_late = task.status == "NOT_COMPLETED" or task.is_overdue or (task.deadline and now > task.deadline)
    actual_time = None
    if task.started_at:
        delta = now - task.started_at
        actual_time = int(delta.total_seconds() / 60)

    task.status = "COMPLETED"
    task.completed_at = now
    task.is_late = is_late
    task.actual_time_taken = actual_time
    db.commit()
    db.refresh(task)

    create_activity_log(db, task.id, current_user.id, current_user.name, "COMPLETED",
                        f"Task {'completed (late)' if is_late else 'completed'}")
    # If this is a sub-task, update parent task status to IN_PROGRESS
    if task.parent_task_id:
        parent_task = db.query(Task).filter(Task.id == task.parent_task_id, Task.is_deleted == False).first()
        if parent_task and parent_task.status == "PENDING":
            parent_task.status = "IN_PROGRESS"
            parent_task.started_at = now
            db.commit()
            await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(parent_task)})
        # Notify supervisor
        if parent_task and parent_task.assigned_to:
            await create_notification(db, parent_task.assigned_to, "TASK_COMPLETED", "Sub-task Completed",
                                      f"Sub-task '{task.title}' has been completed", task.id)
            fcm_tokens = db.query(FCMToken).filter(FCMToken.user_id == parent_task.assigned_to).all()
            for fcm_token in fcm_tokens:
                await send_fcm_notification(fcm_token.token, "Sub-task Completed",
                                            f"Sub-task '{task.title}' has been completed")
    managers = db.query(User).filter(User.role.in_(["OWNER", "MANAGER"]), User.status == "ACTIVE").all()
    late_msg = " (Late)" if is_late else ""
    for mgr in managers:
        await create_notification(db, mgr.id, "TASK_COMPLETED", "Task Completed",
                                   f"Task '{task.title}' has been completed{late_msg} and is ready for verification", task.id)
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(task)})
    return task_to_response(task)


@api_router.post("/tasks/{task_id}/subtasks")
async def create_subtask(task_id: str, task_data: TaskCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(require_roles(["OWNER", "MANAGER", "SUPERVISOR"]))):
    parent_task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not parent_task:
        raise HTTPException(status_code=404, detail="Parent task not found")
    if current_user.role == "SUPERVISOR" and parent_task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="You can only create sub-tasks for your own tasks")
    assigned_to_name = None
    if task_data.assigned_to:
        staff = db.query(User).filter(User.id == task_data.assigned_to).first()
        if staff:
            assigned_to_name = staff.name
    task = Task(
        title=task_data.title, description=task_data.description,
        category=task_data.category, priority=task_data.priority or "MEDIUM",
        status="PENDING", task_type="SUBTASK",
        time_interval=task_data.time_interval, time_unit=task_data.time_unit or "MINUTES",
        allocated_datetime=task_data.allocated_datetime,
        assigned_to=task_data.assigned_to, assigned_to_name=assigned_to_name,
        created_by=current_user.id, created_by_name=current_user.name,
        parent_task_id=task_id, is_notified=False
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    if task_data.assigned_to:
        await create_notification(db, task_data.assigned_to, "TASK_ASSIGNED", "New Sub-Task Assigned",
                                  f"You have been assigned a sub-task: {task.title}", task.id)
    await manager.broadcast_to_all({"type": "task_created", "data": task_to_response(task)})
    # Broadcast parent task update so supervisor card shows Re-assign button and sub-task status immediately
    parent_response = task_to_response(parent_task)
    parent_response["has_active_subtask"] = True
    parent_response["active_subtask"] = {
        "id": task.id,
        "status": task.status,
        "proof_photos": task.proof_photos or [],
        "rejection_reason": task.rejection_reason,
        "supervisor_verified_at": None,
        "assigned_to": task.assigned_to,
        "assigned_to_name": task.assigned_to_name,
    }
    await manager.broadcast_to_all({"type": "task_update", "data": parent_response})
    return task_to_response(task)

@api_router.get("/tasks/{task_id}/subtasks")
def get_subtasks(task_id: str, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    subtasks = db.query(Task).filter(
        Task.parent_task_id == task_id,
        Task.is_deleted == False
    ).all()
    return [task_to_response(t) for t in subtasks]

@api_router.post("/tasks/{task_id}/reassign")
async def reassign_subtask(task_id: str, staff_id: str, db: Session = Depends(get_db),
                           current_user: User = Depends(require_roles(["OWNER", "MANAGER", "SUPERVISOR"]))):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user.role == "SUPERVISOR":
        if not task.parent_task_id:
            raise HTTPException(status_code=403, detail="Supervisors can only reassign sub-tasks")
        if task.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="You can only reassign sub-tasks you created")
        if task.status == "VERIFIED":
            raise HTTPException(status_code=400, detail="Cannot reassign a verified task")
    new_staff = db.query(User).filter(User.id == staff_id, User.status == "ACTIVE").first()
    if not new_staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    old_assignee = task.assigned_to_name
    # Reset task so new staff starts fresh
    task.assigned_to = staff_id
    task.assigned_to_name = new_staff.name
    task.status = "PENDING"
    task.proof_photos = []
    task.rejection_reason = None
    task.started_at = None
    task.completed_at = None
    task.supervisor_verified_at = None
    task.supervisor_verified_by = None
    db.commit()
    db.refresh(task)
    create_activity_log(db, task.id, current_user.id, current_user.name, "REASSIGNED",
                        f"Reassigned from {old_assignee} to {new_staff.name}")
    await create_notification(db, staff_id, "TASK_ASSIGNED", "Sub-Task Assigned",
                              f"You have been assigned a sub-task: {task.title}", task.id)
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(task)})
    return task_to_response(task)

@api_router.post("/tasks/{task_id}/verify")
async def verify_task(task_id: str, db: Session = Depends(get_db),
                      current_user: User = Depends(require_roles(["OWNER", "MANAGER", "SUPERVISOR"]))):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user.role == "SUPERVISOR":
        if task.parent_task_id is None:
            raise HTTPException(status_code=403, detail="Supervisors can only verify sub-tasks")
        if task.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="You can only verify sub-tasks you created")
        if task.status != "COMPLETED":
            raise HTTPException(status_code=400, detail="Task must be COMPLETED before supervisor verification")
        if task.supervisor_verified_at:
            raise HTTPException(status_code=400, detail="Sub-task has already been supervisor-verified")
        # Supervisor first-stage verify
        task.status = "SUPERVISOR_VERIFIED"
        task.supervisor_verified_at = now_sl()
        task.supervisor_verified_by = current_user.id
        db.commit()
        create_activity_log(db, task.id, current_user.id, current_user.name, "SUPERVISOR_VERIFIED", "Sub-task verified by supervisor — awaiting manager/owner final verification")
        # Notify owner/manager to do final verification
        managers = db.query(User).filter(User.role.in_(["OWNER", "MANAGER"]), User.status == "ACTIVE").all()
        for mgr in managers:
            await create_notification(db, mgr.id, "TASK_COMPLETED", "Sub-task Ready for Final Verification",
                                      f"Sub-task '{task.title}' has been supervisor-verified and is ready for your final approval", task.id)
        if task.assigned_to:
            await create_notification(db, task.assigned_to, "TASK_VERIFIED", "Sub-task Supervisor-Verified",
                                      f"Your sub-task '{task.title}' was verified by supervisor and is pending manager approval", task.id)
    else:
        # Owner/Manager final verification — accept COMPLETED (regular tasks) or SUPERVISOR_VERIFIED (sub-tasks)
        if task.status not in ("COMPLETED", "SUPERVISOR_VERIFIED"):
            raise HTTPException(status_code=400, detail="Task must be COMPLETED or SUPERVISOR_VERIFIED to verify")
        if task.parent_task_id and task.status == "COMPLETED":
            raise HTTPException(status_code=400, detail="This sub-task must be supervisor-verified before final verification")
        task.status = "VERIFIED"
        task.verified_at = now_sl()
        task.verified_by = current_user.id
        db.commit()
        create_activity_log(db, task.id, current_user.id, current_user.name, "VERIFIED", "Task fully verified")
        if task.assigned_to:
            await create_notification(db, task.assigned_to, "TASK_VERIFIED", "Task Verified",
                                      f"Your task '{task.title}' has been fully verified!", task.id)
        # If this was a sub-task, auto-verify the parent task when no active sub-tasks remain
        if task.parent_task_id:
            parent_task = db.query(Task).filter(Task.id == task.parent_task_id, Task.is_deleted == False).first()
            if parent_task:
                remaining_active = db.query(Task).filter(
                    Task.parent_task_id == task.parent_task_id,
                    Task.is_deleted == False,
                    Task.status != "VERIFIED"
                ).count()
                if remaining_active == 0:
                    # All sub-tasks done — mark parent task as VERIFIED too
                    parent_task.status = "VERIFIED"
                    parent_task.verified_at = now_sl()
                    parent_task.verified_by = current_user.id
                    db.commit()
                    create_activity_log(db, parent_task.id, current_user.id, current_user.name,
                                        "VERIFIED", "Auto-verified: all sub-tasks have been verified")
                    if parent_task.assigned_to:
                        await create_notification(db, parent_task.assigned_to, "TASK_VERIFIED", "Task Fully Verified",
                                                  f"Your task '{parent_task.title}' has been fully verified!", parent_task.id)
                parent_response = task_to_response(parent_task)
                parent_response["has_active_subtask"] = remaining_active > 0
                parent_response["active_subtask"] = None
                await manager.broadcast_to_all({"type": "task_update", "data": parent_response})
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(task)})
    return task_to_response(task)

@api_router.post("/tasks/{task_id}/reject")
async def reject_task(task_id: str, reason: str = "", db: Session = Depends(get_db),
                      current_user: User = Depends(require_roles(["OWNER", "MANAGER", "SUPERVISOR"]))):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user.role == "SUPERVISOR":
        if not task.parent_task_id:
            raise HTTPException(status_code=403, detail="Supervisors can only reject sub-tasks")
        if task.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="You can only reject sub-tasks you created")
        if task.status != "COMPLETED":
            raise HTTPException(status_code=400, detail="Can only reject a COMPLETED sub-task")
    was_supervisor_verified = task.status == "SUPERVISOR_VERIFIED"
    supervisor_id = task.supervisor_verified_by  # capture before clearing
    task.status = "REJECTED"
    task.proof_photos = []
    task.rejection_reason = reason
    # Reset supervisor verification stamps so supervisor can re-verify after staff fixes and resubmits
    if was_supervisor_verified:
        task.supervisor_verified_at = None
        task.supervisor_verified_by = None
    db.commit()
    create_activity_log(db, task.id, current_user.id, current_user.name, "REJECTED", f"Proof rejected: {reason}")
    if task.assigned_to:
        await create_notification(db, task.assigned_to, "TASK_REJECTED", "Proof Rejected",
                                  f"Your proof for '{task.title}' was rejected. {reason}", task.id)
        fcm_tokens = db.query(FCMToken).filter(FCMToken.user_id == task.assigned_to).all()
        for fcm_token in fcm_tokens:
            await send_fcm_notification(
                fcm_token.token,
                "Proof Rejected",
                f"Your proof for '{task.title}' was rejected. {reason}"
            )
    # Notify the supervisor when manager/owner overrules their verification
    if was_supervisor_verified and supervisor_id and current_user.role in ("OWNER", "MANAGER"):
        await create_notification(db, supervisor_id, "TASK_REJECTED", "Your Verification Was Overruled",
                                  f"Manager rejected sub-task '{task.title}' after your verification. "
                                  f"Reason: {reason}. Staff must resubmit — please re-verify once fixed.", task.id)
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(task)})
    return task_to_response(task)

@api_router.post("/tasks/{task_id}/proof")
async def upload_proof(task_id: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    uploads_dir = ROOT_DIR / "uploads" / "proofs"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_ext = Path(file.filename).suffix or ".jpg"
    filename = f"{task_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = uploads_dir / filename
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    proof_url = f"/api/uploads/proofs/{filename}"
    task.proof_photos = list(task.proof_photos or []) + [proof_url]
    db.commit()
    db.refresh(task)
    create_activity_log(db, task.id, current_user.id, current_user.name, "PROOF_UPLOADED", "Proof photo uploaded")
    return {"message": "Proof uploaded", "url": proof_url, "task": task_to_response(task)}

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, db: Session = Depends(get_db),
                      current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_deleted = True
    db.commit()
    await manager.broadcast_to_all({"type": "task_deleted", "data": {"id": task_id}})
    return {"message": "Task deleted"}

# ===================== REPORTS =====================
@api_router.get("/reports/tasks")
def get_task_reports(
    status: str = None, category: str = None, priority: str = None, assigned_to: str = None,
    date_from: str = None, date_to: str = None, include_archived: bool = True,
    limit: int = 10, offset: int = 0,
    db: Session = Depends(get_db), current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))
):
    query = db.query(Task).filter(Task.is_deleted == False)
    if not include_archived:
        query = query.filter(Task.is_archived == False)
    if status:
        query = query.filter(Task.status == status)
    if category:
        query = query.filter(Task.category == category)
    if priority:
        query = query.filter(Task.priority == priority)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Task.created_at >= from_date)
        except ValueError:
            pass
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Task.created_at < to_date)
        except ValueError:
            pass
    tasks = query.order_by(Task.created_at.desc()).all()
    total = len(tasks)
    paginated = tasks[offset:offset + limit]
    return {
        "tasks": [task_to_response(t) for t in paginated],
        "total": total,
        "has_more": offset + limit < total,
        "summary": {
            "total": total,
            "verified": sum(1 for t in tasks if t.status == "VERIFIED"),
            "completed": sum(1 for t in tasks if t.status == "COMPLETED"),
            "late": sum(1 for t in tasks if t.is_late),
            "overdue": sum(1 for t in tasks if t.is_overdue),
            "pending": sum(1 for t in tasks if t.status == "PENDING"),
            "in_progress": sum(1 for t in tasks if t.status == "IN_PROGRESS"),
            "not_completed": sum(1 for t in tasks if t.status == "NOT_COMPLETED"),
        }
    }

# ===================== TASK COMMENTS =====================
@api_router.get("/tasks/{task_id}/comments", response_model=List[CommentResponse])
def get_task_comments(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.desc()).all()
    return [CommentResponse(id=c.id, task_id=c.task_id, user_id=c.user_id, user_name=c.user_name,
                            content=c.content, created_at=c.created_at) for c in comments]

@api_router.post("/tasks/{task_id}/comments", response_model=CommentResponse)
async def add_task_comment(task_id: str, comment_data: CommentCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    comment = TaskComment(task_id=task_id, user_id=current_user.id, user_name=current_user.name,
                          content=comment_data.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    create_activity_log(db, task_id, current_user.id, current_user.name, "COMMENT_ADDED", comment_data.content[:100])
    return CommentResponse(id=comment.id, task_id=comment.task_id, user_id=comment.user_id,
                           user_name=comment.user_name, content=comment.content, created_at=comment.created_at)

# ===================== TASK ACTIVITY LOG =====================
@api_router.get("/tasks/{task_id}/activity")
def get_task_activity(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    logs = db.query(TaskActivityLog).filter(TaskActivityLog.task_id == task_id).order_by(TaskActivityLog.created_at.desc()).all()
    return [{"id": log.id, "task_id": log.task_id, "user_id": log.user_id, "user_name": log.user_name,
             "action": log.action, "details": log.details, "created_at": log.created_at.isoformat()} for log in logs]

# ===================== FCM TOKEN =====================
class FCMTokenRequest(BaseModel):
    token: str

@api_router.post("/fcm-token")
def save_fcm_token(request: FCMTokenRequest, db: Session = Depends(get_db), 
                   current_user: User = Depends(get_current_user)):
   # Delete all existing tokens for this user
    db.query(FCMToken).filter(FCMToken.user_id == current_user.id).delete()
    # Save the new token
    fcm_token = FCMToken(user_id=current_user.id, token=request.token)
    db.add(fcm_token)
    db.commit()
    return {"message": "FCM token saved"}
# ===================== NOTIFICATIONS =====================
@api_router.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notifications = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return [NotificationResponse(id=n.id, type=n.type, title=n.title, message=n.message,
                                  task_id=n.task_id, is_read=n.is_read, created_at=n.created_at) for n in notifications]

@api_router.get("/notifications/unread-count")
def get_unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    count = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).count()
    return {"count": count}

@api_router.post("/notifications/mark-read")
def mark_notifications_read(notification_ids: List[str] = None, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if notification_ids:
        query = query.filter(Notification.id.in_(notification_ids))
    query.update({"is_read": True}, synchronize_session=False)
    db.commit()
    return {"message": "Notifications marked as read"}

@api_router.post("/notifications/mark-all-read")
@api_router.put("/notifications/read-all")
def mark_all_notifications_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == current_user.id).update({"is_read": True}, synchronize_session=False)
    db.commit()
    return {"message": "All notifications marked as read"}

@api_router.put("/notifications/{notification_id}/read")
def mark_single_notification_read(notification_id: str, db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    notification = db.query(Notification).filter(Notification.id == notification_id,
                                                   Notification.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}

# ===================== DASHBOARD =====================
@api_router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    base_query = db.query(Task).filter(Task.is_deleted == False)
    if current_user.role == "STAFF":
        base_query = base_query.filter(Task.assigned_to == current_user.id)
    total_tasks = base_query.count()
    in_progress = base_query.filter(Task.status == "IN_PROGRESS").count()
    completed = base_query.filter(Task.status == "COMPLETED").count()
    verified = base_query.filter(Task.status == "VERIFIED").count()
    tasks_to_assign = db.query(Task).filter(Task.is_deleted == False, Task.assigned_to == None).count()
    tasks_to_verify = db.query(Task).filter(Task.is_deleted == False, Task.status.in_(["COMPLETED", "SUPERVISOR_VERIFIED"])).count()
    staff_count = db.query(User).filter(User.role.in_(["STAFF", "MANAGER", "SUPERVISOR"]), User.status == "ACTIVE").count()
    return DashboardStats(total_tasks=total_tasks, in_progress=in_progress, completed=completed,
                          verified=verified, tasks_to_assign=tasks_to_assign,
                          tasks_to_verify=tasks_to_verify, staff_count=staff_count)

# ===================== FILE SERVING =====================
@api_router.get("/uploads/proofs/{filename}")
async def serve_proof_file(filename: str):
    file_path = ROOT_DIR / "uploads" / "proofs" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

# ===================== WEBSOCKET =====================
@api_router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)

# ===================== SEED DATA =====================
@api_router.post("/seed")
def seed_data(db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == "owner@zomoto.lk").first():
        return {"message": "Already seeded"}
    users_data = [
        {"name": "Restaurant Owner", "email": "owner@zomoto.lk", "phone": "0771234567", "role": "OWNER"},
        {"name": "Manager", "email": "manager@zomoto.lk", "phone": "0771234568", "role": "MANAGER"},
        {"name": "Staff Member", "email": "staff@zomoto.lk", "phone": "0771234569", "role": "STAFF"},
    ]
    for u in users_data:
        user = User(name=u["name"], email=u["email"], phone=u["phone"], role=u["role"],
                    hashed_password=get_password_hash("123456"))
        db.add(user)
    categories_data = [
        {"name": "Kitchen", "color": "#EF4444"}, {"name": "Cleaning", "color": "#3B82F6"},
        {"name": "Maintenance", "color": "#F59E0B"}, {"name": "Other", "color": "#6B7280"},
    ]
    for c in categories_data:
        db.add(Category(name=c["name"], color=c["color"]))
    db.commit()
    return {"message": "Database seeded successfully"}

# ===================== BACKGROUND TASKS =====================
async def send_scheduled_notifications():
    """Send push notifications when task allocated_datetime is reached."""
    while True:
        try:
            db = SessionLocal()
            now = now_sl()
            # Find tasks that:
            # 1. Are still PENDING
            # 2. Have an allocated_datetime in the past (time has come)
            # 3. Have not been notified yet (use started_at as proxy — if None, not started)
            # We use a 2-minute window to avoid missing tasks
            one_min_ago = now - timedelta(minutes=1)
            tasks_due = db.query(Task).filter(
                Task.is_deleted == False,
                Task.status == "PENDING",
                Task.allocated_datetime <= now,
                Task.assigned_to != None,
                Task.is_notified == False
            ).all()

            for task in tasks_due:
                # Mark as notified FIRST before sending to prevent duplicates
                task.is_notified = True
                db.commit()
                
                fcm_tokens = db.query(FCMToken).filter(FCMToken.user_id == task.assigned_to).all()
                for fcm_token in fcm_tokens:
                    await send_fcm_notification(
                        fcm_token.token,
                        "Task Starting Now",
                        f"Your task '{task.title}' is scheduled to start now"
                    )
                logger.info(f"Sent scheduled notification for task: {task.title}")
            db.close()
        except Exception as e:
            logger.error(f"Error sending scheduled notifications: {e}")
        await asyncio.sleep(60)


async def check_overdue_tasks():
    """Check for overdue tasks. All datetimes are naive SL — same reference as DB."""
    while True:
        try:
            db = SessionLocal()
            now = now_sl()
            overdue_tasks = db.query(Task).filter(
                Task.is_deleted == False,
                Task.status == "IN_PROGRESS",
                Task.deadline < now,
                Task.is_overdue == False
            ).all()
            for task in overdue_tasks:
                task.is_overdue = True
                task.is_late = True
                if task.assigned_to:
                    db.add(Notification(user_id=task.assigned_to, type="TASK_OVERDUE",
                                        title="Task Overdue",
                                        message=f"Task '{task.title}' has exceeded its deadline",
                                        task_id=task.id))
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Error checking overdue tasks: {e}")
        await asyncio.sleep(60)

def parse_day_intervals(day_intervals_str: str) -> set:
    days = set()
    if not day_intervals_str:
        return days
    for part in day_intervals_str.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                for d in range(int(start.strip()), int(end.strip()) + 1):
                    if 1 <= d <= 31:
                        days.add(d)
            except ValueError:
                continue
        else:
            try:
                d = int(part)
                if 1 <= d <= 31:
                    days.add(d)
            except ValueError:
                continue
    return days

async def generate_recurring_tasks():
    """Background job: generate task instances from active recurring templates.
    allocated_time in templates is 'HH:MM' in SL time — combined with today's SL date."""
    while True:
        try:
            db = SessionLocal()
            now = now_sl()
            today = now.date()
            today_day = today.day

            templates = db.query(TaskTemplate).filter(
                TaskTemplate.is_recurring == True,
                TaskTemplate.is_active == True
            ).all()

            for tmpl in templates:
                scheduled_days = parse_day_intervals(tmpl.day_intervals)
                if not scheduled_days or today_day not in scheduled_days:
                    continue
                today_start = datetime.combine(today, datetime.min.time())
                today_end = datetime.combine(today, datetime.max.time())
                existing = db.query(Task).filter(
                    Task.template_id == tmpl.id,
                    Task.created_at >= today_start,
                    Task.created_at <= today_end,
                    Task.is_deleted == False
                ).first()
                if existing:
                    continue

                task = _build_task_from_template(tmpl, today, now)
                db.add(task)
                logger.info(f"Generated recurring task: {task.title} from template {tmpl.id}")

                if tmpl.assigned_to:
                    db.add(Notification(user_id=tmpl.assigned_to, type="TASK_ASSIGNED",
                                        title="New Recurring Task",
                                        message=f"Recurring task '{task.title}' has been assigned to you",
                                        task_id=task.id))
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Error generating recurring tasks: {e}")
        await asyncio.sleep(300)

# ===================== APP STARTUP =====================
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Zomoto Tasks API with MySQL...")
    seed_default_data()
    asyncio.create_task(check_overdue_tasks())
    asyncio.create_task(generate_recurring_tasks())
    asyncio.create_task(send_scheduled_notifications())

def seed_default_data():
    db = SessionLocal()
    try:
        default_users = [
            {"name": "Owner", "email": "owner@zomoto.lk", "role": "OWNER", "password": "123456"},
            {"name": "Manager", "email": "manager@zomoto.lk", "role": "MANAGER", "password": "123456"},
            {"name": "Staff", "email": "staff@zomoto.lk", "role": "STAFF", "password": "123456"},
        ]
        for u in default_users:
            if not db.query(User).filter(User.email == u["email"]).first():
                db.add(User(name=u["name"], email=u["email"], role=u["role"],
                            hashed_password=get_password_hash(u["password"])))
                logger.info(f"Seeded user: {u['email']}")
        db.commit()
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

# Include API router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "healthy", "database": "MySQL", "version": "3.0.0"}

if __name__ == "__main__":
    import uvicorn
    _host = os.environ.get("HOST", "0.0.0.0")
    _port = int(os.environ.get("PORT", 8000))
    _reload = os.environ.get("ENV", "development") == "development"
    uvicorn.run("server:app", host=_host, port=_port, reload=_reload)
