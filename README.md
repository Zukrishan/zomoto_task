# Zomoto Tasks - Restaurant Task Management System

A production-ready, mobile-first restaurant task management system built with React, FastAPI, and MySQL.

## 🚀 Quick Start

### Demo Credentials
| Role | Email | Password |
|------|-------|----------|
| Owner | owner@zomoto.lk | 123456 |
| Manager | manager@zomoto.lk | 123456 |
| Staff | staff@zomoto.lk | 123456 |

## 📊 Database Connection (MySQL)

### Connection Details
```
Host: localhost
Database: zomoto_tasks
User: root
Password: (none)
Port: 3306
```

### Connection String
```
mysql+pymysql://root@localhost/zomoto_tasks
```

### Connect via Command Line
```bash
mysql -u root zomoto_tasks
```

### View Tables
```bash
mysql -u root zomoto_tasks -e "SHOW TABLES;"
```

### Database Tables
| Table | Description |
|-------|-------------|
| users | User accounts (Owner, Manager, Staff) |
| tasks | Task records with status tracking |
| task_templates | Task library templates |
| task_comments | Comments on tasks |
| task_attachments | File attachments (images, documents) |
| task_activity_logs | Audit trail for all task changes |
| categories | Task categories with colors |
| notifications | In-app notifications |
| push_subscriptions | Web push subscriptions |
| notification_logs | SMS/Push notification logs |

### Sample Queries
```sql
-- View all users
SELECT id, name, email, role, status FROM users;

-- View all tasks
SELECT id, title, status, assigned_to_name, created_at FROM tasks;

-- View task with comments count
SELECT t.title, t.status, COUNT(c.id) as comments
FROM tasks t
LEFT JOIN task_comments c ON t.id = c.task_id
GROUP BY t.id;
```

## 🛠️ Tech Stack

- **Frontend**: React 19, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, SQLAlchemy
- **Database**: MySQL/MariaDB
- **Auth**: JWT with role-based access control
- **Font**: DM Sans

## 📁 Project Structure

```
/app
├── backend/
│   ├── server.py          # Main FastAPI application
│   ├── .env               # Environment variables
│   ├── requirements.txt   # Python dependencies
│   └── uploads/           # File attachments storage
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── context/       # Auth context
│   │   └── lib/           # API utilities
│   ├── public/
│   │   └── manifest.json  # PWA manifest
│   └── package.json
└── README.md
```

## 🔧 Environment Variables

### Backend (.env)
```env
MYSQL_URL=mysql+pymysql://root@localhost/zomoto_tasks
JWT_SECRET=your-secret-key
CORS_ORIGINS=*
NOTIFY_LK_USER_ID=your-notify-user-id
NOTIFY_LK_API_KEY=your-notify-api-key
NOTIFY_LK_SENDER_ID=NotifyDEMO
```

### Frontend (.env)
```env
REACT_APP_BACKEND_URL=https://your-domain.com
```

## 📱 Features

### User Roles & Permissions
| Feature | Owner | Manager | Staff |
|---------|-------|---------|-------|
| View Dashboard | ✅ | ✅ | ✅ |
| Create Tasks | ✅ | ✅ | ❌ |
| Edit Tasks | ✅ | ✅ | ❌ |
| Delete Tasks | ✅ | ✅ | ❌ |
| Assign Tasks | ✅ | ✅ | ❌ |
| Verify Tasks | ✅ | ✅ | ❌ |
| Update Task Status | ✅ | ✅ | Own tasks only |
| Manage Users | ✅ | ❌ | ❌ |
| Manage Categories | ✅ | ✅ | ❌ |
| View All Tasks | ✅ | ✅ | Own tasks only |

### Task Status Workflow
```
CREATED → ASSIGNED → IN_PROGRESS → COMPLETED → VERIFIED
```

### Core Features
- ✅ Task CRUD with status workflow
- ✅ Task Library (templates) with autocomplete
- ✅ Categories management with colors
- ✅ In-app notifications
- ✅ Comments & activity log
- ✅ File attachments with image optimization
- ✅ Full-screen image viewer
- ✅ Mobile-first responsive design
- ✅ PWA ready

## 🔌 API Endpoints

### Authentication
```
POST /api/auth/login     - User login
GET  /api/auth/me        - Get current user
```

### Users (Owner only)
```
GET    /api/users              - List all users
POST   /api/users              - Create user
PUT    /api/users/{id}         - Update user
DELETE /api/users/{id}         - Deactivate user
POST   /api/users/{id}/reset-password - Reset password
```

### Tasks
```
GET    /api/tasks              - List tasks (filtered by role)
POST   /api/tasks              - Create task
GET    /api/tasks/{id}         - Get task details
PUT    /api/tasks/{id}         - Update task
DELETE /api/tasks/{id}         - Delete task
POST   /api/tasks/{id}/verify  - Verify completed task
```

### Comments & Attachments
```
GET  /api/tasks/{id}/comments     - Get comments
POST /api/tasks/{id}/comments     - Add comment
GET  /api/tasks/{id}/attachments  - Get attachments
POST /api/tasks/{id}/attachments  - Upload file
GET  /api/attachments/{id}        - Download file
GET  /api/attachments/{id}/thumbnail - Get thumbnail
```

### Categories
```
GET    /api/categories         - List categories
POST   /api/categories         - Create category
PUT    /api/categories/{id}    - Update category
DELETE /api/categories/{id}    - Delete category
```

### Notifications
```
GET /api/notifications              - Get notifications
GET /api/notifications/unread-count - Get unread count
PUT /api/notifications/{id}/read    - Mark as read
PUT /api/notifications/read-all     - Mark all as read
```

### Dashboard
```
GET /api/dashboard/stats - Get dashboard statistics
```

## 📲 SMS Notifications (notify.lk)

To enable SMS notifications, add your notify.lk credentials to `/app/backend/.env`:

```env
NOTIFY_LK_USER_ID=your-user-id
NOTIFY_LK_API_KEY=your-api-key
NOTIFY_LK_SENDER_ID=YourSenderID
```

Get credentials at: https://www.notify.lk/

## 🔮 Future Roadmap

### P0 - Critical
- [ ] Firebase Cloud Messaging for push notifications
- [ ] Offline support with service worker
- [ ] Task due date reminders

### P1 - High Priority
- [ ] Performance reports
- [ ] Bulk task operations
- [ ] Export to PDF/Excel

### P2 - Medium Priority
- [ ] AI task suggestions
- [ ] Payroll integration
- [ ] Multi-restaurant support

## 📄 License

Proprietary - Zomoto Tasks © 2026
