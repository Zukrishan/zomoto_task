from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
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
import aiofiles
from PIL import Image

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
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict

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

# ============== Helper Functions ==============

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

async def create_notification(user_id: str, notification_type: str, title: str, message: str, task_id: str = None):
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "task_id": task_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)

def optimize_image(file_path: Path, max_size: int = 1920):
    try:
        with Image.open(file_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            optimized_path = file_path.with_suffix('.jpg')
            img.save(optimized_path, 'JPEG', quality=85, optimize=True)
            thumb_path = file_path.parent / f"thumb_{file_path.stem}.jpg"
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=75, optimize=True)
            return optimized_path, thumb_path
    except Exception as e:
        logger.error(f"Image optimization failed: {e}")
        return file_path, None

# ============== AUTH ROUTES ==============

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = await db.users.find_one({"email": request.email}, {"_id": 0})
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("status") != "ACTIVE":
        raise HTTPException(status_code=401, detail="Account is inactive")
    
    access_token = create_access_token(data={"sub": user["id"], "role": user["role"]})
    user_response = UserResponse(id=user["id"], name=user["name"], email=user["email"], phone=user.get("phone", ""), role=user["role"], status=user["status"], created_at=user.get("created_at", ""), employee_id=user.get("employee_id"))
    return TokenResponse(access_token=access_token, user=user_response)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(id=current_user["id"], name=current_user["name"], email=current_user["email"], phone=current_user.get("phone", ""), role=current_user["role"], status=current_user["status"], created_at=current_user.get("created_at", ""), employee_id=current_user.get("employee_id"))

# ============== USER ROUTES ==============

@api_router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate, current_user: dict = Depends(require_roles(["OWNER"]))):
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
        "employee_id": f"EMP{str(uuid.uuid4())[:8].upper()}"
    }
    await db.users.insert_one(user)
    return UserResponse(id=user["id"], name=user["name"], email=user["email"], phone=user["phone"], role=user["role"], status=user["status"], created_at=user["created_at"], employee_id=user.get("employee_id"))

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    users = await db.users.find({"role": {"$ne": "OWNER"}}, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(id=u["id"], name=u["name"], email=u["email"], phone=u.get("phone", ""), role=u["role"], status=u["status"], created_at=u.get("created_at", ""), employee_id=u.get("employee_id")) for u in users]

@api_router.get("/users/staff", response_model=List[UserResponse])
async def get_staff_users(current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    users = await db.users.find({"role": "STAFF", "status": "ACTIVE"}, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(id=u["id"], name=u["name"], email=u["email"], phone=u.get("phone", ""), role=u["role"], status=u["status"], created_at=u.get("created_at", ""), employee_id=u.get("employee_id")) for u in users]

@api_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_data: UserUpdate, current_user: dict = Depends(require_roles(["OWNER"]))):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = {k: v for k, v in user_data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return UserResponse(id=updated_user["id"], name=updated_user["name"], email=updated_user["email"], phone=updated_user.get("phone", ""), role=updated_user["role"], status=updated_user["status"], created_at=updated_user.get("created_at", ""), employee_id=updated_user.get("employee_id"))

@api_router.delete("/users/{user_id}")
async def deactivate_user(user_id: str, current_user: dict = Depends(require_roles(["OWNER"]))):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"id": user_id}, {"$set": {"status": "INACTIVE", "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "User deactivated successfully"}

@api_router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: str, current_user: dict = Depends(require_roles(["OWNER"]))):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"id": user_id}, {"$set": {"password": get_password_hash("123456"), "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Password reset to 123456"}

# ============== CATEGORY ROUTES ==============

@api_router.post("/categories", response_model=CategoryResponse)
async def create_category(category_data: CategoryCreate, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    existing = await db.categories.find_one({"name": {"$regex": f"^{category_data.name}$", "$options": "i"}, "is_active": True})
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    category = {"id": str(uuid.uuid4()), "name": category_data.name, "color": category_data.color or "#6B7280", "is_active": True, "created_by": current_user["id"], "created_at": datetime.now(timezone.utc).isoformat()}
    await db.categories.insert_one(category)
    return CategoryResponse(id=category["id"], name=category["name"], color=category["color"], is_active=category["is_active"], created_at=category["created_at"])

@api_router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(current_user: dict = Depends(get_current_user)):
    categories = await db.categories.find({"is_active": True}, {"_id": 0}).to_list(100)
    if not categories:
        defaults = [
            {"id": "cat-kitchen", "name": "Kitchen", "color": "#EF4444", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": "cat-cleaning", "name": "Cleaning", "color": "#10B981", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": "cat-maintenance", "name": "Maintenance", "color": "#F59E0B", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": "cat-other", "name": "Other", "color": "#6B7280", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        ]
        await db.categories.insert_many(defaults)
        categories = defaults
    return [CategoryResponse(id=c["id"], name=c["name"], color=c["color"], is_active=c["is_active"], created_at=c.get("created_at", "")) for c in categories]

@api_router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: str, category_data: CategoryCreate, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    category = await db.categories.find_one({"id": category_id}, {"_id": 0})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    update_data = {"name": category_data.name}
    if category_data.color:
        update_data["color"] = category_data.color
    await db.categories.update_one({"id": category_id}, {"$set": update_data})
    updated = await db.categories.find_one({"id": category_id}, {"_id": 0})
    return CategoryResponse(id=updated["id"], name=updated["name"], color=updated["color"], is_active=updated["is_active"], created_at=updated.get("created_at", ""))

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    await db.categories.update_one({"id": category_id}, {"$set": {"is_active": False}})
    return {"message": "Category deleted"}

# ============== TASK TEMPLATE ROUTES ==============

@api_router.post("/task-templates", response_model=TaskTemplateResponse)
async def create_task_template(template_data: TaskTemplateCreate, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    existing = await db.task_templates.find_one({"name_lower": template_data.name.lower(), "is_active": True})
    if existing:
        raise HTTPException(status_code=400, detail="Task template already exists")
    template = {"id": str(uuid.uuid4()), "name": template_data.name, "name_lower": template_data.name.lower(), "default_category": template_data.default_category, "default_priority": template_data.default_priority, "is_active": True, "created_by": current_user["id"], "created_at": datetime.now(timezone.utc).isoformat()}
    await db.task_templates.insert_one(template)
    return TaskTemplateResponse(id=template["id"], name=template["name"], default_category=template["default_category"], default_priority=template["default_priority"], is_active=template["is_active"], created_at=template["created_at"])

@api_router.get("/task-templates", response_model=List[TaskTemplateResponse])
async def get_task_templates(search: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {"is_active": True}
    if search:
        query["name_lower"] = {"$regex": search.lower(), "$options": "i"}
    templates = await db.task_templates.find(query, {"_id": 0}).to_list(100)
    return [TaskTemplateResponse(id=t["id"], name=t["name"], default_category=t.get("default_category"), default_priority=t.get("default_priority"), is_active=t["is_active"], created_at=t.get("created_at", "")) for t in templates]

@api_router.delete("/task-templates/{template_id}")
async def delete_task_template(template_id: str, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    await db.task_templates.update_one({"id": template_id}, {"$set": {"is_active": False}})
    return {"message": "Task template deleted"}

# ============== TASK ROUTES ==============

@api_router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    assigned_to_name = None
    status = "CREATED"
    if task_data.assigned_to:
        assigned_user = await db.users.find_one({"id": task_data.assigned_to}, {"_id": 0})
        if assigned_user:
            assigned_to_name = assigned_user["name"]
            status = "ASSIGNED"
    
    task = {"id": str(uuid.uuid4()), "title": task_data.title, "description": task_data.description or "", "category": task_data.category, "priority": task_data.priority, "due_date": task_data.due_date, "status": status, "created_by": current_user["id"], "created_by_name": current_user["name"], "assigned_to": task_data.assigned_to, "assigned_to_name": assigned_to_name, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.tasks.insert_one(task)
    await log_activity(task["id"], current_user["id"], current_user["name"], "CREATED", f"Task '{task['title']}' created")
    if task_data.assigned_to:
        await log_activity(task["id"], current_user["id"], current_user["name"], "ASSIGNED", f"Task assigned to {assigned_to_name}")
        await create_notification(task_data.assigned_to, "TASK_ASSIGNED", "New Task Assigned", f"You have been assigned: {task['title']}", task["id"])
    return TaskResponse(**{k: v for k, v in task.items() if k != "_id"})

@api_router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(status: Optional[str] = None, assigned_to: Optional[str] = None, category: Optional[str] = None, priority: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == "STAFF":
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
    if current_user["role"] == "STAFF" and task.get("assigned_to") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return TaskResponse(**task)

@api_router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task_data: TaskUpdate, current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if current_user["role"] == "STAFF":
        if task.get("assigned_to") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        update_data = {}
        if task_data.status:
            valid_transitions = {"ASSIGNED": ["IN_PROGRESS"], "IN_PROGRESS": ["COMPLETED"]}
            if task_data.status not in valid_transitions.get(task["status"], []):
                raise HTTPException(status_code=400, detail=f"Invalid status transition from {task['status']}")
            update_data["status"] = task_data.status
            await log_activity(task_id, current_user["id"], current_user["name"], "STATUS_CHANGED", f"Status changed to {task_data.status}")
            if task_data.status == "COMPLETED" and task.get("created_by"):
                await create_notification(task["created_by"], "TASK_COMPLETED", "Task Completed", f"Task '{task['title']}' has been completed", task_id)
    else:
        update_data = {k: v for k, v in task_data.model_dump().items() if v is not None}
        if task_data.assigned_to:
            assigned_user = await db.users.find_one({"id": task_data.assigned_to}, {"_id": 0})
            if assigned_user:
                update_data["assigned_to_name"] = assigned_user["name"]
                if task["status"] == "CREATED":
                    update_data["status"] = "ASSIGNED"
                await log_activity(task_id, current_user["id"], current_user["name"], "REASSIGNED", f"Task reassigned to {assigned_user['name']}")
                await create_notification(task_data.assigned_to, "TASK_ASSIGNED", "Task Assigned", f"You have been assigned: {task['title']}", task_id)
        if task_data.status:
            await log_activity(task_id, current_user["id"], current_user["name"], "STATUS_CHANGED", f"Status changed to {task_data.status}")
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return TaskResponse(**updated_task)

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.tasks.delete_one({"id": task_id})
    await db.task_comments.delete_many({"task_id": task_id})
    await db.task_attachments.delete_many({"task_id": task_id})
    await db.task_activity_logs.delete_many({"task_id": task_id})
    return {"message": "Task deleted successfully"}

@api_router.post("/tasks/{task_id}/verify", response_model=TaskResponse)
async def verify_task(task_id: str, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "COMPLETED":
        raise HTTPException(status_code=400, detail="Only completed tasks can be verified")
    await db.tasks.update_one({"id": task_id}, {"$set": {"status": "VERIFIED", "updated_at": datetime.now(timezone.utc).isoformat()}})
    await log_activity(task_id, current_user["id"], current_user["name"], "VERIFIED", "Task verified")
    if task.get("assigned_to"):
        await create_notification(task["assigned_to"], "TASK_VERIFIED", "Task Verified", f"Your task '{task['title']}' has been verified", task_id)
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return TaskResponse(**updated_task)

# ============== COMMENTS ROUTES ==============

@api_router.post("/tasks/{task_id}/comments", response_model=CommentResponse)
async def add_comment(task_id: str, comment_data: CommentCreate, current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user["role"] == "STAFF" and task.get("assigned_to") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    comment = {"id": str(uuid.uuid4()), "task_id": task_id, "user_id": current_user["id"], "user_name": current_user["name"], "content": comment_data.content, "created_at": datetime.now(timezone.utc).isoformat()}
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
async def upload_attachment(task_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user["role"] == "STAFF" and task.get("assigned_to") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    upload_dir = ROOT_DIR / "uploads" / task_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix.lower()
    file_path = upload_dir / f"{file_id}{file_ext}"
    
    content = await file.read()
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    file_size = len(content)
    thumbnail_path = None
    
    if file.content_type and file.content_type.startswith('image/'):
        try:
            optimized_path, thumb_path = optimize_image(file_path)
            if optimized_path != file_path:
                file_path.unlink(missing_ok=True)
                file_path = optimized_path
            thumbnail_path = str(thumb_path) if thumb_path else None
        except Exception as e:
            logger.error(f"Image optimization error: {e}")
    
    attachment = {"id": file_id, "task_id": task_id, "filename": file.filename, "file_path": str(file_path), "content_type": file.content_type, "file_size": file_size, "thumbnail_path": thumbnail_path, "uploaded_by": current_user["id"], "uploaded_by_name": current_user["name"], "created_at": datetime.now(timezone.utc).isoformat()}
    await db.task_attachments.insert_one(attachment)
    await log_activity(task_id, current_user["id"], current_user["name"], "ATTACHMENT_ADDED", f"File '{file.filename}' uploaded")
    return {"id": file_id, "filename": file.filename, "message": "File uploaded successfully"}

@api_router.get("/tasks/{task_id}/attachments")
async def get_attachments(task_id: str, current_user: dict = Depends(get_current_user)):
    attachments = await db.task_attachments.find({"task_id": task_id}, {"_id": 0}).to_list(100)
    return [{"id": a["id"], "task_id": a["task_id"], "filename": a["filename"], "content_type": a.get("content_type", "application/octet-stream"), "file_size": a.get("file_size"), "uploaded_by_name": a.get("uploaded_by_name", ""), "created_at": a.get("created_at", ""), "url": f"/api/attachments/{a['id']}", "thumbnail_url": f"/api/attachments/{a['id']}/thumbnail" if a.get("thumbnail_path") else None} for a in attachments]

@api_router.get("/attachments/{attachment_id}")
async def get_attachment_file(attachment_id: str):
    attachment = await db.task_attachments.find_one({"id": attachment_id}, {"_id": 0})
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    file_path = Path(attachment["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=attachment["filename"], media_type=attachment.get("content_type", "application/octet-stream"))

@api_router.get("/attachments/{attachment_id}/thumbnail")
async def get_attachment_thumbnail(attachment_id: str):
    attachment = await db.task_attachments.find_one({"id": attachment_id}, {"_id": 0})
    if not attachment or not attachment.get("thumbnail_path"):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    thumb_path = Path(attachment["thumbnail_path"])
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file not found")
    return FileResponse(path=thumb_path, media_type="image/jpeg")

# ============== NOTIFICATION ROUTES ==============

@api_router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(unread_only: bool = False, limit: int = 50, current_user: dict = Depends(get_current_user)):
    query = {"user_id": current_user["id"]}
    if unread_only:
        query["is_read"] = False
    notifications = await db.notifications.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return [NotificationResponse(**n) for n in notifications]

@api_router.get("/notifications/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    count = await db.notifications.count_documents({"user_id": current_user["id"], "is_read": False})
    return {"count": count}

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    await db.notifications.update_one({"id": notification_id, "user_id": current_user["id"]}, {"$set": {"is_read": True}})
    return {"message": "Notification marked as read"}

@api_router.put("/notifications/read-all")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"user_id": current_user["id"], "is_read": False}, {"$set": {"is_read": True}})
    return {"message": "All notifications marked as read"}

# ============== DASHBOARD ROUTES ==============

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == "STAFF":
        query["assigned_to"] = current_user["id"]
    total_tasks = await db.tasks.count_documents(query)
    in_progress = await db.tasks.count_documents({**query, "status": "IN_PROGRESS"})
    completed = await db.tasks.count_documents({**query, "status": "COMPLETED"})
    verified = await db.tasks.count_documents({**query, "status": "VERIFIED"})
    stats = DashboardStats(total_tasks=total_tasks, in_progress=in_progress, completed=completed, verified=verified)
    if current_user["role"] in ["OWNER", "MANAGER"]:
        stats.tasks_to_assign = await db.tasks.count_documents({"status": "CREATED"})
        stats.tasks_to_verify = await db.tasks.count_documents({"status": "COMPLETED"})
        stats.total_staff = await db.users.count_documents({"role": "STAFF", "status": "ACTIVE"})
    return stats

# ============== SEED DATA ==============

@api_router.post("/seed")
async def seed_data():
    existing_owner = await db.users.find_one({"email": "owner@zomoto.lk"})
    if existing_owner:
        return {"message": "Data already seeded"}
    
    users = [
        {"id": str(uuid.uuid4()), "name": "Restaurant Owner", "email": "owner@zomoto.lk", "phone": "0771234567", "password": get_password_hash("123456"), "role": "OWNER", "status": "ACTIVE", "created_at": datetime.now(timezone.utc).isoformat(), "employee_id": "EMP001"},
        {"id": str(uuid.uuid4()), "name": "Restaurant Manager", "email": "manager@zomoto.lk", "phone": "0772345678", "password": get_password_hash("123456"), "role": "MANAGER", "status": "ACTIVE", "created_at": datetime.now(timezone.utc).isoformat(), "employee_id": "EMP002"},
        {"id": str(uuid.uuid4()), "name": "Staff Member", "email": "staff@zomoto.lk", "phone": "0773456789", "password": get_password_hash("123456"), "role": "STAFF", "status": "ACTIVE", "created_at": datetime.now(timezone.utc).isoformat(), "employee_id": "EMP003"},
    ]
    await db.users.insert_many(users)
    
    templates = [
        {"id": str(uuid.uuid4()), "name": "Clean Kitchen", "name_lower": "clean kitchen", "default_category": "Cleaning", "default_priority": "HIGH", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "Stock Check", "name_lower": "stock check", "default_category": "Kitchen", "default_priority": "MEDIUM", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "name": "Equipment Maintenance", "name_lower": "equipment maintenance", "default_category": "Maintenance", "default_priority": "HIGH", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
    ]
    await db.task_templates.insert_many(templates)
    return {"message": "Seed data created successfully", "users": ["owner@zomoto.lk", "manager@zomoto.lk", "staff@zomoto.lk"], "password": "123456"}

# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "database": "MongoDB", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include router
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
