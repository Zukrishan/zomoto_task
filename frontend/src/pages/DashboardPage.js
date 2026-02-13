import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ClipboardList, 
  Clock, 
  CheckCircle2, 
  ShieldCheck,
  Users,
  AlertCircle,
  Plus,
  ArrowRight,
  Wifi
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket, useWebSocketEvent } from '../context/WebSocketContext';
import api from '../lib/api';
import Layout from '../components/Layout';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import TaskCard from '../components/TaskCard';
import CreateTaskModal from '../components/CreateTaskModal';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user, isOwner, isManager, isStaff } = useAuth();
  const { isConnected } = useWebSocket();
  const [stats, setStats] = useState(null);
  const [recentTasks, setRecentTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateTask, setShowCreateTask] = useState(false);

  const fetchDashboardData = useCallback(async () => {
    try {
      const [statsRes, tasksRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/tasks')
      ]);
      setStats(statsRes.data);
      setRecentTasks(tasksRes.data.slice(0, 5));
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // WebSocket handlers for real-time dashboard updates
  const handleTaskEvent = useCallback(() => {
    // Refresh dashboard data when any task event occurs
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Subscribe to all task events
  useWebSocketEvent('task_created', handleTaskEvent);
  useWebSocketEvent('task_update', handleTaskEvent);
  useWebSocketEvent('task_deleted', handleTaskEvent);
  useWebSocketEvent('tasks_deleted', handleTaskEvent);

  const StatCard = ({ icon: Icon, label, value, color, onClick }) => (
    <Card 
      className={`bg-white rounded-2xl border border-zinc-100 shadow-sm cursor-pointer hover:shadow-md transition-shadow ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
      data-testid={`stat-${label.toLowerCase().replace(/\s+/g, '-')}`}
    >
      <CardContent className="p-4 flex items-center gap-4">
        <div className={`p-3 rounded-xl ${color}`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-zinc-900">{value}</p>
          <p className="text-sm text-zinc-500">{label}</p>
        </div>
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#E23744]"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6 pb-24 md:pb-6" data-testid="dashboard-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900" data-testid="greeting">
              Hello, {user?.name?.split(' ')[0]} 👋
            </h1>
            <p className="text-sm text-zinc-500 mt-1">
              {isOwner && 'Restaurant Owner Dashboard'}
              {isManager && 'Manager Dashboard'}
              {isStaff && 'Your Tasks'}
            </p>
          </div>
          {(isOwner || isManager) && (
            <Button 
              onClick={() => setShowCreateTask(true)}
              className="h-10 px-4 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full shadow-md"
              data-testid="create-task-btn"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Task
            </Button>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4">
          <StatCard
            icon={ClipboardList}
            label="Total Tasks"
            value={stats?.total_tasks || 0}
            color="bg-[#E23744]"
            onClick={() => navigate('/tasks')}
          />
          <StatCard
            icon={Clock}
            label="In Progress"
            value={stats?.in_progress || 0}
            color="bg-amber-500"
            onClick={() => navigate('/tasks?status=IN_PROGRESS')}
          />
          <StatCard
            icon={CheckCircle2}
            label="Completed"
            value={stats?.completed || 0}
            color="bg-emerald-500"
            onClick={() => navigate('/tasks?status=COMPLETED')}
          />
          <StatCard
            icon={ShieldCheck}
            label="Verified"
            value={stats?.verified || 0}
            color="bg-blue-500"
            onClick={() => navigate('/tasks?status=VERIFIED')}
          />
        </div>

        {/* Additional Stats for Owner/Manager */}
        {(isOwner || isManager) && (
          <div className="grid grid-cols-3 gap-4">
            <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm" data-testid="stat-to-assign">
              <CardContent className="p-4 text-center">
                <AlertCircle className="h-6 w-6 text-orange-500 mx-auto mb-2" />
                <p className="text-xl font-bold text-zinc-900">{stats?.tasks_to_assign || 0}</p>
                <p className="text-xs text-zinc-500">To Assign</p>
              </CardContent>
            </Card>
            <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm" data-testid="stat-to-verify">
              <CardContent className="p-4 text-center">
                <ShieldCheck className="h-6 w-6 text-blue-500 mx-auto mb-2" />
                <p className="text-xl font-bold text-zinc-900">{stats?.tasks_to_verify || 0}</p>
                <p className="text-xs text-zinc-500">To Verify</p>
              </CardContent>
            </Card>
            <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm" data-testid="stat-total-staff">
              <CardContent className="p-4 text-center">
                <Users className="h-6 w-6 text-purple-500 mx-auto mb-2" />
                <p className="text-xl font-bold text-zinc-900">{stats?.total_staff || 0}</p>
                <p className="text-xs text-zinc-500">Staff</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Recent Tasks */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-zinc-900">Recent Tasks</h2>
            <Button 
              variant="ghost" 
              onClick={() => navigate('/tasks')}
              className="text-sm text-[#E23744] hover:text-[#C42B37]"
              data-testid="view-all-tasks"
            >
              View All <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </div>

          {recentTasks.length > 0 ? (
            <div className="space-y-3">
              {recentTasks.map((task) => (
                <TaskCard 
                  key={task.id} 
                  task={task} 
                  onClick={() => navigate(`/tasks/${task.id}`)}
                  onTaskUpdate={fetchDashboardData}
                  currentUser={user}
                />
              ))}
            </div>
          ) : (
            <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm">
              <CardContent className="p-8 text-center">
                <ClipboardList className="h-12 w-12 text-zinc-300 mx-auto mb-3" />
                <p className="text-zinc-500">No tasks yet</p>
                {(isOwner || isManager) && (
                  <Button 
                    onClick={() => setShowCreateTask(true)}
                    className="mt-4 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full"
                    data-testid="empty-create-task"
                  >
                    Create First Task
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <CreateTaskModal 
        open={showCreateTask} 
        onClose={() => setShowCreateTask(false)}
        onSuccess={() => {
          setShowCreateTask(false);
          fetchDashboardData();
        }}
      />
    </Layout>
  );
}
