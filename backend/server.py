from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import httpx
import aiofiles
from PIL import Image
import io
import enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MySQL connection
MYSQL_URL = os.environ.get('MYSQL_URL', 'mysql+pymysql://root@localhost/zomoto_tasks')
engine = create_engine(MYSQL_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'zomoto-tasks-secret-key-2024')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============== ENUMS ==============

class UserRoleEnum(str, enum.Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    STAFF = "STAFF"

class TaskStatusEnum(str, enum.Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"

class TaskPriorityEnum(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

# ============== SQLAlchemy MODELS ==============

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50))
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="STAFF")
    status = Column(String(20), nullable=False, default="ACTIVE")
    employee_id = Column(String(50))
    salary_type = Column(String(50))
    basic_salary = Column(Integer)
    created_by = Column(String(36))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    color = Column(String(20), default="#6B7280")
    is_active = Column(Boolean, default=True)
    created_by = Column(String(36))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class TaskTemplate(Base):
    __tablename__ = "task_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    name_lower = Column(String(255), index=True)
    default_category = Column(String(100))
    default_priority = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_by = Column(String(36))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    priority = Column(String(20), default="MEDIUM")
    due_date = Column(DateTime)
    status = Column(String(20), default="CREATED")
    created_by = Column(String(36), nullable=False)
    created_by_name = Column(String(255))
    assigned_to = Column(String(36), index=True)
    assigned_to_name = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class TaskComment(Base):
    __tablename__ = "task_comments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)
    user_name = Column(String(255))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class TaskAttachment(Base):
    __tablename__ = "task_attachments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    content_type = Column(String(100))
    file_size = Column(Integer)
    thumbnail_path = Column(String(500))
    uploaded_by = Column(String(36))
    uploaded_by_name = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class TaskActivityLog(Base):
    __tablename__ = "task_activity_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)
    user_name = Column(String(255))
    action = Column(String(50), nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    task_id = Column(String(36))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    endpoint = Column(Text, nullable=False)
    keys = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class NotificationLog(Base):
    __tablename__ = "notification_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(50), nullable=False)
    recipient = Column(String(255))
    message = Column(Text)
    status = Column(String(20))
    response = Column(Text)
    sent_by = Column(String(36))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Create tables
Base.metadata.create_all(bind=engine)

# ============== Pydantic Models ==============

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    role: str = "STAFF"

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    role: str
    status: str
    created_at: str
    employee_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TaskTemplateCreate(BaseModel):
    name: str
    default_category: Optional[str] = None
    default_priority: Optional[str] = None

class TaskTemplateResponse(BaseModel):
    id: str
    name: str
    default_category: Optional[str] = None
    default_priority: Optional[str] = None
    is_active: bool
    created_at: str

class CategoryCreate(BaseModel):
    name: str
    color: Optional[str] = "#6B7280"

class CategoryResponse(BaseModel):
    id: str
    name: str
    color: str
    is_active: bool
    created_at: str

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str = "Other"
    priority: str = "MEDIUM"
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    priority: str
    due_date: Optional[str]
    status: str
    created_by: str
    created_by_name: str
    assigned_to: Optional[str]
    assigned_to_name: Optional[str]
    created_at: str
    updated_at: str

class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: str
    task_id: str
    user_id: str
    user_name: str
    content: str
    created_at: str

class ActivityLogResponse(BaseModel):
    id: str
    task_id: str
    user_id: str
    user_name: str
    action: str
    details: str
    created_at: str

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    task_id: Optional[str] = None
    is_read: bool
    created_at: str

class AttachmentResponse(BaseModel):
    id: str
    task_id: str
    filename: str
    content_type: str
    file_size: Optional[int] = None
    uploaded_by_name: str
    created_at: str
    url: str
    thumbnail_url: Optional[str] = None

class DashboardStats(BaseModel):
    total_tasks: int
    in_progress: int
    completed: int
    verified: int
    tasks_to_assign: Optional[int] = None
    tasks_to_verify: Optional[int] = None
    total_staff: Optional[int] = None

# ============== Database Dependency ==============

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============== Auth Helpers ==============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        if user.status != "ACTIVE":
            raise HTTPException(status_code=401, detail="User is inactive")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

# ============== Helper Functions ==============

def log_activity(db: Session, task_id: str, user_id: str, user_name: str, action: str, details: str):
    log_entry = TaskActivityLog(
        id=str(uuid.uuid4()),
        task_id=task_id,
        user_id=user_id,
        user_name=user_name,
        action=action,
        details=details
    )
    db.add(log_entry)
    db.commit()

def create_notification(db: Session, user_id: str, notification_type: str, title: str, message: str, task_id: str = None):
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        task_id=task_id
    )
    db.add(notification)
    db.commit()

def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone or "",
        role=user.role,
        status=user.status,
        created_at=user.created_at.isoformat() if user.created_at else "",
        employee_id=user.employee_id
    )

def task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description or "",
        category=task.category or "Other",
        priority=task.priority or "MEDIUM",
        due_date=task.due_date.isoformat() if task.due_date else None,
        status=task.status,
        created_by=task.created_by,
        created_by_name=task.created_by_name or "",
        assigned_to=task.assigned_to,
        assigned_to_name=task.assigned_to_name,
        created_at=task.created_at.isoformat() if task.created_at else "",
        updated_at=task.updated_at.isoformat() if task.updated_at else ""
    )

def optimize_image(file_path: Path, max_size: int = 1920) -> Path:
    """Optimize image and create thumbnail"""
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize if too large
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Save optimized
            optimized_path = file_path.with_suffix('.jpg')
            img.save(optimized_path, 'JPEG', quality=85, optimize=True)
            
            # Create thumbnail
            thumb_path = file_path.parent / f"thumb_{file_path.stem}.jpg"
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=75, optimize=True)
            
            return optimized_path, thumb_path
    except Exception as e:
        logger.error(f"Image optimization failed: {e}")
        return file_path, None

# ============== FastAPI App ==============

app = FastAPI(title="Zomoto Tasks API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# ============== AUTH ROUTES ==============

@api_router.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Account is inactive")
    
    access_token = create_access_token(data={"sub": user.id, "role": user.role})
    return TokenResponse(access_token=access_token, user=user_to_response(user))

@api_router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return user_to_response(current_user)

# ============== USER ROUTES ==============

@api_router.post("/users", response_model=UserResponse)
def create_user(user_data: UserCreate, current_user: User = Depends(require_roles(["OWNER"])), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        id=str(uuid.uuid4()),
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        password=get_password_hash(user_data.password),
        role=user_data.role,
        status="ACTIVE",
        created_by=current_user.id,
        employee_id=f"EMP{str(uuid.uuid4())[:8].upper()}"
    )
    db.add(user)
    db.commit()
    return user_to_response(user)

@api_router.get("/users", response_model=List[UserResponse])
def get_users(current_user: User = Depends(require_roles(["OWNER", "MANAGER"])), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role != "OWNER").all()
    return [user_to_response(u) for u in users]

@api_router.get("/users/staff", response_model=List[UserResponse])
def get_staff_users(current_user: User = Depends(require_roles(["OWNER", "MANAGER"])), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role == "STAFF", User.status == "ACTIVE").all()
    return [user_to_response(u) for u in users]

@api_router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: str, user_data: UserUpdate, current_user: User = Depends(require_roles(["OWNER"])), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for field, value in user_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value)
    db.commit()
    return user_to_response(user)

@api_router.delete("/users/{user_id}")
def deactivate_user(user_id: str, current_user: User = Depends(require_roles(["OWNER"])), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "INACTIVE"
    db.commit()
    return {"message": "User deactivated successfully"}

@api_router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, current_user: User = Depends(require_roles(["OWNER"])), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = get_password_hash("123456")
    db.commit()
    return {"message": "Password reset to 123456"}

# ============== CATEGORY ROUTES ==============

@api_router.post("/categories", response_model=CategoryResponse)
def create_category(category_data: CategoryCreate, current_user: User = Depends(require_roles(["OWNER", "MANAGER"])), db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.name.ilike(category_data.name), Category.is_active == True).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    category = Category(
        id=str(uuid.uuid4()),
        name=category_data.name,
        color=category_data.color or "#6B7280",
        created_by=current_user.id
    )
    db.add(category)
    db.commit()
    return CategoryResponse(id=category.id, name=category.name, color=category.color, is_active=category.is_active, created_at=category.created_at.isoformat())

@api_router.get("/categories", response_model=List[CategoryResponse])
def get_categories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    categories = db.query(Category).filter(Category.is_active == True).all()
    
    if not categories:
        defaults = [
            Category(id="cat-kitchen", name="Kitchen", color="#EF4444", is_active=True),
            Category(id="cat-cleaning", name="Cleaning", color="#10B981", is_active=True),
            Category(id="cat-maintenance", name="Maintenance", color="#F59E0B", is_active=True),
            Category(id="cat-other", name="Other", color="#6B7280", is_active=True),
        ]
        for cat in defaults:
            db.add(cat)
        db.commit()
        categories = defaults
    
    return [CategoryResponse(id=c.id, name=c.name, color=c.color, is_active=c.is_active, created_at=c.created_at.isoformat() if c.created_at else "") for c in categories]

@api_router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: str, category_data: CategoryCreate, current_user: User = Depends(require_roles(["OWNER", "MANAGER"])), db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    category.name = category_data.name
    if category_data.color:
        category.color = category_data.color
    db.commit()
    return CategoryResponse(id=category.id, name=category.name, color=category.color, is_active=category.is_active, created_at=category.created_at.isoformat() if category.created_at else "")

@api_router.delete("/categories/{category_id}")
def delete_category(category_id: str, current_user: User = Depends(require_roles(["OWNER", "MANAGER"])), db: Session = Depends(get_db)):
    tasks_using = db.query(Task).filter(Task.category == category_id).count()
    if tasks_using > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete - {tasks_using} tasks are using it")
    db.query(Category).filter(Category.id == category_id).update({"is_active": False})
    db.commit()
    return {"message": "Category deleted"}

# ============== TASK TEMPLATE ROUTES ==============

@api_router.post("/task-templates", response_model=TaskTemplateResponse)
def create_task_template(template_data: TaskTemplateCreate, current_user: User = Depends(require_roles(["OWNER", "MANAGER"])), db: Session = Depends(get_db)):
    existing = db.query(TaskTemplate).filter(TaskTemplate.name_lower == template_data.name.lower(), TaskTemplate.is_active == True).first()
    if existing:
        raise HTTPException(status_code=400, detail="Task template already exists")
    
    template = TaskTemplate(
        id=str(uuid.uuid4()),
        name=template_data.name,
        name_lower=template_data.name.lower(),
        default_category=template_data.default_category,
        default_priority=template_data.default_priority,
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    return TaskTemplateResponse(id=template.id, name=template.name, default_category=template.default_category, default_priority=template.default_priority, is_active=template.is_active, created_at=template.created_at.isoformat())

@api_router.get("/task-templates", response_model=List[TaskTemplateResponse])
def get_task_templates(search: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(TaskTemplate).filter(TaskTemplate.is_active == True)
    if search:
        query = query.filter(TaskTemplate.name_lower.like(f"%{search.lower()}%"))
    templates = query.all()
    return [TaskTemplateResponse(id=t.id, name=t.name, default_category=t.default_category, default_priority=t.default_priority, is_active=t.is_active, created_at=t.created_at.isoformat() if t.created_at else "") for t in templates]

@api_router.delete("/task-templates/{template_id}")
def delete_task_template(template_id: str, current_user: User = Depends(require_roles(["OWNER", "MANAGER"])), db: Session = Depends(get_db)):
    db.query(TaskTemplate).filter(TaskTemplate.id == template_id).update({"is_active": False})
    db.commit()
    return {"message": "Task template deleted"}

# ============== TASK ROUTES ==============

@api_router.post("/tasks", response_model=TaskResponse)
def create_task(task_data: TaskCreate, current_user: User = Depends(require_roles(["OWNER", "MANAGER"])), db: Session = Depends(get_db)):
    assigned_to_name = None
    status = "CREATED"
    
    if task_data.assigned_to:
        assigned_user = db.query(User).filter(User.id == task_data.assigned_to).first()
        if assigned_user:
            assigned_to_name = assigned_user.name
            status = "ASSIGNED"
    
    due_date = None
    if task_data.due_date:
        try:
            due_date = datetime.fromisoformat(task_data.due_date.replace('Z', '+00:00'))
        except:
            pass
    
    task = Task(
        id=str(uuid.uuid4()),
        title=task_data.title,
        description=task_data.description or "",
        category=task_data.category,
        priority=task_data.priority,
        due_date=due_date,
        status=status,
        created_by=current_user.id,
        created_by_name=current_user.name,
        assigned_to=task_data.assigned_to,
        assigned_to_name=assigned_to_name
    )
    db.add(task)
    db.commit()
    
    log_activity(db, task.id, current_user.id, current_user.name, "CREATED", f"Task '{task.title}' created")
    
    if task_data.assigned_to:
        log_activity(db, task.id, current_user.id, current_user.name, "ASSIGNED", f"Task assigned to {assigned_to_name}")
        create_notification(db, task_data.assigned_to, "TASK_ASSIGNED", "New Task Assigned", f"You have been assigned: {task.title}", task.id)
    
    return task_to_response(task)

@api_router.get("/tasks", response_model=List[TaskResponse])
def get_tasks(status: Optional[str] = None, assigned_to: Optional[str] = None, category: Optional[str] = None, priority: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Task)
    
    if current_user.role == "STAFF":
        query = query.filter(Task.assigned_to == current_user.id)
    elif assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    
    if status:
        query = query.filter(Task.status == status)
    if category:
        query = query.filter(Task.category == category)
    if priority:
        query = query.filter(Task.priority == priority)
    
    tasks = query.order_by(Task.created_at.desc()).all()
    return [task_to_response(t) for t in tasks]

@api_router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if current_user.role == "STAFF" and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return task_to_response(task)

@api_router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: str, task_data: TaskUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if current_user.role == "STAFF":
        if task.assigned_to != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if task_data.status:
            valid_transitions = {"ASSIGNED": ["IN_PROGRESS"], "IN_PROGRESS": ["COMPLETED"]}
            if task_data.status not in valid_transitions.get(task.status, []):
                raise HTTPException(status_code=400, detail=f"Invalid status transition from {task.status}")
            task.status = task_data.status
            log_activity(db, task_id, current_user.id, current_user.name, "STATUS_CHANGED", f"Status changed to {task_data.status}")
            
            if task_data.status == "COMPLETED" and task.created_by:
                create_notification(db, task.created_by, "TASK_COMPLETED", "Task Completed", f"Task '{task.title}' has been completed", task_id)
    else:
        if task_data.title:
            task.title = task_data.title
        if task_data.description is not None:
            task.description = task_data.description
        if task_data.category:
            task.category = task_data.category
        if task_data.priority:
            task.priority = task_data.priority
        if task_data.due_date:
            try:
                task.due_date = datetime.fromisoformat(task_data.due_date.replace('Z', '+00:00'))
            except:
                pass
        if task_data.status:
            task.status = task_data.status
            log_activity(db, task_id, current_user.id, current_user.name, "STATUS_CHANGED", f"Status changed to {task_data.status}")
        if task_data.assigned_to:
            assigned_user = db.query(User).filter(User.id == task_data.assigned_to).first()
            if assigned_user:
                task.assigned_to = task_data.assigned_to
                task.assigned_to_name = assigned_user.name
                if task.status == "CREATED":
                    task.status = "ASSIGNED"
                log_activity(db, task_id, current_user.id, current_user.name, "REASSIGNED", f"Task reassigned to {assigned_user.name}")
                create_notification(db, task_data.assigned_to, "TASK_ASSIGNED", "Task Assigned", f"You have been assigned: {task.title}", task_id)
    
    db.commit()
    return task_to_response(task)

@api_router.delete("/tasks/{task_id}")
def delete_task(task_id: str, current_user: User = Depends(require_roles(["OWNER", "MANAGER"])), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.query(TaskComment).filter(TaskComment.task_id == task_id).delete()
    db.query(TaskAttachment).filter(TaskAttachment.task_id == task_id).delete()
    db.query(TaskActivityLog).filter(TaskActivityLog.task_id == task_id).delete()
    db.query(Notification).filter(Notification.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}

@api_router.post("/tasks/{task_id}/verify", response_model=TaskResponse)
def verify_task(task_id: str, current_user: User = Depends(require_roles(["OWNER", "MANAGER"])), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Only completed tasks can be verified")
    
    task.status = "VERIFIED"
    log_activity(db, task_id, current_user.id, current_user.name, "VERIFIED", "Task verified")
    
    if task.assigned_to:
        create_notification(db, task.assigned_to, "TASK_VERIFIED", "Task Verified", f"Your task '{task.title}' has been verified", task_id)
    
    db.commit()
    return task_to_response(task)

# ============== COMMENTS ROUTES ==============

@api_router.post("/tasks/{task_id}/comments", response_model=CommentResponse)
def add_comment(task_id: str, comment_data: CommentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if current_user.role == "STAFF" and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    comment = TaskComment(
        id=str(uuid.uuid4()),
        task_id=task_id,
        user_id=current_user.id,
        user_name=current_user.name,
        content=comment_data.content
    )
    db.add(comment)
    log_activity(db, task_id, current_user.id, current_user.name, "COMMENT_ADDED", f"Comment: {comment_data.content[:50]}...")
    db.commit()
    
    return CommentResponse(id=comment.id, task_id=comment.task_id, user_id=comment.user_id, user_name=comment.user_name, content=comment.content, created_at=comment.created_at.isoformat())

@api_router.get("/tasks/{task_id}/comments", response_model=List[CommentResponse])
def get_comments(task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.desc()).all()
    return [CommentResponse(id=c.id, task_id=c.task_id, user_id=c.user_id, user_name=c.user_name or "", content=c.content, created_at=c.created_at.isoformat() if c.created_at else "") for c in comments]

# ============== ACTIVITY LOG ROUTES ==============

@api_router.get("/tasks/{task_id}/activity", response_model=List[ActivityLogResponse])
def get_activity_log(task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(TaskActivityLog).filter(TaskActivityLog.task_id == task_id).order_by(TaskActivityLog.created_at.desc()).all()
    return [ActivityLogResponse(id=l.id, task_id=l.task_id, user_id=l.user_id, user_name=l.user_name or "", action=l.action, details=l.details or "", created_at=l.created_at.isoformat() if l.created_at else "") for l in logs]

# ============== ATTACHMENTS ROUTES ==============

@api_router.post("/tasks/{task_id}/attachments")
def upload_attachment(task_id: str, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if current_user.role == "STAFF" and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    upload_dir = ROOT_DIR / "uploads" / task_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix.lower()
    file_path = upload_dir / f"{file_id}{file_ext}"
    
    content = file.file.read()
    with open(file_path, 'wb') as f:
        f.write(content)
    
    file_size = len(content)
    thumbnail_path = None
    
    # Optimize if image
    if file.content_type and file.content_type.startswith('image/'):
        try:
            optimized_path, thumb_path = optimize_image(file_path)
            if optimized_path != file_path:
                file_path.unlink(missing_ok=True)
                file_path = optimized_path
            thumbnail_path = str(thumb_path) if thumb_path else None
        except Exception as e:
            logger.error(f"Image optimization error: {e}")
    
    attachment = TaskAttachment(
        id=file_id,
        task_id=task_id,
        filename=file.filename,
        file_path=str(file_path),
        content_type=file.content_type,
        file_size=file_size,
        thumbnail_path=thumbnail_path,
        uploaded_by=current_user.id,
        uploaded_by_name=current_user.name
    )
    db.add(attachment)
    log_activity(db, task_id, current_user.id, current_user.name, "ATTACHMENT_ADDED", f"File '{file.filename}' uploaded")
    db.commit()
    
    return {"id": file_id, "filename": file.filename, "message": "File uploaded successfully"}

@api_router.get("/tasks/{task_id}/attachments", response_model=List[AttachmentResponse])
def get_attachments(task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attachments = db.query(TaskAttachment).filter(TaskAttachment.task_id == task_id).all()
    return [AttachmentResponse(
        id=a.id,
        task_id=a.task_id,
        filename=a.filename,
        content_type=a.content_type or "application/octet-stream",
        file_size=a.file_size,
        uploaded_by_name=a.uploaded_by_name or "",
        created_at=a.created_at.isoformat() if a.created_at else "",
        url=f"/api/attachments/{a.id}",
        thumbnail_url=f"/api/attachments/{a.id}/thumbnail" if a.thumbnail_path else None
    ) for a in attachments]

@api_router.get("/attachments/{attachment_id}")
def get_attachment_file(attachment_id: str, db: Session = Depends(get_db)):
    attachment = db.query(TaskAttachment).filter(TaskAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    file_path = Path(attachment.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(path=file_path, filename=attachment.filename, media_type=attachment.content_type or "application/octet-stream")

@api_router.get("/attachments/{attachment_id}/thumbnail")
def get_attachment_thumbnail(attachment_id: str, db: Session = Depends(get_db)):
    attachment = db.query(TaskAttachment).filter(TaskAttachment.id == attachment_id).first()
    if not attachment or not attachment.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    thumb_path = Path(attachment.thumbnail_path)
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file not found")
    
    return FileResponse(path=thumb_path, media_type="image/jpeg")

# ============== NOTIFICATION ROUTES ==============

@api_router.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(unread_only: bool = False, limit: int = 50, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    return [NotificationResponse(id=n.id, user_id=n.user_id, type=n.type, title=n.title, message=n.message or "", task_id=n.task_id, is_read=n.is_read, created_at=n.created_at.isoformat() if n.created_at else "") for n in notifications]

@api_router.get("/notifications/unread-count")
def get_unread_count(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).count()
    return {"count": count}

@api_router.put("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).update({"is_read": True})
    db.commit()
    return {"message": "Notification marked as read"}

@api_router.put("/notifications/read-all")
def mark_all_notifications_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}

# ============== DASHBOARD ROUTES ==============

@api_router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Task)
    
    if current_user.role == "STAFF":
        query = query.filter(Task.assigned_to == current_user.id)
    
    total_tasks = query.count()
    in_progress = query.filter(Task.status == "IN_PROGRESS").count()
    completed = db.query(Task).filter(Task.status == "COMPLETED").count() if current_user.role == "STAFF" else query.filter(Task.status == "COMPLETED").count()
    verified = query.filter(Task.status == "VERIFIED").count()
    
    stats = DashboardStats(total_tasks=total_tasks, in_progress=in_progress, completed=completed, verified=verified)
    
    if current_user.role in ["OWNER", "MANAGER"]:
        stats.tasks_to_assign = db.query(Task).filter(Task.status == "CREATED").count()
        stats.tasks_to_verify = db.query(Task).filter(Task.status == "COMPLETED").count()
        stats.total_staff = db.query(User).filter(User.role == "STAFF", User.status == "ACTIVE").count()
    
    return stats

# ============== SEED DATA ==============

@api_router.post("/seed")
def seed_data(db: Session = Depends(get_db)):
    existing_owner = db.query(User).filter(User.email == "owner@zomoto.lk").first()
    if existing_owner:
        return {"message": "Data already seeded"}
    
    users = [
        User(id=str(uuid.uuid4()), name="Restaurant Owner", email="owner@zomoto.lk", phone="0771234567", password=get_password_hash("123456"), role="OWNER", status="ACTIVE", employee_id="EMP001"),
        User(id=str(uuid.uuid4()), name="Restaurant Manager", email="manager@zomoto.lk", phone="0772345678", password=get_password_hash("123456"), role="MANAGER", status="ACTIVE", employee_id="EMP002", salary_type="MONTHLY", basic_salary=50000),
        User(id=str(uuid.uuid4()), name="Staff Member", email="staff@zomoto.lk", phone="0773456789", password=get_password_hash("123456"), role="STAFF", status="ACTIVE", employee_id="EMP003", salary_type="MONTHLY", basic_salary=30000),
    ]
    for u in users:
        db.add(u)
    
    templates = [
        TaskTemplate(id=str(uuid.uuid4()), name="Clean Kitchen", name_lower="clean kitchen", default_category="Cleaning", default_priority="HIGH"),
        TaskTemplate(id=str(uuid.uuid4()), name="Stock Check", name_lower="stock check", default_category="Kitchen", default_priority="MEDIUM"),
        TaskTemplate(id=str(uuid.uuid4()), name="Equipment Maintenance", name_lower="equipment maintenance", default_category="Maintenance", default_priority="HIGH"),
        TaskTemplate(id=str(uuid.uuid4()), name="Table Setup", name_lower="table setup", default_category="Other", default_priority="MEDIUM"),
        TaskTemplate(id=str(uuid.uuid4()), name="Floor Mopping", name_lower="floor mopping", default_category="Cleaning", default_priority="LOW"),
    ]
    for t in templates:
        db.add(t)
    
    db.commit()
    return {"message": "Seed data created successfully", "users": ["owner@zomoto.lk", "manager@zomoto.lk", "staff@zomoto.lk"], "password": "123456"}

# ============== HEALTH CHECK ==============

@api_router.get("/health")
def health_check():
    return {"status": "healthy", "database": "MySQL", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
