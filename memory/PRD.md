# Zomoto Tasks - Restaurant Task Management System

## Original Problem Statement
Build a production-ready, mobile-first restaurant task management system called Zomoto Tasks. The system must streamline daily restaurant operations by enforcing clear accountability, task tracking, and verification, while being future-ready for payroll, performance tracking, salary deductions, and AI features.

## User Personas
- **Owner**: Full system access, can create tasks, manage users, verify tasks, view reports
- **Manager**: Can create/assign tasks, manage staff assignments, verify completed tasks
- **Staff**: Can view assigned tasks, start tasks, upload proof, complete tasks

## Core Requirements

### Task Lifecycle (Implemented Feb 10, 2026)
- States: `PENDING` → `IN_PROGRESS` → `COMPLETED` → `VERIFIED`
- Auto-trigger `NOT_COMPLETED` when deadline exceeded
- Actions:
  - **Start Task**: Changes status from PENDING to IN_PROGRESS
  - **Complete Task**: Requires proof photo upload, changes to COMPLETED
  - **Verify Task**: Manager/Owner only, changes to VERIFIED

### Time-Bound Tasks (Implemented Feb 10, 2026)
- Mandatory `time_interval` field (numeric value)
- `time_unit` field: MINUTES or HOURS
- `allocated_datetime`: When task should start
- Auto-calculated `deadline` = allocated_datetime + time_interval

### Task Types (Implemented Feb 10-13, 2026)
- `INSTANT`: One-time task with specific allocated datetime and deadline
- `RECURRING`: Monthly schedule-based task with day intervals
  - Can schedule up to 5 intervals per month
  - Example: Days 1-5, 10-15, 21-25 = task visible on those days
  - Task only appears to assigned staff during active intervals
  - Recurrence data stored: `recurrence_type`, `recurrence_intervals`

## What's Been Implemented

### Backend (FastAPI + MySQL/MariaDB via SQLAlchemy)
- ✅ Migrated from MongoDB to MySQL using SQLAlchemy ORM
- ✅ Auto-seed default users (Owner, Manager, Staff) and categories on startup
- ✅ User CRUD with role-based access control (OWNER, MANAGER, STAFF)
- ✅ JWT Authentication with 24-hour token expiry
- ✅ New Task Lifecycle (PENDING, IN_PROGRESS, COMPLETED, NOT_COMPLETED, VERIFIED)
- ✅ Time-bound tasks with time_interval, time_unit, allocated_datetime, deadline
- ✅ Task Start endpoint (`POST /api/tasks/{task_id}/start`)
- ✅ Task Complete endpoint (`POST /api/tasks/{task_id}/complete`) - requires proof photos
- ✅ Task Verify endpoint (`POST /api/tasks/{task_id}/verify`) - Manager/Owner only
- ✅ Proof Photo upload endpoint (`POST /api/tasks/{task_id}/proof`)
- ✅ Background task to auto-mark overdue tasks as NOT_COMPLETED
- ✅ WebSocket infrastructure for live updates
- ✅ SMS integration via notify.lk (credentials configured)
- ✅ Task soft delete and bulk delete
- ✅ Categories CRUD
- ✅ Task Templates (Library) CRUD
- ✅ Comments system
- ✅ Activity logging
- ✅ In-app notifications

### Frontend (React + TailwindCSS + shadcn/ui)
- ✅ Login page with Zomoto branding
- ✅ Role-based dashboards showing new task status counts
- ✅ Task list with status, category, priority filters
- ✅ Task cards showing time_interval, time remaining, overdue indicator
- ✅ Create Task modal with:
  - Task Type selector (Instant/Recurring)
  - Time Allowed field (interval + unit)
  - Start Date & Time picker
  - Deadline preview
  - Staff assignment
- ✅ Edit Task modal with time fields
- ✅ Task Detail page with:
  - New lifecycle status badges
  - Overdue warning
  - Start Task / Complete Task / Verify Task action buttons
  - Proof Photos section (required for completion)
  - Time info display (interval, allocated, deadline, start_time)
  - Comments, Attachments, Activity tabs
- ✅ Soft delete with confirmation
- ✅ User management (Owner only)
- ✅ Categories management
- ✅ Task Library page

## Demo Credentials
| Role | Email | Password |
|------|-------|----------|
| Owner | owner@zomoto.lk | 123456 |
| Manager | manager@zomoto.lk | 123456 |
| Staff | staff@zomoto.lk | 123456 |

## API Endpoints
All endpoints prefixed with `/api`

### Auth
- `POST /auth/login` - Login
- `GET /auth/me` - Get current user

### Users
- `GET /users` - List users (Owner/Manager)
- `POST /users` - Create user (Owner)
- `PUT /users/{id}` - Update user (Owner)
- `DELETE /users/{id}` - Deactivate user (Owner)
- `GET /users/staff` - List staff only (Owner/Manager)

### Tasks
- `GET /tasks` - List tasks (with filters: status, category, priority)
- `POST /tasks` - Create task (Owner/Manager)
- `GET /tasks/{id}` - Get task detail
- `PUT /tasks/{id}` - Update task
- `DELETE /tasks/{id}` - Soft delete task (Owner/Manager)
- `POST /tasks/{id}/start` - Start task
- `POST /tasks/{id}/complete` - Complete task (requires proof)
- `POST /tasks/{id}/verify` - Verify task (Owner/Manager)
- `POST /tasks/{id}/proof` - Upload proof photo
- `POST /tasks/bulk-delete` - Bulk soft delete

### Categories
- `GET /categories` - List categories
- `POST /categories` - Create category (Owner/Manager)
- `PUT /categories/{id}` - Update category
- `DELETE /categories/{id}` - Delete category

### Task Templates
- `GET /task-templates` - List templates
- `POST /task-templates` - Create template
- `DELETE /task-templates/{id}` - Delete template

### Comments & Activity
- `GET /tasks/{id}/comments` - Get comments
- `POST /tasks/{id}/comments` - Add comment
- `GET /tasks/{id}/activity` - Get activity log

### Notifications
- `GET /notifications` - Get notifications
- `GET /notifications/unread-count` - Get unread count
- `PUT /notifications/{id}/read` - Mark as read
- `PUT /notifications/read-all` - Mark all as read

### Dashboard
- `GET /dashboard/stats` - Get dashboard statistics

## 3rd Party Integrations

### notify.lk (SMS) - Configured
- API Key: Configured in `.env`
- User ID: 28528
- Sender ID: Zeeha HLD
- Status: Ready to use (not yet triggered in production)

### Firebase (Push Notifications) - Pending
- Playbook fetched but not yet integrated

## Testing Status
- Backend API Tests: **19/21 passed (90.5%)** - 2 test naming mismatches (not API bugs)
- Frontend Tests: **95% success rate** - All critical flows pass
- Test file: `/app/backend/tests/test_task_lifecycle.py`
- Test reports: `/app/test_reports/`

## Bug Fixes (Feb 21, 2026)
- ✅ Fixed backend crash on `/api/tasks/` - TypeError comparing timezone-aware vs naive datetimes
- ✅ Fixed CreateTaskModal crash - template `name` field mismatch (backend returns `title`)
- ✅ Fixed datetime handling in task creation, updates, status changes (all use naive UTC)
- ✅ Fixed overdue task checker datetime comparison
- ✅ Added auto-seed for default users and categories on fresh DB
- ✅ Verified task editing works end-to-end after MySQL migration

## Features & Fixes (Feb 28, 2026)
- ✅ **Recurring Task Redesign**: Task Library now manages recurring rules with day-interval schedules. Background job auto-generates daily task instances on scheduled days. Title format: "Task Name (Mar 01 09:00 AM)"
- ✅ **Late Task Completion**: Staff can complete tasks even after deadline. Tasks marked as NOT_COMPLETED can still be completed with "Late" badge. Actual time taken is tracked.
- ✅ **Task Card Enhancements**: Shows "Allowed: X min", "Started: HH:MM", "Took: X min", and "Late" badge
- ✅ **Generate Now**: Manual trigger for recurring task generation from Library page
- ✅ **Template Edit/Toggle**: Templates can be edited and recurring rules can be paused/activated

## Prioritized Backlog

### P0 (Critical) - DONE
- ✅ New task lifecycle implementation
- ✅ Time-bound tasks
- ✅ Proof photo upload requirement
- ✅ Task edit functionality fix
- ✅ Recurring task assignment optional (Feb 17, 2026)
- ✅ Dynamic categories in Create Task modal (Feb 17, 2026)
- ✅ Password field in Add User modal (Feb 17, 2026)
- ✅ Notification dropdown z-index and positioning fix (Feb 17, 2026)

### P1 (High Priority) - DONE
- ✅ Multi-select and "Select All" for bulk task deletion
- ✅ WebSocket real-time updates on frontend
- ✅ Long-press to select on mobile

### P2 (Medium Priority) - Next
- [ ] SMS notifications via notify.lk on task events
- [ ] Web Push notifications via Firebase
- [ ] Performance reports (tasks per staff, verification rate)

### P3 (Future)
- [ ] Salary Deduction / Incentives module
- [ ] Payroll Integration
- [ ] AI-driven features (task suggestions, performance insights)

## Technical Stack
- **Frontend**: React 18, React Router 6, TailwindCSS, shadcn/ui
- **Backend**: FastAPI, Pydantic, SQLAlchemy ORM
- **Database**: MySQL/MariaDB (migrated from MongoDB)
- **Authentication**: JWT with RBAC
- **Architecture**: Full-stack monolith, PWA-ready

## File Structure
```
/app/
├── backend/
│   ├── .env (MongoDB URL, JWT secret, notify.lk credentials)
│   ├── requirements.txt
│   ├── server.py (Main backend - 1200+ lines)
│   └── tests/
│       └── test_task_lifecycle.py
├── frontend/
│   ├── .env (REACT_APP_BACKEND_URL)
│   ├── package.json
│   └── src/
│       ├── components/
│       │   ├── CreateTaskModal.js
│       │   ├── EditTaskModal.js
│       │   ├── TaskCard.js
│       │   └── ...
│       └── pages/
│           ├── TasksPage.js
│           ├── TaskDetailPage.js
│           └── ...
└── memory/
    └── PRD.md (this file)
```
