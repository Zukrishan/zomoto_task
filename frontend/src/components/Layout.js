import { NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  ClipboardList, 
  Users, 
  BookOpen, 
  LogOut,
  Menu,
  X,
  Tags
} from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from './ui/button';
import NotificationBell from './NotificationBell';

export default function Layout({ children }) {
  const navigate = useNavigate();
  const { user, logout, isOwner, isManager } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', show: true },
    { to: '/tasks', icon: ClipboardList, label: 'Tasks', show: true },
    { to: '/users', icon: Users, label: 'Team', show: isOwner },
    { to: '/task-library', icon: BookOpen, label: 'Library', show: isOwner || isManager },
    { to: '/categories', icon: Tags, label: 'Categories', show: isOwner || isManager },
  ];

  const NavItem = ({ to, icon: Icon, label }) => (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
          isActive 
            ? 'bg-[#E23744] text-white' 
            : 'text-zinc-600 hover:bg-zinc-100'
        }`
      }
      onClick={() => setSidebarOpen(false)}
      data-testid={`nav-${label.toLowerCase()}`}
    >
      <Icon className="h-5 w-5" />
      <span className="font-medium">{label}</span>
    </NavLink>
  );

  return (
    <div className="min-h-screen bg-[#F4F4F5]">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex md:flex-col md:w-64 md:fixed md:inset-y-0 bg-white border-r border-zinc-200 z-30">
        {/* Logo */}
        <div className="p-6 border-b border-zinc-100">
          <img 
            src="https://customer-assets.emergentagent.com/job_task-tracker-735/artifacts/kinqp8ij_Zomoto_Logo-1.png"
            alt="Zomoto Logo"
            className="h-12 w-auto"
          />
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.filter(item => item.show).map(item => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>

        {/* User & Logout */}
        <div className="p-4 border-t border-zinc-100">
          <div className="flex items-center gap-3 mb-3 px-4">
            <div className="w-10 h-10 rounded-full bg-[#E23744]/10 flex items-center justify-center">
              <span className="text-[#E23744] font-semibold">
                {user?.name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-zinc-900 truncate">{user?.name}</p>
              <p className="text-xs text-zinc-500">{user?.role}</p>
            </div>
          </div>
          <Button
            variant="ghost"
            onClick={handleLogout}
            className="w-full justify-start text-zinc-600 hover:text-red-500 hover:bg-red-50 rounded-xl"
            data-testid="logout-btn"
          >
            <LogOut className="h-5 w-5 mr-3" />
            Sign Out
          </Button>
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="md:hidden fixed top-0 left-0 right-0 h-16 bg-white border-b border-zinc-200 z-30 flex items-center justify-between px-4 safe-area-top">
        <img 
          src="https://customer-assets.emergentagent.com/job_task-tracker-735/artifacts/kinqp8ij_Zomoto_Logo-1.png"
          alt="Zomoto Logo"
          className="h-8 w-auto"
        />
        <div className="flex items-center gap-2">
          <NotificationBell />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="rounded-full"
            data-testid="mobile-menu-btn"
          >
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </header>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Mobile Sidebar */}
      <aside className={`md:hidden fixed inset-y-0 left-0 w-64 bg-white z-50 transform transition-transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-6 border-b border-zinc-100">
          <img 
            src="https://customer-assets.emergentagent.com/job_task-tracker-735/artifacts/kinqp8ij_Zomoto_Logo-1.png"
            alt="Zomoto Logo"
            className="h-12 w-auto"
          />
        </div>
        <nav className="p-4 space-y-1">
          {navItems.filter(item => item.show).map(item => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-zinc-100 bg-white safe-area-bottom">
          <div className="flex items-center gap-3 mb-3 px-4">
            <div className="w-10 h-10 rounded-full bg-[#E23744]/10 flex items-center justify-center">
              <span className="text-[#E23744] font-semibold">
                {user?.name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-zinc-900 truncate">{user?.name}</p>
              <p className="text-xs text-zinc-500">{user?.role}</p>
            </div>
          </div>
          <Button
            variant="ghost"
            onClick={handleLogout}
            className="w-full justify-start text-zinc-600 hover:text-red-500 hover:bg-red-50 rounded-xl"
          >
            <LogOut className="h-5 w-5 mr-3" />
            Sign Out
          </Button>
        </div>
      </aside>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-zinc-200 z-30 safe-area-bottom">
        <div className="flex justify-around py-2">
          {navItems.filter(item => item.show).slice(0, 4).map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex flex-col items-center py-2 px-4 ${
                  isActive ? 'text-[#E23744]' : 'text-zinc-400'
                }`
              }
              data-testid={`mobile-nav-${label.toLowerCase()}`}
            >
              <Icon className="h-5 w-5" />
              <span className="text-xs mt-1">{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main className="md:ml-64 pt-16 md:pt-0 min-h-screen">
        <div className="max-w-4xl mx-auto p-4 md:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
