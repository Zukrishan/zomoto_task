from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
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

# notify.lk Configuration
NOTIFY_LK_USER_ID = os.environ.get('NOTIFY_LK_USER_ID', '28528')
NOTIFY_LK_API_KEY = os.environ.get('NOTIFY_LK_API_KEY', 'JeP7ACSaYTSwOY5eCl6S')
NOTIFY_LK_SENDER_ID = os.environ.get('NOTIFY_LK_SENDER_ID', 'Zeeha HLD')

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI(title="Zomoto Tasks API", version="2.0.0")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def broadcast_to_users(self, user_ids: List[str], message: dict):
        for user_id in user_ids:
            await self.broadcast_to_user(user_id, message)
    
    async def broadcast_to_all(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# ============== ENUMS ==============

class TaskStatus:
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NOT_COMPLETED = "NOT_COMPLETED"
    VERIFIED = "VERIFIED"

class TaskType:
    INSTANT = "INSTANT"
    RECURRING = "RECURRING"

class TimeUnit:
    MINUTES = "MINUTES"
    HOURS = "HOURS"

class RecurrenceType:
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"

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

class RecurrenceInterval(BaseModel):
    start_day: int
    end_day: int

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str = "Other"
    priority: str = "MEDIUM"
    task_type: str = "INSTANT"  # INSTANT or RECURRING
    time_interval: int = 30  # Duration in time_unit
    time_unit: str = "MINUTES"  # MINUTES or HOURS
    allocated_datetime: str  # When task should start
    assigned_to: Optional[str] = None
    # Recurring task fields
    recurrence_type: Optional[str] = None  # DAILY or MONTHLY
    recurrence_intervals: Optional[List[RecurrenceInterval]] = None  # For monthly
    recurrence_end_date: Optional[str] = None  # Max 1 month

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    time_interval: Optional[int] = None
    time_unit: Optional[str] = None
    allocated_datetime: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    priority: str
    task_type: str
    time_interval: int
    time_unit: str
    allocated_datetime: Optional[str]
    deadline: Optional[str]
    start_time: Optional[str]
    status: str
    created_by: str
    created_by_name: str
    assigned_to: Optional[str]
    assigned_to_name: Optional[str]
    is_overdue: bool
    proof_photos: List[str]
    created_at: str
    updated_at: str
    is_deleted: bool
    # Recurring task fields
    recurrence_type: Optional[str] = None
    recurrence_intervals: Optional[List[dict]] = None

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
    pending: int
    in_progress: int
    completed: int
    not_completed: int
    verified: int
    tasks_to_assign: Optional[int] = None
    tasks_to_verify: Optional[int] = None
    total_staff: Optional[int] = None

class BulkDeleteRequest(BaseModel):
    task_ids: List[str]

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
    # Broadcast via WebSocket
    await manager.broadcast_to_user(user_id, {"type": "notification", "data": notification})

async def send_sms(phone: str, message: str, task_id: str = None):
    """Send SMS via notify.lk"""
    # Check for duplicate notification today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if task_id:
        existing = await db.notification_logs.find_one({
            "task_id": task_id,
            "type": "SMS",
            "recipient": phone,
            "created_at": {"$gte": today_start.isoformat()}
        })
        if existing:
            logger.info(f"SMS already sent today for task {task_id} to {phone}")
            return False
    
    # Format phone number for Sri Lanka
    formatted_phone = phone.lstrip('0')
    if not formatted_phone.startswith('94'):
        formatted_phone = '94' + formatted_phone
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://app.notify.lk/api/v1/send",
                data={
                    "user_id": NOTIFY_LK_USER_ID,
                    "api_key": NOTIFY_LK_API_KEY,
                    "sender_id": NOTIFY_LK_SENDER_ID,
                    "to": formatted_phone,
                    "message": message
                },
                timeout=30.0
            )
            
            # Log notification
            await db.notification_logs.insert_one({
                "id": str(uuid.uuid4()),
                "type": "SMS",
                "task_id": task_id,
                "recipient": phone,
                "message": message,
                "status": "SENT" if response.status_code == 200 else "FAILED",
                "response": response.text,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"SMS sent to {formatted_phone}: {response.status_code}")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"SMS sending failed: {e}")
        return False

def calculate_deadline(allocated_datetime: str, time_interval: int, time_unit: str) -> datetime:
    """Calculate deadline based on allocated time and interval"""
    try:
        allocated = datetime.fromisoformat(allocated_datetime.replace('Z', '+00:00'))
        if time_unit == TimeUnit.HOURS:
            return allocated + timedelta(hours=time_interval)
        else:
            return allocated + timedelta(minutes=time_interval)
    except:
        return None

def is_task_overdue(task: dict) -> bool:
    """Check if task is overdue"""
    if task.get("status") in [TaskStatus.COMPLETED, TaskStatus.VERIFIED, TaskStatus.NOT_COMPLETED]:
        return False
    deadline = task.get("deadline")
    if not deadline:
        return False
    try:
        deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > deadline_dt
    except:
        return False

def is_recurring_task_active(task: dict) -> bool:
    """Check if recurring task should be visible now based on day AND time"""
    if task.get("task_type") != TaskType.RECURRING:
        return True
    
    now = datetime.now(timezone.utc)
    today = now.date()
    current_time = now.time()
    recurrence_type = task.get("recurrence_type")
    
    # Check if current day falls within any interval
    day_is_active = False
    if recurrence_type == RecurrenceType.DAILY:
        day_is_active = True
    elif recurrence_type == RecurrenceType.MONTHLY:
        intervals = task.get("recurrence_intervals", [])
        current_day = today.day
        for interval in intervals:
            if interval.get("start_day", 0) <= current_day <= interval.get("end_day", 0):
                day_is_active = True
                break
    else:
        day_is_active = True
    
    if not day_is_active:
        return False
    
    # Check if current time is >= allocated time
    allocated_datetime_str = task.get("allocated_datetime")
    if allocated_datetime_str:
        try:
            # Parse the allocated datetime
            if isinstance(allocated_datetime_str, str):
                allocated_dt = datetime.fromisoformat(allocated_datetime_str.replace('Z', '+00:00'))
            else:
                allocated_dt = allocated_datetime_str
            
            # Get just the time part for comparison
            allocated_time = allocated_dt.time()
            
            # Task is only visible if current time >= allocated time
            if current_time < allocated_time:
                return False
        except Exception as e:
            logger.error(f"Error parsing allocated_datetime: {e}")
            # If parsing fails, show the task
            pass
    
    return True

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

def task_to_response(task: dict) -> TaskResponse:
    return TaskResponse(
        id=task["id"],
        title=task["title"],
        description=task.get("description", ""),
        category=task.get("category", "Other"),
        priority=task.get("priority", "MEDIUM"),
        task_type=task.get("task_type", "INSTANT"),
        time_interval=task.get("time_interval", 30),
        time_unit=task.get("time_unit", "MINUTES"),
        allocated_datetime=task.get("allocated_datetime"),
        deadline=task.get("deadline"),
        start_time=task.get("start_time"),
        status=task.get("status", "PENDING"),
        created_by=task.get("created_by", ""),
        created_by_name=task.get("created_by_name", ""),
        assigned_to=task.get("assigned_to"),
        assigned_to_name=task.get("assigned_to_name"),
        is_overdue=is_task_overdue(task),
        proof_photos=task.get("proof_photos", []),
        created_at=task.get("created_at", ""),
        updated_at=task.get("updated_at", ""),
        is_deleted=task.get("is_deleted", False),
        recurrence_type=task.get("recurrence_type"),
        recurrence_intervals=task.get("recurrence_intervals")
    )

# ============== Background Task: Check Overdue Tasks ==============

async def check_overdue_tasks():
    """Background task to mark overdue tasks as NOT_COMPLETED"""
    while True:
        try:
            now = datetime.now(timezone.utc)
            # Find tasks that are overdue and not yet marked
            overdue_tasks = await db.tasks.find({
                "status": {"$in": [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]},
                "deadline": {"$lt": now.isoformat()},
                "is_deleted": {"$ne": True}
            }, {"_id": 0}).to_list(1000)
            
            for task in overdue_tasks:
                await db.tasks.update_one(
                    {"id": task["id"]},
                    {"$set": {"status": TaskStatus.NOT_COMPLETED, "updated_at": now.isoformat()}}
                )
                await log_activity(task["id"], "SYSTEM", "System", "STATUS_CHANGED", "Task auto-marked as NOT_COMPLETED (deadline exceeded)")
                
                # Notify assigned user
                if task.get("assigned_to"):
                    await create_notification(
                        task["assigned_to"],
                        "TASK_EXPIRED",
                        "Task Deadline Exceeded",
                        f"Task '{task['title']}' was not completed in time",
                        task["id"]
                    )
                
                # Broadcast update
                await manager.broadcast_to_all({
                    "type": "task_update",
                    "data": task_to_response({**task, "status": TaskStatus.NOT_COMPLETED}).model_dump()
                })
            
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logger.error(f"Error in overdue check: {e}")
            await asyncio.sleep(60)

# Track which recurring tasks have been activated today to avoid duplicate broadcasts
activated_recurring_tasks = set()

async def check_recurring_tasks_activation():
    """Background task to broadcast recurring tasks when their scheduled time arrives"""
    global activated_recurring_tasks
    
    # Reset the set at midnight
    last_reset_date = datetime.now(timezone.utc).date()
    
    while True:
        try:
            now = datetime.now(timezone.utc)
            today = now.date()
            current_time = now.time()
            current_day = today.day
            
            # Reset activated tasks at midnight
            if today != last_reset_date:
                activated_recurring_tasks = set()
                last_reset_date = today
            
            # Find all recurring tasks that might need activation
            recurring_tasks = await db.tasks.find({
                "task_type": TaskType.RECURRING,
                "is_deleted": {"$ne": True},
                "status": {"$nin": [TaskStatus.COMPLETED, TaskStatus.VERIFIED, TaskStatus.NOT_COMPLETED]}
            }, {"_id": 0}).to_list(1000)
            
            for task in recurring_tasks:
                task_id = task["id"]
                
                # Skip if already activated today
                if task_id in activated_recurring_tasks:
                    continue
                
                # Check if day is within intervals
                recurrence_type = task.get("recurrence_type")
                if recurrence_type == RecurrenceType.MONTHLY:
                    intervals = task.get("recurrence_intervals", [])
                    day_active = any(
                        interval.get("start_day", 0) <= current_day <= interval.get("end_day", 0)
                        for interval in intervals
                    )
                    if not day_active:
                        continue
                
                # Check if allocated time has been reached
                allocated_datetime_str = task.get("allocated_datetime")
                if allocated_datetime_str:
                    try:
                        if isinstance(allocated_datetime_str, str):
                            allocated_dt = datetime.fromisoformat(allocated_datetime_str.replace('Z', '+00:00'))
                        else:
                            allocated_dt = allocated_datetime_str
                        
                        allocated_time = allocated_dt.time()
                        
                        # If current time just passed allocated time (within last 60 seconds window)
                        # Convert times to seconds for comparison
                        current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
                        allocated_seconds = allocated_time.hour * 3600 + allocated_time.minute * 60 + allocated_time.second
                        
                        # If we're within 60 seconds after the allocated time, broadcast
                        if 0 <= (current_seconds - allocated_seconds) <= 60:
                            # Mark as activated
                            activated_recurring_tasks.add(task_id)
                            
                            # Broadcast to the assigned user
                            if task.get("assigned_to"):
                                task_response = task_to_response(task).model_dump()
                                await manager.broadcast_to_user(task["assigned_to"], {
                                    "type": "recurring_task_activated",
                                    "data": task_response
                                })
                                logger.info(f"Recurring task '{task['title']}' activated for user {task['assigned_to']}")
                                
                                # Also create a notification
                                await create_notification(
                                    task["assigned_to"],
                                    "TASK_ASSIGNED",
                                    "Scheduled Task Active",
                                    f"Task '{task['title']}' is now active",
                                    task_id
                                )
                    except Exception as e:
                        logger.error(f"Error checking recurring task time: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logger.error(f"Error in recurring task activation check: {e}")
            await asyncio.sleep(60)

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
    assigned_user = None
    
    if task_data.assigned_to:
        assigned_user = await db.users.find_one({"id": task_data.assigned_to}, {"_id": 0})
        if assigned_user:
            assigned_to_name = assigned_user["name"]
    
    # Calculate deadline
    deadline = calculate_deadline(task_data.allocated_datetime, task_data.time_interval, task_data.time_unit)
    
    task = {
        "id": str(uuid.uuid4()),
        "title": task_data.title,
        "description": task_data.description or "",
        "category": task_data.category,
        "priority": task_data.priority,
        "task_type": task_data.task_type,
        "time_interval": task_data.time_interval,
        "time_unit": task_data.time_unit,
        "allocated_datetime": task_data.allocated_datetime,
        "deadline": deadline.isoformat() if deadline else None,
        "start_time": None,
        "status": TaskStatus.PENDING,
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "assigned_to": task_data.assigned_to,
        "assigned_to_name": assigned_to_name,
        "proof_photos": [],
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add recurring fields if applicable
    if task_data.task_type == TaskType.RECURRING:
        task["recurrence_type"] = task_data.recurrence_type
        task["recurrence_intervals"] = [i.model_dump() for i in (task_data.recurrence_intervals or [])]
        task["recurrence_end_date"] = task_data.recurrence_end_date
    
    await db.tasks.insert_one(task)
    await log_activity(task["id"], current_user["id"], current_user["name"], "CREATED", f"Task '{task['title']}' created")
    
    # Send notifications if assigned
    if task_data.assigned_to and assigned_user:
        await create_notification(task_data.assigned_to, "TASK_ASSIGNED", "New Task Assigned", f"You have been assigned: {task['title']}", task["id"])
        # Send SMS
        if assigned_user.get("phone"):
            await send_sms(assigned_user["phone"], f"New task assigned: {task['title']}. Deadline: {task_data.time_interval} {task_data.time_unit.lower()}", task["id"])
    
    # Broadcast to all managers/owners
    await manager.broadcast_to_all({"type": "task_created", "data": task_to_response(task).model_dump()})
    
    return task_to_response(task)

@api_router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(status: Optional[str] = None, assigned_to: Optional[str] = None, category: Optional[str] = None, priority: Optional[str] = None, include_deleted: bool = False, current_user: dict = Depends(get_current_user)):
    query = {}
    
    if not include_deleted:
        query["is_deleted"] = {"$ne": True}
    
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
    
    # Filter recurring tasks based on schedule
    active_tasks = []
    for task in tasks:
        if is_recurring_task_active(task):
            # Check and update overdue status
            if is_task_overdue(task) and task["status"] not in [TaskStatus.NOT_COMPLETED, TaskStatus.COMPLETED, TaskStatus.VERIFIED]:
                await db.tasks.update_one({"id": task["id"]}, {"$set": {"status": TaskStatus.NOT_COMPLETED}})
                task["status"] = TaskStatus.NOT_COMPLETED
            active_tasks.append(task_to_response(task))
    
    return active_tasks

@api_router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user["role"] == "STAFF" and task.get("assigned_to") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return task_to_response(task)

@api_router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task_data: TaskUpdate, current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if current_user["role"] == "STAFF":
        if task.get("assigned_to") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        # Staff can only update status
        if task_data.status:
            raise HTTPException(status_code=400, detail="Use /start or /complete endpoints")
    else:
        update_data = {k: v for k, v in task_data.model_dump().items() if v is not None}
        
        # Recalculate deadline if time changed
        if task_data.time_interval or task_data.time_unit or task_data.allocated_datetime:
            allocated = task_data.allocated_datetime or task.get("allocated_datetime")
            interval = task_data.time_interval or task.get("time_interval", 30)
            unit = task_data.time_unit or task.get("time_unit", "MINUTES")
            deadline = calculate_deadline(allocated, interval, unit)
            if deadline:
                update_data["deadline"] = deadline.isoformat()
        
        if task_data.assigned_to:
            assigned_user = await db.users.find_one({"id": task_data.assigned_to}, {"_id": 0})
            if assigned_user:
                update_data["assigned_to_name"] = assigned_user["name"]
                await log_activity(task_id, current_user["id"], current_user["name"], "REASSIGNED", f"Task reassigned to {assigned_user['name']}")
                await create_notification(task_data.assigned_to, "TASK_ASSIGNED", "Task Assigned", f"You have been assigned: {task['title']}", task_id)
                if assigned_user.get("phone"):
                    await send_sms(assigned_user["phone"], f"Task assigned: {task['title']}", task_id)
        
        if update_data:
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    
    # Broadcast update
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(updated_task).model_dump()})
    
    return task_to_response(updated_task)

@api_router.post("/tasks/{task_id}/start", response_model=TaskResponse)
async def start_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Staff starts working on a task"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if current_user["role"] == "STAFF" and task.get("assigned_to") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if task["status"] != TaskStatus.PENDING:
        raise HTTPException(status_code=400, detail="Task can only be started from PENDING status")
    
    now = datetime.now(timezone.utc)
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {"status": TaskStatus.IN_PROGRESS, "start_time": now.isoformat(), "updated_at": now.isoformat()}}
    )
    
    await log_activity(task_id, current_user["id"], current_user["name"], "STARTED", "Task started")
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(updated_task).model_dump()})
    
    return task_to_response(updated_task)

@api_router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Staff marks task as completed (requires proof photos)"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if current_user["role"] == "STAFF" and task.get("assigned_to") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if task["status"] != TaskStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Task can only be completed from IN_PROGRESS status")
    
    # Check if proof photos exist
    if not task.get("proof_photos") or len(task.get("proof_photos", [])) == 0:
        raise HTTPException(status_code=400, detail="Please upload proof photos before completing the task")
    
    now = datetime.now(timezone.utc)
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {"status": TaskStatus.COMPLETED, "updated_at": now.isoformat()}}
    )
    
    await log_activity(task_id, current_user["id"], current_user["name"], "COMPLETED", "Task completed")
    
    # Notify creator
    if task.get("created_by"):
        await create_notification(task["created_by"], "TASK_COMPLETED", "Task Completed", f"Task '{task['title']}' has been completed", task_id)
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(updated_task).model_dump()})
    
    return task_to_response(updated_task)

@api_router.post("/tasks/{task_id}/verify", response_model=TaskResponse)
async def verify_task(task_id: str, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Only completed tasks can be verified")
    
    now = datetime.now(timezone.utc)
    await db.tasks.update_one({"id": task_id}, {"$set": {"status": TaskStatus.VERIFIED, "updated_at": now.isoformat()}})
    await log_activity(task_id, current_user["id"], current_user["name"], "VERIFIED", "Task verified")
    
    if task.get("assigned_to"):
        await create_notification(task["assigned_to"], "TASK_VERIFIED", "Task Verified", f"Your task '{task['title']}' has been verified", task_id)
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(updated_task).model_dump()})
    
    return task_to_response(updated_task)

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    """Soft delete a single task"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.tasks.update_one({"id": task_id}, {"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc).isoformat()}})
    await log_activity(task_id, current_user["id"], current_user["name"], "DELETED", "Task deleted")
    
    await manager.broadcast_to_all({"type": "task_deleted", "data": {"id": task_id}})
    
    return {"message": "Task deleted successfully"}

@api_router.post("/tasks/bulk-delete")
async def bulk_delete_tasks(request: BulkDeleteRequest, current_user: dict = Depends(require_roles(["OWNER", "MANAGER"]))):
    """Soft delete multiple tasks"""
    now = datetime.now(timezone.utc).isoformat()
    
    for task_id in request.task_ids:
        await db.tasks.update_one({"id": task_id}, {"$set": {"is_deleted": True, "updated_at": now}})
        await log_activity(task_id, current_user["id"], current_user["name"], "DELETED", "Task deleted (bulk)")
    
    await manager.broadcast_to_all({"type": "tasks_deleted", "data": {"ids": request.task_ids}})
    
    return {"message": f"{len(request.task_ids)} tasks deleted successfully"}

# ============== PROOF PHOTO UPLOAD ==============

@api_router.post("/tasks/{task_id}/proof")
async def upload_proof_photo(task_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Upload proof photo for task completion"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if current_user["role"] == "STAFF" and task.get("assigned_to") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if task["status"] not in [TaskStatus.IN_PROGRESS, TaskStatus.PENDING]:
        raise HTTPException(status_code=400, detail="Can only upload proof for pending or in-progress tasks")
    
    # Save file
    upload_dir = ROOT_DIR / "uploads" / "proofs" / task_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix.lower()
    file_path = upload_dir / f"{file_id}{file_ext}"
    
    content = await file.read()
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Optimize image
    if file.content_type and file.content_type.startswith('image/'):
        try:
            optimized_path, _ = optimize_image(file_path)
            if optimized_path != file_path:
                file_path.unlink(missing_ok=True)
                file_path = optimized_path
        except:
            pass
    
    # Add to proof_photos array
    photo_url = f"/api/proofs/{task_id}/{file_id}"
    await db.tasks.update_one(
        {"id": task_id},
        {"$push": {"proof_photos": photo_url}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Store file info
    await db.proof_photos.insert_one({
        "id": file_id,
        "task_id": task_id,
        "filename": file.filename,
        "file_path": str(file_path),
        "content_type": file.content_type,
        "uploaded_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    await log_activity(task_id, current_user["id"], current_user["name"], "PROOF_UPLOADED", f"Proof photo uploaded: {file.filename}")
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    await manager.broadcast_to_all({"type": "task_update", "data": task_to_response(updated_task).model_dump()})
    
    return {"id": file_id, "url": photo_url, "message": "Proof photo uploaded successfully"}

@api_router.get("/proofs/{task_id}/{photo_id}")
async def get_proof_photo(task_id: str, photo_id: str):
    """Get proof photo file"""
    photo = await db.proof_photos.find_one({"id": photo_id, "task_id": task_id}, {"_id": 0})
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    file_path = Path(photo["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(path=file_path, media_type=photo.get("content_type", "image/jpeg"))

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
    
    # Broadcast comment
    await manager.broadcast_to_all({"type": "comment_added", "data": {"task_id": task_id, "comment": comment}})
    
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
    query = {"is_deleted": {"$ne": True}}
    if current_user["role"] == "STAFF":
        query["assigned_to"] = current_user["id"]
    
    total_tasks = await db.tasks.count_documents(query)
    pending = await db.tasks.count_documents({**query, "status": TaskStatus.PENDING})
    in_progress = await db.tasks.count_documents({**query, "status": TaskStatus.IN_PROGRESS})
    completed = await db.tasks.count_documents({**query, "status": TaskStatus.COMPLETED})
    not_completed = await db.tasks.count_documents({**query, "status": TaskStatus.NOT_COMPLETED})
    verified = await db.tasks.count_documents({**query, "status": TaskStatus.VERIFIED})
    
    stats = DashboardStats(total_tasks=total_tasks, pending=pending, in_progress=in_progress, completed=completed, not_completed=not_completed, verified=verified)
    
    if current_user["role"] in ["OWNER", "MANAGER"]:
        stats.tasks_to_assign = await db.tasks.count_documents({"status": TaskStatus.PENDING, "assigned_to": None, "is_deleted": {"$ne": True}})
        stats.tasks_to_verify = await db.tasks.count_documents({"status": TaskStatus.COMPLETED, "is_deleted": {"$ne": True}})
        stats.total_staff = await db.users.count_documents({"role": "STAFF", "status": "ACTIVE"})
    
    return stats

# ============== WEBSOCKET ==============

@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
        
        await manager.connect(websocket, user_id)
        try:
            while True:
                data = await websocket.receive_text()
                # Handle ping/pong or other messages
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id)
    except JWTError:
        await websocket.close(code=4001)

# Also expose WebSocket on /api/ws path for ingress routing
@app.websocket("/api/ws/{token}")
async def websocket_endpoint_api(websocket: WebSocket, token: str):
    await websocket_endpoint(websocket, token)

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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start background task on startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_overdue_tasks())

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
