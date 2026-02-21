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
Port: 3306
```

### Connection String
```
mysql://root:password@localhost:3306/zomoto_tasks
```

### Connect via Command Line
```bash
mysql -u root -p zomoto_tasks
```

### View Tables
```bash
mysql -u root -p -D zomoto_tasks -e "SHOW TABLES;"
```

### Database Tables
| Table | Description |
|-------|-------------|
| documents | Generic JSON document storage table for application collections |

### Sample Queries (MySQL)
```sql
-- View all user documents
SELECT JSON_EXTRACT(data, "$.email") AS email
FROM documents
WHERE collection_name = "users";

-- View all task documents
SELECT data
FROM documents
WHERE collection_name = "tasks";
```

## 🛠️ Tech Stack

- **Frontend**: React 19, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, SQLAlchemy
- **Database**: MySQL
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
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=zomoto_tasks
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
