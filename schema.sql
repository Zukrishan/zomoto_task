-- Zomoto Tasks - MySQL Database Schema
-- Run: mysql -u root zomoto_tasks < schema.sql

CREATE DATABASE IF NOT EXISTS zomoto_tasks;
USE zomoto_tasks;

-- 1. Users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50) DEFAULT NULL,
    role VARCHAR(20) DEFAULT 'STAFF',
    status VARCHAR(20) DEFAULT 'ACTIVE',
    hashed_password VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email)
);

-- 2. Categories
CREATE TABLE IF NOT EXISTS categories (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    color VARCHAR(50) DEFAULT '#6B7280',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Task Templates
CREATE TABLE IF NOT EXISTS task_templates (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    category VARCHAR(255) DEFAULT NULL,
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    time_interval INT DEFAULT 30,
    time_unit VARCHAR(20) DEFAULT 'MINUTES',
    is_recurring TINYINT(1) DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1,
    day_intervals VARCHAR(255) DEFAULT NULL,
    allocated_time VARCHAR(10) DEFAULT NULL,
    assigned_to VARCHAR(36) DEFAULT NULL,
    assigned_to_name VARCHAR(255) DEFAULT NULL,
    created_by VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

-- 4. Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    category VARCHAR(255) DEFAULT NULL,
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    status VARCHAR(20) DEFAULT 'PENDING',
    task_type VARCHAR(20) DEFAULT 'INSTANT',
    time_interval INT DEFAULT 30,
    time_unit VARCHAR(20) DEFAULT 'MINUTES',
    allocated_datetime DATETIME DEFAULT NULL,
    deadline DATETIME DEFAULT NULL,
    recurrence_pattern VARCHAR(50) DEFAULT NULL,
    recurrence_intervals JSON DEFAULT NULL,
    proof_photos JSON DEFAULT NULL,
    attachments JSON DEFAULT NULL,
    assigned_to VARCHAR(36) DEFAULT NULL,
    assigned_to_name VARCHAR(255) DEFAULT NULL,
    created_by VARCHAR(36) DEFAULT NULL,
    created_by_name VARCHAR(255) DEFAULT NULL,
    started_at DATETIME DEFAULT NULL,
    completed_at DATETIME DEFAULT NULL,
    verified_at DATETIME DEFAULT NULL,
    verified_by VARCHAR(36) DEFAULT NULL,
    is_deleted TINYINT(1) DEFAULT 0,
    is_overdue TINYINT(1) DEFAULT 0,
    parent_task_id VARCHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tasks_status (status),
    INDEX idx_tasks_assigned_to (assigned_to),
    INDEX idx_tasks_is_deleted (is_deleted),
    INDEX idx_tasks_created_at (created_at),
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- 5. Task Comments
CREATE TABLE IF NOT EXISTS task_comments (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) DEFAULT NULL,
    user_name VARCHAR(255) DEFAULT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_comments_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 6. Task Activity Logs
CREATE TABLE IF NOT EXISTS task_activity_logs (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) DEFAULT NULL,
    user_name VARCHAR(255) DEFAULT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_activity_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 7. Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT DEFAULT NULL,
    task_id VARCHAR(36) DEFAULT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notifications_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Seed default categories
INSERT IGNORE INTO categories (id, name, color) VALUES
(UUID(), 'Kitchen', '#EF4444'),
(UUID(), 'Cleaning', '#3B82F6'),
(UUID(), 'Maintenance', '#F59E0B'),
(UUID(), 'Other', '#6B7280');

-- Seed default users (password: 123456 -> bcrypt hash)
-- Generate fresh hashes on your server with: python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('123456'))"
-- Replace the hash below with your generated one
INSERT IGNORE INTO users (id, name, email, role, hashed_password) VALUES
(UUID(), 'Owner', 'owner@zomoto.lk', 'OWNER', '$2b$12$fUi9Y.Ol26dDiWrJ1jQEP.eaGz/O/Sv7oPXWff.Ea9uJaTuKF/W/i'),
(UUID(), 'Manager', 'manager@zomoto.lk', 'MANAGER', '$2b$12$fUi9Y.Ol26dDiWrJ1jQEP.eaGz/O/Sv7oPXWff.Ea9uJaTuKF/W/i'),
(UUID(), 'Staff', 'staff@zomoto.lk', 'STAFF', '$2b$12$fUi9Y.Ol26dDiWrJ1jQEP.eaGz/O/Sv7oPXWff.Ea9uJaTuKF/W/i');
