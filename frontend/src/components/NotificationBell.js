import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Check, CheckCheck } from 'lucide-react';
import { format } from 'date-fns';
import api from '../lib/api';
import { Button } from './ui/button';
import { Badge } from './ui/badge';

export default function NotificationBell() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    fetchNotifications();
    fetchUnreadCount();
    
    // Poll for new notifications every 30 seconds
    const interval = setInterval(() => {
      fetchUnreadCount();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchNotifications = async () => {
    try {
      const response = await api.get('/notifications?limit=10');
      setNotifications(response.data);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    }
  };

  const fetchUnreadCount = async () => {
    try {
      const response = await api.get('/notifications/unread-count');
      setUnreadCount(response.data.count);
    } catch (error) {
      console.error('Failed to fetch unread count:', error);
    }
  };

  const handleMarkRead = async (notificationId) => {
    try {
      await api.put(`/notifications/${notificationId}/read`);
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.put('/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const handleNotificationClick = (notification) => {
    if (!notification.is_read) {
      handleMarkRead(notification.id);
    }
    if (notification.task_id) {
      navigate(`/tasks/${notification.task_id}`);
      setShowDropdown(false);
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'TASK_ASSIGNED':
        return '📋';
      case 'TASK_COMPLETED':
        return '✅';
      case 'TASK_VERIFIED':
        return '🏆';
      default:
        return '🔔';
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => {
          setShowDropdown(!showDropdown);
          if (!showDropdown) {
            fetchNotifications();
          }
        }}
        className="relative rounded-full"
        data-testid="notification-bell"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-[#E23744] text-white text-xs flex items-center justify-center font-medium">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </Button>

      {showDropdown && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-2xl shadow-xl border border-zinc-100 z-50 overflow-hidden animate-slide-up" data-testid="notification-dropdown">
          {/* Header */}
          <div className="px-4 py-3 border-b border-zinc-100 flex items-center justify-between bg-zinc-50">
            <h3 className="font-semibold text-zinc-900">Notifications</h3>
            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleMarkAllRead}
                className="text-xs text-[#E23744] hover:text-[#C42B37]"
                data-testid="mark-all-read-btn"
              >
                <CheckCheck className="h-4 w-4 mr-1" />
                Mark all read
              </Button>
            )}
          </div>

          {/* Notifications List */}
          <div className="max-h-80 overflow-y-auto">
            {notifications.length > 0 ? (
              notifications.map(notification => (
                <div
                  key={notification.id}
                  onClick={() => handleNotificationClick(notification)}
                  className={`px-4 py-3 border-b border-zinc-50 hover:bg-zinc-50 cursor-pointer transition-colors ${
                    !notification.is_read ? 'bg-red-50/50' : ''
                  }`}
                  data-testid={`notification-${notification.id}`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-lg">{getNotificationIcon(notification.type)}</span>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${!notification.is_read ? 'font-medium text-zinc-900' : 'text-zinc-700'}`}>
                        {notification.title}
                      </p>
                      <p className="text-xs text-zinc-500 line-clamp-2 mt-0.5">
                        {notification.message}
                      </p>
                      <p className="text-xs text-zinc-400 mt-1">
                        {format(new Date(notification.created_at), 'MMM d, h:mm a')}
                      </p>
                    </div>
                    {!notification.is_read && (
                      <div className="w-2 h-2 rounded-full bg-[#E23744] mt-2"></div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="px-4 py-8 text-center text-zinc-400">
                <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No notifications yet</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
