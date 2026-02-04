from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
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
import base64
import aiofiles
from fastapi.responses import FileResponse

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'zomoto-tasks-secret-key-2024')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI(title="Zomoto Tasks API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== MODELS ==============

class UserRole:
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    STAFF = "STAFF"

class TaskStatus:
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"

class TaskPriority:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class TaskCategory:
    KITCHEN = "Kitchen"
    CLEANING = "Cleaning"
    MAINTENANCE = "Maintenance"
    OTHER = "Other"

# Pydantic Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    role: str = UserRole.STAFF

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

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str = TaskCategory.OTHER
    priority: str = TaskPriority.MEDIUM
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

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict

class DashboardStats(BaseModel):
    total_tasks: int
    in_progress: int
    completed: int
    verified: int
    tasks_to_assign: Optional[int] = None
    tasks_to_verify: Optional[int] = None
    total_staff: Optional[int] = None

# ============== AUTH HELPERS ==============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        if user.get("status") != "ACTIVE":
            raise HTTPException(status_code=401, detail="User is inactive")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_roles(allowed_roles: List[str]):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

# ============== ACTIVITY LOG HELPER ==============

async def log_activity(task_id: str, user_id: str, user_name: str, action: str, details: str):
    log_entry = {
        "id": str(uuid.uuid4()),
        "task_id": task_id,
        "user_id": user_id,
        "user_name": user_name,
        "action": action,
        "details": details,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.task_activity_logs.insert_one(log_entry)

# ============== AUTH ROUTES ==============

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = await db.users.find_one({"email": request.email}, {"_id": 0})
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("status") != "ACTIVE":
        raise HTTPException(status_code=401, detail="Account is inactive")
    
    access_token = create_access_token(data={"sub": user["id"], "role": user["role"]})
    
    user_response = UserResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        phone=user["phone"],
        role=user["role"],
        status=user["status"],
        created_at=user["created_at"],
        employee_id=user.get("employee_id")
    )
    
    return TokenResponse(access_token=access_token, user=user_response)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
        phone=current_user["phone"],
        role=current_user["role"],
        status=current_user["status"],
        created_at=current_user["created_at"],
        employee_id=current_user.get("employee_id")
    )

# ============== USER MANAGEMENT ROUTES (OWNER ONLY) ==============

@api_router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate, current_user: dict = Depends(require_roles([UserRole.OWNER]))):
    # Check if email already exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = {
        "id": str(uuid.uuid4()),
        "name": user_data.name,
        "email": user_data.email,
        "phone": user_data.phone,
        "password": get_password_hash(user_data.password),
        "role": user_data.role,
        "status": "ACTIVE",
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "employee_id": f"EMP{str(uuid.uuid4())[:8].upper()}",
        "salary_type": None,
        "basic_salary": None
    }
    
    await db.users.insert_one(user)
    
    return UserResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        phone=user["phone"],
        role=user["role"],
        status=user["status"],
        created_at=user["created_at"],
        employee_id=user.get("employee_id")
    )

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_roles([UserRole.OWNER, UserRole.MANAGER]))):
    users = await db.users.find({"role": {"$ne": UserRole.OWNER}}, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(
        id=u["id"],
        name=u["name"],
        email=u["email"],
        phone=u["phone"],
        role=u["role"],
        status=u["status"],
        created_at=u["created_at"],
        employee_id=u.get("employee_id")
    ) for u in users]

@api_router.get("/users/staff", response_model=List[UserResponse])
async def get_staff_users(current_user: dict = Depends(require_roles([UserRole.OWNER, UserRole.MANAGER]))):
    users = await db.users.find({"role": UserRole.STAFF, "status": "ACTIVE"}, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(
        id=u["id"],
        name=u["name"],
        email=u["email"],
        phone=u["phone"],
        role=u["role"],
        status=u["status"],
        created_at=u["created_at"],
        employee_id=u.get("employee_id")
    ) for u in users]

@api_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_data: UserUpdate, current_user: dict = Depends(require_roles([UserRole.OWNER]))):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {k: v for k, v in user_data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return UserResponse(
        id=updated_user["id"],
        name=updated_user["name"],
        email=updated_user["email"],
        phone=updated_user["phone"],
        role=updated_user["role"],
        status=updated_user["status"],
        created_at=updated_user["created_at"],
        employee_id=updated_user.get("employee_id")
    )

@api_router.delete("/users/{user_id}")
async def deactivate_user(user_id: str, current_user: dict = Depends(require_roles([UserRole.OWNER]))):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Soft delete - just deactivate
    await db.users.update_one(
        {"id": user_id}, 
        {"$set": {"status": "INACTIVE", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "User deactivated successfully"}

@api_router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: str, current_user: dict = Depends(require_roles([UserRole.OWNER]))):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Reset to default password
    new_password = "123456"
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"password": get_password_hash(new_password), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Password reset to 123456"}

# ============== TASK LIBRARY ROUTES ==============

@api_router.post("/task-templates", response_model=TaskTemplateResponse)
async def create_task_template(template_data: TaskTemplateCreate, current_user: dict = Depends(require_roles([UserRole.OWNER, UserRole.MANAGER]))):
    # Check if name already exists
    existing = await db.task_templates.find_one({"name": template_data.name.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Task template with this name already exists")
    
    template = {
        "id": str(uuid.uuid4()),
        "name": template_data.name,
        "name_lower": template_data.name.lower(),
        "default_category": template_data.default_category,
        "default_priority": template_data.default_priority,
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.task_templates.insert_one(template)
    
    return TaskTemplateResponse(
        id=template["id"],
        name=template["name"],
        default_category=template["default_category"],
        default_priority=template["default_priority"],
        is_active=template["is_active"],
        created_at=template["created_at"]
    )

@api_router.get("/task-templates", response_model=List[TaskTemplateResponse])
async def get_task_templates(
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {"is_active": True}
    if search:
        query["name_lower"] = {"$regex": search.lower(), "$options": "i"}
    
    templates = await db.task_templates.find(query, {"_id": 0}).to_list(100)
    return [TaskTemplateResponse(
        id=t["id"],
        name=t["name"],
        default_category=t.get("default_category"),
        default_priority=t.get("default_priority"),
        is_active=t["is_active"],
        created_at=t["created_at"]
    ) for t in templates]

@api_router.delete("/task-templates/{template_id}")
async def delete_task_template(template_id: str, current_user: dict = Depends(require_roles([UserRole.OWNER, UserRole.MANAGER]))):
    await db.task_templates.update_one({"id": template_id}, {"$set": {"is_active": False}})
    return {"message": "Task template deleted"}

# ============== TASK ROUTES ==============

@api_router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate, current_user: dict = Depends(require_roles([UserRole.OWNER, UserRole.MANAGER]))):
    assigned_to_name = None
    status = TaskStatus.CREATED
    
    if task_data.assigned_to:
        assigned_user = await db.users.find_one({"id": task_data.assigned_to}, {"_id": 0})
        if assigned_user:
            assigned_to_name = assigned_user["name"]
            status = TaskStatus.ASSIGNED
    
    task = {
        "id": str(uuid.uuid4()),
        "title": task_data.title,
        "description": task_data.description or "",
        "category": task_data.category,
        "priority": task_data.priority,
        "due_date": task_data.due_date,
        "status": status,
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "assigned_to": task_data.assigned_to,
        "assigned_to_name": assigned_to_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.tasks.insert_one(task)
    
    # Log activity
    await log_activity(task["id"], current_user["id"], current_user["name"], "CREATED", f"Task '{task['title']}' created")
    
    if task_data.assigned_to:
        await log_activity(task["id"], current_user["id"], current_user["name"], "ASSIGNED", f"Task assigned to {assigned_to_name}")
    
    return TaskResponse(**{k: v for k, v in task.items() if k != "_id"})

@api_router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    
    # Staff can only see their own tasks
    if current_user["role"] == UserRole.STAFF:
        query["assigned_to"] = current_user["id"]
    elif assigned_to:
        query["assigned_to"] = assigned_to
    
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if priority:
        query["priority"] = priority
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [TaskResponse(**t) for t in tasks]

@api_router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Staff can only view their own tasks
    if current_user["role"] == UserRole.STAFF and task.get("assigned_to") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return TaskResponse(**task)

@api_router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task_data: TaskUpdate, current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Permission checks
    if current_user["role"] == UserRole.STAFF:
        # Staff can only update status on their own tasks
        if task.get("assigned_to") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Staff can only change status: ASSIGNED -> IN_PROGRESS -> COMPLETED
        update_data = {}
        if task_data.status:
            valid_transitions = {
                TaskStatus.ASSIGNED: [TaskStatus.IN_PROGRESS],
                TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED]
            }
            current_status = task["status"]
            allowed = valid_transitions.get(current_status, [])
            if task_data.status not in allowed:
                raise HTTPException(status_code=400, detail=f"Invalid status transition from {current_status} to {task_data.status}")
            update_data["status"] = task_data.status
    else:
        # Owner/Manager can update everything
        update_data = {k: v for k, v in task_data.model_dump().items() if v is not None}
        
        # Handle assigned_to updates
        if task_data.assigned_to:
            assigned_user = await db.users.find_one({"id": task_data.assigned_to}, {"_id": 0})
            if assigned_user:
                update_data["assigned_to_name"] = assigned_user["name"]
                if task["status"] == TaskStatus.CREATED:
                    update_data["status"] = TaskStatus.ASSIGNED
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.tasks.update_one({"id": task_id}, {"$set": update_data})
        
        # Log activity
        if "status" in update_data:
            await log_activity(task_id, current_user["id"], current_user["name"], "STATUS_CHANGED", f"Status changed to {update_data['status']}")
        if "assigned_to" in update_data:
            await log_activity(task_id, current_user["id"], current_user["name"], "REASSIGNED", f"Task reassigned to {update_data.get('assigned_to_name', 'Unknown')}")
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return TaskResponse(**updated_task)

@api_router.post("/tasks/{task_id}/verify", response_model=TaskResponse)
async def verify_task(task_id: str, current_user: dict = Depends(require_roles([UserRole.OWNER, UserRole.MANAGER]))):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Only completed tasks can be verified")
    
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {"status": TaskStatus.VERIFIED, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    await log_activity(task_id, current_user["id"], current_user["name"], "VERIFIED", "Task verified")
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return TaskResponse(**updated_task)

# ============== COMMENTS ROUTES ==============

@api_router.post("/tasks/{task_id}/comments", response_model=CommentResponse)
async def add_comment(task_id: str, comment_data: CommentCreate, current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Staff can only comment on their own tasks
    if current_user["role"] == UserRole.STAFF and task.get("assigned_to") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    comment = {
        "id": str(uuid.uuid4()),
        "task_id": task_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "content": comment_data.content,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.task_comments.insert_one(comment)
    await log_activity(task_id, current_user["id"], current_user["name"], "COMMENT_ADDED", f"Comment: {comment_data.content[:50]}...")
    
    return CommentResponse(**{k: v for k, v in comment.items() if k != "_id"})

@api_router.get("/tasks/{task_id}/comments", response_model=List[CommentResponse])
async def get_comments(task_id: str, current_user: dict = Depends(get_current_user)):
    comments = await db.task_comments.find({"task_id": task_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [CommentResponse(**c) for c in comments]

# ============== ACTIVITY LOG ROUTES ==============

@api_router.get("/tasks/{task_id}/activity", response_model=List[ActivityLogResponse])
async def get_activity_log(task_id: str, current_user: dict = Depends(get_current_user)):
    logs = await db.task_activity_logs.find({"task_id": task_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [ActivityLogResponse(**log) for log in logs]

# ============== ATTACHMENTS ROUTES ==============

@api_router.post("/tasks/{task_id}/attachments")
async def upload_attachment(
    task_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Staff can only upload to their own tasks
    if current_user["role"] == UserRole.STAFF and task.get("assigned_to") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Save file
    upload_dir = ROOT_DIR / "uploads" / task_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix
    file_path = upload_dir / f"{file_id}{file_ext}"
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    attachment = {
        "id": file_id,
        "task_id": task_id,
        "filename": file.filename,
        "file_path": str(file_path),
        "content_type": file.content_type,
        "uploaded_by": current_user["id"],
        "uploaded_by_name": current_user["name"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.task_attachments.insert_one(attachment)
    await log_activity(task_id, current_user["id"], current_user["name"], "ATTACHMENT_ADDED", f"File '{file.filename}' uploaded")
    
    return {"id": file_id, "filename": file.filename, "message": "File uploaded successfully"}

@api_router.get("/tasks/{task_id}/attachments")
async def get_attachments(task_id: str, current_user: dict = Depends(get_current_user)):
    attachments = await db.task_attachments.find({"task_id": task_id}, {"_id": 0}).to_list(100)
    return [{"id": a["id"], "filename": a["filename"], "uploaded_by_name": a["uploaded_by_name"], "created_at": a["created_at"]} for a in attachments]

# ============== DASHBOARD ROUTES ==============

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    query = {}
    
    if current_user["role"] == UserRole.STAFF:
        query["assigned_to"] = current_user["id"]
    
    total_tasks = await db.tasks.count_documents(query)
    in_progress = await db.tasks.count_documents({**query, "status": TaskStatus.IN_PROGRESS})
    completed = await db.tasks.count_documents({**query, "status": TaskStatus.COMPLETED})
    verified = await db.tasks.count_documents({**query, "status": TaskStatus.VERIFIED})
    
    stats = DashboardStats(
        total_tasks=total_tasks,
        in_progress=in_progress,
        completed=completed,
        verified=verified
    )
    
    if current_user["role"] in [UserRole.OWNER, UserRole.MANAGER]:
        stats.tasks_to_assign = await db.tasks.count_documents({"status": TaskStatus.CREATED})
        stats.tasks_to_verify = await db.tasks.count_documents({"status": TaskStatus.COMPLETED})
        stats.total_staff = await db.users.count_documents({"role": UserRole.STAFF, "status": "ACTIVE"})
    
    return stats

# ============== PUSH NOTIFICATION ROUTES ==============

@api_router.post("/push/subscribe")
async def subscribe_push(subscription: PushSubscription, current_user: dict = Depends(get_current_user)):
    sub_data = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "endpoint": subscription.endpoint,
        "keys": subscription.keys,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Remove old subscriptions for this user
    await db.push_subscriptions.delete_many({"user_id": current_user["id"]})
    await db.push_subscriptions.insert_one(sub_data)
    
    return {"message": "Subscription saved"}

@api_router.delete("/push/unsubscribe")
async def unsubscribe_push(current_user: dict = Depends(get_current_user)):
    await db.push_subscriptions.delete_many({"user_id": current_user["id"]})
    return {"message": "Unsubscribed from push notifications"}

# ============== SMS NOTIFICATION (notify.lk) ==============

@api_router.post("/notifications/sms")
async def send_sms_notification(
    phone: str = Form(...),
    message: str = Form(...),
    current_user: dict = Depends(require_roles([UserRole.OWNER, UserRole.MANAGER]))
):
    # notify.lk integration
    notify_user_id = os.environ.get('NOTIFY_LK_USER_ID')
    notify_api_key = os.environ.get('NOTIFY_LK_API_KEY')
    notify_sender_id = os.environ.get('NOTIFY_LK_SENDER_ID', 'NotifyDEMO')
    
    if not notify_user_id or not notify_api_key:
        raise HTTPException(status_code=500, detail="SMS service not configured")
    
    # Format phone number (remove leading 0, add 94 for Sri Lanka)
    formatted_phone = phone.lstrip('0')
    if not formatted_phone.startswith('94'):
        formatted_phone = '94' + formatted_phone
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://app.notify.lk/api/v1/send",
                data={
                    "user_id": notify_user_id,
                    "api_key": notify_api_key,
                    "sender_id": notify_sender_id,
                    "to": formatted_phone,
                    "message": message
                }
            )
            
            # Log notification
            await db.notification_logs.insert_one({
                "id": str(uuid.uuid4()),
                "type": "SMS",
                "recipient": phone,
                "message": message,
                "status": "SENT" if response.status_code == 200 else "FAILED",
                "response": response.text,
                "sent_by": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            return {"message": "SMS sent", "status": response.status_code}
    except Exception as e:
        logger.error(f"SMS sending failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send SMS")

# ============== SEED DATA ==============

@api_router.post("/seed")
async def seed_data():
    # Check if already seeded
    existing_owner = await db.users.find_one({"email": "owner@zomoto.lk"})
    if existing_owner:
        return {"message": "Data already seeded"}
    
    # Create demo users
    users = [
        {
            "id": str(uuid.uuid4()),
            "name": "Restaurant Owner",
            "email": "owner@zomoto.lk",
            "phone": "0771234567",
            "password": get_password_hash("123456"),
            "role": UserRole.OWNER,
            "status": "ACTIVE",
            "created_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "employee_id": "EMP001",
            "salary_type": None,
            "basic_salary": None
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Restaurant Manager",
            "email": "manager@zomoto.lk",
            "phone": "0772345678",
            "password": get_password_hash("123456"),
            "role": UserRole.MANAGER,
            "status": "ACTIVE",
            "created_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "employee_id": "EMP002",
            "salary_type": "MONTHLY",
            "basic_salary": 50000
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Staff Member",
            "email": "staff@zomoto.lk",
            "phone": "0773456789",
            "password": get_password_hash("123456"),
            "role": UserRole.STAFF,
            "status": "ACTIVE",
            "created_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "employee_id": "EMP003",
            "salary_type": "MONTHLY",
            "basic_salary": 30000
        }
    ]
    
    await db.users.insert_many(users)
    
    # Create task templates
    templates = [
        {"id": str(uuid.uuid4()), "name": "Clean Kitchen", "name_lower": "clean kitchen", "default_category": TaskCategory.CLEANING, "default_priority": TaskPriority.HIGH, "is_active": True, "created_by": users[0]["id"], "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "Stock Check", "name_lower": "stock check", "default_category": TaskCategory.KITCHEN, "default_priority": TaskPriority.MEDIUM, "is_active": True, "created_by": users[0]["id"], "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "Equipment Maintenance", "name_lower": "equipment maintenance", "default_category": TaskCategory.MAINTENANCE, "default_priority": TaskPriority.HIGH, "is_active": True, "created_by": users[0]["id"], "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "Table Setup", "name_lower": "table setup", "default_category": TaskCategory.OTHER, "default_priority": TaskPriority.MEDIUM, "is_active": True, "created_by": users[0]["id"], "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "Floor Mopping", "name_lower": "floor mopping", "default_category": TaskCategory.CLEANING, "default_priority": TaskPriority.LOW, "is_active": True, "created_by": users[0]["id"], "created_at": datetime.now(timezone.utc).isoformat()},
    ]
    
    await db.task_templates.insert_many(templates)
    
    # Create sample tasks
    tasks = [
        {
            "id": str(uuid.uuid4()),
            "title": "Clean Kitchen Area",
            "description": "Deep clean the entire kitchen area including all surfaces and equipment",
            "category": TaskCategory.CLEANING,
            "priority": TaskPriority.HIGH,
            "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "status": TaskStatus.ASSIGNED,
            "created_by": users[1]["id"],
            "created_by_name": users[1]["name"],
            "assigned_to": users[2]["id"],
            "assigned_to_name": users[2]["name"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Daily Stock Check",
            "description": "Check and record all inventory levels",
            "category": TaskCategory.KITCHEN,
            "priority": TaskPriority.MEDIUM,
            "due_date": datetime.now(timezone.utc).isoformat(),
            "status": TaskStatus.IN_PROGRESS,
            "created_by": users[1]["id"],
            "created_by_name": users[1]["name"],
            "assigned_to": users[2]["id"],
            "assigned_to_name": users[2]["name"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Fix Broken Chair",
            "description": "Repair the broken chair in dining area",
            "category": TaskCategory.MAINTENANCE,
            "priority": TaskPriority.LOW,
            "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "status": TaskStatus.CREATED,
            "created_by": users[0]["id"],
            "created_by_name": users[0]["name"],
            "assigned_to": None,
            "assigned_to_name": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.tasks.insert_many(tasks)
    
    return {"message": "Seed data created successfully", "users": ["owner@zomoto.lk", "manager@zomoto.lk", "staff@zomoto.lk"], "password": "123456"}

# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
