# Zomoto Tasks - Restaurant Task Management System

## Original Problem Statement
Build a production-ready, mobile-first restaurant task management system called Zomoto Tasks with:
- User Roles: OWNER, MANAGER, STAFF with strict permissions
- Core Workflow: Create → Assign → Complete → Verify
- Task Library with autocomplete
- PWA ready with push notification support
- notify.lk SMS integration (pluggable)
- Mobile-first design with Red (#E23744) Zomoto branding

## User Personas
1. **Restaurant Owner** - Full system access, user management, all task operations
2. **Restaurant Manager** - Create/assign tasks, verify completed tasks, view staff
3. **Staff Member** - View assigned tasks, update status, add comments/attachments

## Core Requirements (Static)
- JWT authentication with role-based access control
- Task status workflow: CREATED → ASSIGNED → IN_PROGRESS → COMPLETED → VERIFIED
- Task Library with autocomplete for quick task creation
- Comments and attachments on tasks
- Activity logging for audit trail
- Dashboard with role-specific stats
- Mobile-first responsive design
- PWA manifest for installability

## What's Been Implemented (Feb 4, 2026)
### Backend (FastAPI + MongoDB)
- ✅ User authentication (login, JWT tokens)
- ✅ Role-based access control (OWNER, MANAGER, STAFF)
- ✅ User CRUD (create, update, deactivate, reset password)
- ✅ Task CRUD with status workflow
- ✅ Task Library (templates) CRUD
- ✅ Comments system
- ✅ File attachments
- ✅ Activity logging
- ✅ Dashboard stats API
- ✅ Push notification subscription endpoints
- ✅ notify.lk SMS integration (pluggable)
- ✅ Seed data (demo users)

### Frontend (React + Shadcn UI)
- ✅ Login page with Zomoto branding
- ✅ Role-based dashboards (Owner, Manager, Staff views)
- ✅ Task list with filters (status, category, priority)
- ✅ Task detail page with comments, attachments, activity log
- ✅ Task creation modal with Task Library autocomplete
- ✅ User management page (Owner only)
- ✅ Task Library management page
- ✅ Mobile-first responsive design
- ✅ Bottom navigation for mobile
- ✅ Sidebar navigation for desktop
- ✅ PWA manifest

## Prioritized Backlog

### P0 - Critical (Next Sprint)
- [ ] Firebase Cloud Messaging setup for push notifications
- [ ] Offline support with service worker
- [ ] Task due date reminders

### P1 - High Priority
- [ ] notify.lk SMS integration testing with real API keys
- [ ] Performance reports page
- [ ] Task filters by date range
- [ ] Bulk task operations

### P2 - Medium Priority
- [ ] AI task suggestions
- [ ] Performance insights
- [ ] Payroll integration hooks
- [ ] Email notifications

## Tech Stack
- **Frontend**: React 19, Tailwind CSS, Shadcn UI, DM Sans font
- **Backend**: FastAPI, MongoDB
- **Auth**: JWT with role-based guards
- **Theme**: Red (#E23744) / White (Zomoto brand)

## API Endpoints
- POST /api/auth/login - User login
- GET /api/auth/me - Get current user
- GET/POST /api/users - User management
- GET/POST/PUT/DELETE /api/tasks - Task CRUD
- POST /api/tasks/{id}/verify - Verify task
- GET/POST /api/tasks/{id}/comments - Comments
- GET/POST /api/tasks/{id}/attachments - Attachments
- GET /api/tasks/{id}/activity - Activity log
- GET/POST/DELETE /api/task-templates - Task Library
- GET /api/dashboard/stats - Dashboard stats
- POST /api/push/subscribe - Push subscription
- POST /api/notifications/sms - Send SMS

## Demo Credentials
- Owner: owner@zomoto.lk / 123456
- Manager: manager@zomoto.lk / 123456
- Staff: staff@zomoto.lk / 123456
