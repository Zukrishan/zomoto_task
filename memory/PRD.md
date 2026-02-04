# Zomoto Tasks - Restaurant Task Management System

## Original Problem Statement
Build a production-ready, mobile-first restaurant task management system with:
- User Roles: OWNER, MANAGER, STAFF with strict permissions
- Core Workflow: Create → Assign → Complete → Verify
- MySQL database storage
- Task Library with autocomplete
- PWA ready, notify.lk SMS integration (pluggable)
- Mobile-first design with Red (#E23744) Zomoto branding

## Database: MySQL
- All data stored in MySQL database (zomoto_tasks)
- Tables: users, tasks, task_templates, task_comments, task_attachments, task_activity_logs, categories, notifications, push_subscriptions, notification_logs

## What's Been Implemented (Feb 4, 2026)

### Backend (FastAPI + MySQL/SQLAlchemy)
- ✅ User CRUD with role-based access control
- ✅ Task CRUD (Create, Read, Update, Delete)
- ✅ Task status workflow with notifications
- ✅ Categories CRUD (dynamic category management)
- ✅ Task Library (templates) CRUD
- ✅ Comments system
- ✅ File attachments with image optimization & thumbnails
- ✅ Activity logging
- ✅ In-app notifications system
- ✅ Dashboard stats API

### Frontend (React + Shadcn UI)
- ✅ Login page with Zomoto branding
- ✅ Role-based dashboards
- ✅ Task list with filters
- ✅ Task detail with Edit/Delete
- ✅ Task creation modal with autocomplete
- ✅ User management (Owner only)
- ✅ Categories management page
- ✅ Task Library page
- ✅ Notification bell with dropdown
- ✅ Image viewer with zoom/rotate
- ✅ Mobile-first responsive design

## Demo Credentials
- Owner: owner@zomoto.lk / 123456
- Manager: manager@zomoto.lk / 123456
- Staff: staff@zomoto.lk / 123456

## API Endpoints
All endpoints prefixed with /api
- POST /auth/login, GET /auth/me
- GET/POST/PUT/DELETE /users
- GET/POST/PUT/DELETE /tasks
- POST /tasks/{id}/verify
- GET/POST /tasks/{id}/comments
- GET/POST /tasks/{id}/attachments
- GET /attachments/{id}, GET /attachments/{id}/thumbnail
- GET/POST/PUT/DELETE /categories
- GET/POST/DELETE /task-templates
- GET/PUT /notifications
- GET /dashboard/stats
