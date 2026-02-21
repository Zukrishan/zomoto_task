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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MySQL Configuration
MYSQL_URL = os.environ.get('MYSQL_URL', 'mysql+pymysql://root@localhost/zomoto_tasks?unix_socket=/run/mysqld/mysqld.sock')
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

# ===================== ENUMS =====================
class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    color = Column(String(50), default="#6B7280")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class TaskTemplate(Base):
    __tablename__ = "task_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(255))
    priority = Column(String(20), default="MEDIUM")
    time_interval = Column(Integer, default=30)
    time_unit = Column(String(20), default="MINUTES")
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

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
    allocated_datetime = Column(DateTime)
    deadline = Column(DateTime)
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
    verified_by = Column(String(36))
    is_deleted = Column(Boolean, default=False, index=True)
    is_overdue = Column(Boolean, default=False)
    parent_task_id = Column(String(36))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class TaskComment(Base):
    __tablename__ = "task_comments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    user_name = Column(String(255))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class TaskActivityLog(Base):
    __tablename__ = "task_activity_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    user_name = Column(String(255))
    action = Column(String(100), nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    task_id = Column(String(36))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Create all tables
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

class TemplateResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    time_interval: int
    time_unit: str
    created_at: datetime

    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    content: str

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
        logger.info(f"WebSocket connected for user {user_id}. Total connections for user: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")
    
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
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        task_id=task_id
    )
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
    log = TaskActivityLog(
        task_id=task_id,
        user_id=user_id,
        user_name=user_name,
        action=action,
        details=details
    )
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
        user=UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            status=user.status,
            created_at=user.created_at
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        phone=current_user.phone,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at
    )

# ===================== USER ENDPOINTS =====================
@api_router.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    users = db.query(User).all()
    return [UserResponse(
        id=u.id, name=u.name, email=u.email, phone=u.phone,
        role=u.role, status=u.status, created_at=u.created_at
    ) for u in users]

@api_router.get("/users/staff", response_model=List[UserResponse])
def get_staff(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).filter(User.role.in_(["STAFF", "MANAGER"]), User.status == "ACTIVE").all()
    return [UserResponse(
        id=u.id, name=u.name, email=u.email, phone=u.phone,
        role=u.role, status=u.status, created_at=u.created_at
    ) for u in users]

@api_router.post("/users", response_model=UserResponse)
def create_user(user_data: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        role=user_data.role,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id, name=user.name, email=user.email, phone=user.phone,
        role=user.role, status=user.status, created_at=user.created_at
    )

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
    
    return UserResponse(
        id=user.id, name=user.name, email=user.email, phone=user.phone,
        role=user.role, status=user.status, created_at=user.created_at
    )

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
@api_router.get("/task-templates", response_model=List[TemplateResponse])
def get_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    templates = db.query(TaskTemplate).all()
    return [TemplateResponse(
        id=t.id, title=t.title, description=t.description, category=t.category,
        priority=t.priority, time_interval=t.time_interval, time_unit=t.time_unit, created_at=t.created_at
    ) for t in templates]

@api_router.post("/task-templates", response_model=TemplateResponse)
def create_template(template_data: TemplateCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    template = TaskTemplate(
        title=template_data.title,
        description=template_data.description,
        category=template_data.category,
        priority=template_data.priority,
        time_interval=template_data.time_interval,
        time_unit=template_data.time_unit,
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return TemplateResponse(
        id=template.id, title=template.title, description=template.description, category=template.category,
        priority=template.priority, time_interval=template.time_interval, time_unit=template.time_unit, created_at=template.created_at
    )

@api_router.delete("/task-templates/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db),
                    current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    return {"message": "Template deleted"}

# ===================== TASK ENDPOINTS =====================
def task_to_response(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "category": task.category,
        "priority": task.priority,
        "status": task.status,
        "task_type": task.task_type,
        "time_interval": task.time_interval,
        "time_unit": task.time_unit,
        "allocated_datetime": task.allocated_datetime.isoformat() if task.allocated_datetime else None,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "recurrence_pattern": task.recurrence_pattern,
        "recurrence_intervals": task.recurrence_intervals or [],
        "proof_photos": task.proof_photos or [],
        "attachments": task.attachments or [],
        "assigned_to": task.assigned_to,
        "assigned_to_name": task.assigned_to_name,
        "created_by": task.created_by,
        "created_by_name": task.created_by_name,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "verified_at": task.verified_at.isoformat() if task.verified_at else None,
        "is_overdue": task.is_overdue,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None
    }

@api_router.get("/tasks")
def get_tasks(status: str = None, category: str = None, priority: str = None, assigned_to: str = None,
              db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Task).filter(Task.is_deleted == False)
    
    # Role-based filtering
    if current_user.role == "STAFF":
        query = query.filter(Task.assigned_to == current_user.id)
    
    if status:
        query = query.filter(Task.status == status)
    if category:
        query = query.filter(Task.category == category)
    if priority:
        query = query.filter(Task.priority == priority)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    
    # Filter recurring tasks by day and time
    now = datetime.now(timezone.utc)
    today = now.day
    
    tasks = query.order_by(Task.created_at.desc()).all()
    result = []
    
    for task in tasks:
        # For recurring tasks, check if visible today and time has passed
        if task.task_type == "RECURRING" and task.recurrence_intervals:
            if today not in task.recurrence_intervals:
                continue
            if task.allocated_datetime and task.allocated_datetime > now:
                continue
        
        result.append(task_to_response(task))
    
    return result

@api_router.post("/tasks")
async def create_task(task_data: TaskCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    # Get assigned user name if assigned
    assigned_to_name = None
    if task_data.assigned_to:
        assigned_user = db.query(User).filter(User.id == task_data.assigned_to).first()
        if assigned_user:
            assigned_to_name = assigned_user.name
    
    # Calculate deadline
    allocated_datetime = task_data.allocated_datetime or datetime.now(timezone.utc)
    if task_data.time_unit == "HOURS":
        deadline = allocated_datetime + timedelta(hours=task_data.time_interval)
    else:
        deadline = allocated_datetime + timedelta(minutes=task_data.time_interval)
    
    task = Task(
        title=task_data.title,
        description=task_data.description,
        category=task_data.category,
        priority=task_data.priority,
        task_type=task_data.task_type,
        time_interval=task_data.time_interval,
        time_unit=task_data.time_unit,
        allocated_datetime=allocated_datetime,
        deadline=deadline,
        recurrence_pattern=task_data.recurrence_pattern,
        recurrence_intervals=task_data.recurrence_intervals,
        assigned_to=task_data.assigned_to,
        assigned_to_name=assigned_to_name,
        created_by=current_user.id,
        created_by_name=current_user.name
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create activity log
    create_activity_log(db, task.id, current_user.id, current_user.name, "CREATED", f"Task created: {task.title}")
    
    # Send notification if assigned
    if task.assigned_to:
        await create_notification(
            db, task.assigned_to, "TASK_ASSIGNED", "New Task Assigned",
            f"You have been assigned: {task.title}", task.id
        )
    
    # Broadcast task creation
    await manager.broadcast_to_all({
        "type": "task_created",
        "data": task_to_response(task)
    })
    
    return task_to_response(task)

@api_router.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_to_response(task)

@api_router.put("/tasks/{task_id}")
async def update_task(task_id: str, task_data: TaskUpdate, db: Session = Depends(get_db),
                      current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_fields = task_data.dict(exclude_unset=True)
    
    # Handle assigned_to name
    if "assigned_to" in update_fields and update_fields["assigned_to"]:
        assigned_user = db.query(User).filter(User.id == update_fields["assigned_to"]).first()
        if assigned_user:
            task.assigned_to_name = assigned_user.name
    
    # Recalculate deadline if time changed
    if "time_interval" in update_fields or "time_unit" in update_fields or "allocated_datetime" in update_fields:
        allocated = update_fields.get("allocated_datetime", task.allocated_datetime)
        interval = update_fields.get("time_interval", task.time_interval)
        unit = update_fields.get("time_unit", task.time_unit)
        
        if unit == "HOURS":
            task.deadline = allocated + timedelta(hours=interval)
        else:
            task.deadline = allocated + timedelta(minutes=interval)
    
    for key, value in update_fields.items():
        if value is not None:
            setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    
    create_activity_log(db, task.id, current_user.id, current_user.name, "UPDATED", "Task updated")
    
    await manager.broadcast_to_all({
        "type": "task_update",
        "data": task_to_response(task)
    })
    
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
    task.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    
    create_activity_log(db, task.id, current_user.id, current_user.name, "STARTED", "Task started")
    
    await manager.broadcast_to_all({
        "type": "task_update",
        "data": task_to_response(task)
    })
    
    return task_to_response(task)

@api_router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="Task can only be completed from IN_PROGRESS status")
    
    if not task.proof_photos or len(task.proof_photos) == 0:
        raise HTTPException(status_code=400, detail="Proof photo required before completing")
    
    task.status = "COMPLETED"
    task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    
    create_activity_log(db, task.id, current_user.id, current_user.name, "COMPLETED", "Task completed")
    
    # Notify owner/managers
    managers = db.query(User).filter(User.role.in_(["OWNER", "MANAGER"]), User.status == "ACTIVE").all()
    for mgr in managers:
        await create_notification(
            db, mgr.id, "TASK_COMPLETED", "Task Completed",
            f"Task '{task.title}' has been completed and is ready for verification", task.id
        )
    
    await manager.broadcast_to_all({
        "type": "task_update",
        "data": task_to_response(task)
    })
    
    return task_to_response(task)

@api_router.post("/tasks/{task_id}/verify")
async def verify_task(task_id: str, db: Session = Depends(get_db), 
                      current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Only completed tasks can be verified")
    
    task.status = "VERIFIED"
    task.verified_at = datetime.now(timezone.utc)
    task.verified_by = current_user.id
    db.commit()
    db.refresh(task)
    
    create_activity_log(db, task.id, current_user.id, current_user.name, "VERIFIED", "Task verified")
    
    if task.assigned_to:
        await create_notification(
            db, task.assigned_to, "TASK_VERIFIED", "Task Verified",
            f"Your task '{task.title}' has been verified", task.id
        )
    
    await manager.broadcast_to_all({
        "type": "task_update",
        "data": task_to_response(task)
    })
    
    return task_to_response(task)

@api_router.post("/tasks/{task_id}/proof")
async def upload_proof(task_id: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Create uploads directory
    uploads_dir = ROOT_DIR / "uploads" / "proofs"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix or ".jpg"
    filename = f"{task_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = uploads_dir / filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Get the API base URL for the proof URL
    proof_url = f"/api/uploads/proofs/{filename}"
    
    # Update task proof photos
    proof_photos = task.proof_photos or []
    proof_photos.append(proof_url)
    task.proof_photos = proof_photos
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
    
    await manager.broadcast_to_all({
        "type": "task_deleted",
        "data": {"id": task_id}
    })
    
    return {"message": "Task deleted"}

@api_router.post("/tasks/bulk-delete")
async def bulk_delete_tasks(task_ids: List[str], db: Session = Depends(get_db),
                            current_user: User = Depends(require_roles(["OWNER", "MANAGER"]))):
    db.query(Task).filter(Task.id.in_(task_ids)).update({"is_deleted": True}, synchronize_session=False)
    db.commit()
    
    await manager.broadcast_to_all({
        "type": "tasks_deleted",
        "data": {"ids": task_ids}
    })
    
    return {"message": f"Deleted {len(task_ids)} tasks"}

# ===================== TASK COMMENTS =====================
@api_router.get("/tasks/{task_id}/comments", response_model=List[CommentResponse])
def get_task_comments(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.desc()).all()
    return [CommentResponse(
        id=c.id, task_id=c.task_id, user_id=c.user_id, user_name=c.user_name,
        content=c.content, created_at=c.created_at
    ) for c in comments]

@api_router.post("/tasks/{task_id}/comments", response_model=CommentResponse)
async def add_task_comment(task_id: str, comment_data: CommentCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    comment = TaskComment(
        task_id=task_id,
        user_id=current_user.id,
        user_name=current_user.name,
        content=comment_data.content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    create_activity_log(db, task_id, current_user.id, current_user.name, "COMMENT_ADDED", comment_data.content[:100])
    
    return CommentResponse(
        id=comment.id, task_id=comment.task_id, user_id=comment.user_id, user_name=comment.user_name,
        content=comment.content, created_at=comment.created_at
    )

# ===================== TASK ACTIVITY LOG =====================
@api_router.get("/tasks/{task_id}/activity")
def get_task_activity(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    logs = db.query(TaskActivityLog).filter(TaskActivityLog.task_id == task_id).order_by(TaskActivityLog.created_at.desc()).all()
    return [{
        "id": log.id,
        "task_id": log.task_id,
        "user_id": log.user_id,
        "user_name": log.user_name,
        "action": log.action,
        "details": log.details,
        "created_at": log.created_at.isoformat()
    } for log in logs]

# ===================== NOTIFICATIONS =====================
@api_router.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notifications = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return [NotificationResponse(
        id=n.id, type=n.type, title=n.title, message=n.message,
        task_id=n.task_id, is_read=n.is_read, created_at=n.created_at
    ) for n in notifications]

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
def mark_all_notifications_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == current_user.id).update({"is_read": True}, synchronize_session=False)
    db.commit()
    return {"message": "All notifications marked as read"}

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
    tasks_to_verify = db.query(Task).filter(Task.is_deleted == False, Task.status == "COMPLETED").count()
    staff_count = db.query(User).filter(User.role.in_(["STAFF", "MANAGER"]), User.status == "ACTIVE").count()
    
    return DashboardStats(
        total_tasks=total_tasks,
        in_progress=in_progress,
        completed=completed,
        verified=verified,
        tasks_to_assign=tasks_to_assign,
        tasks_to_verify=tasks_to_verify,
        staff_count=staff_count
    )

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
            # Handle ping/pong for keepalive
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
    # Check if already seeded
    if db.query(User).filter(User.email == "owner@zomoto.lk").first():
        return {"message": "Already seeded"}
    
    # Create users
    users_data = [
        {"name": "Restaurant Owner", "email": "owner@zomoto.lk", "phone": "0771234567", "role": "OWNER"},
        {"name": "Manager", "email": "manager@zomoto.lk", "phone": "0771234568", "role": "MANAGER"},
        {"name": "Staff Member", "email": "staff@zomoto.lk", "phone": "0771234569", "role": "STAFF"},
    ]
    
    for user_data in users_data:
        user = User(
            name=user_data["name"],
            email=user_data["email"],
            phone=user_data["phone"],
            role=user_data["role"],
            hashed_password=get_password_hash("123456")
        )
        db.add(user)
    
    # Create categories
    categories_data = [
        {"name": "Kitchen", "color": "#EF4444"},
        {"name": "Cleaning", "color": "#3B82F6"},
        {"name": "Maintenance", "color": "#F59E0B"},
        {"name": "Other", "color": "#6B7280"},
    ]
    
    for cat_data in categories_data:
        category = Category(name=cat_data["name"], color=cat_data["color"])
        db.add(category)
    
    db.commit()
    return {"message": "Database seeded successfully"}

# ===================== BACKGROUND TASKS =====================
async def check_overdue_tasks():
    """Check for overdue tasks and update their status"""
    while True:
        try:
            db = SessionLocal()
            now = datetime.now(timezone.utc)
            
            # Find tasks that are overdue
            overdue_tasks = db.query(Task).filter(
                Task.is_deleted == False,
                Task.status.in_(["PENDING", "IN_PROGRESS"]),
                Task.deadline < now,
                Task.is_overdue == False
            ).all()
            
            for task in overdue_tasks:
                task.is_overdue = True
                if task.status in ["PENDING", "IN_PROGRESS"]:
                    task.status = "NOT_COMPLETED"
                
                if task.assigned_to:
                    notification = Notification(
                        user_id=task.assigned_to,
                        type="TASK_OVERDUE",
                        title="Task Overdue",
                        message=f"Task '{task.title}' has exceeded its deadline",
                        task_id=task.id
                    )
                    db.add(notification)
            
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Error checking overdue tasks: {e}")
        
        await asyncio.sleep(60)  # Check every minute

# ===================== APP STARTUP =====================
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Zomoto Tasks API with MySQL...")
    asyncio.create_task(check_overdue_tasks())

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

# Health check
@app.get("/")
def health_check():
    return {"status": "healthy", "database": "MySQL", "version": "3.0.0"}
