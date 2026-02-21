import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Plus, Filter, Search, ClipboardList, Trash2, X, CheckSquare, Square, Wifi, WifiOff } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';
import { useWebSocket, useWebSocketEvent } from '../context/WebSocketContext';
import api, { getErrorMessage } from '../lib/api';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Checkbox } from '../components/ui/checkbox';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue 
} from '../components/ui/select';
import { Card, CardContent } from '../components/ui/card';
import TaskCard from '../components/TaskCard';
import CreateTaskModal from '../components/CreateTaskModal';

const STATUS_OPTIONS = [
  { value: 'ALL', label: 'All Status' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'IN_PROGRESS', label: 'In Progress' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'NOT_COMPLETED', label: 'Not Completed' },
  { value: 'VERIFIED', label: 'Verified' },
];

const CATEGORY_OPTIONS = [
  { value: 'ALL', label: 'All Categories' },
  { value: 'Kitchen', label: 'Kitchen' },
  { value: 'Cleaning', label: 'Cleaning' },
  { value: 'Maintenance', label: 'Maintenance' },
  { value: 'Other', label: 'Other' },
];

const PRIORITY_OPTIONS = [
  { value: 'ALL', label: 'All Priorities' },
  { value: 'HIGH', label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
];

export default function TasksPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { isOwner, isManager, user } = useAuth();
  const { isConnected } = useWebSocket();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Multi-select state
  const [selectMode, setSelectMode] = useState(false);
  const [selectedTasks, setSelectedTasks] = useState(new Set());
  const [deleting, setDeleting] = useState(false);
  
  const [filters, setFilters] = useState({
    status: searchParams.get('status') || 'ALL',
    category: 'ALL',
    priority: 'ALL',
  });

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.status !== 'ALL') params.append('status', filters.status);
      if (filters.category !== 'ALL') params.append('category', filters.category);
      if (filters.priority !== 'ALL') params.append('priority', filters.priority);
      
      const response = await api.get(`/tasks?${params.toString()}`);
      setTasks(response.data);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    } finally {
      setLoading(false);
    }
  }, [filters.status, filters.category, filters.priority]);

  // Silent fetch (no loading state) for polling - updates both new tasks AND status changes
  const silentFetchTasks = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filters.status !== 'ALL') params.append('status', filters.status);
      if (filters.category !== 'ALL') params.append('category', filters.category);
      if (filters.priority !== 'ALL') params.append('priority', filters.priority);
      
      const response = await api.get(`/tasks?${params.toString()}`);
      
      // Check if there are any changes (new tasks OR status changes)
      const currentTasksMap = new Map(tasks.map(t => [t.id, t]));
      const newTasksMap = new Map(response.data.map(t => [t.id, t]));
      
      let hasChanges = false;
      
      // Check for new tasks
      for (const task of response.data) {
        if (!currentTasksMap.has(task.id)) {
          hasChanges = true;
          if (task.task_type === 'RECURRING') {
            toast.info(`Scheduled task now active: ${task.title}`, { duration: 5000 });
          }
          break;
        }
        // Check for status changes
        const currentTask = currentTasksMap.get(task.id);
        if (currentTask && currentTask.status !== task.status) {
          hasChanges = true;
          break;
        }
      }
      
      // Also check if tasks were removed
      if (!hasChanges) {
        for (const task of tasks) {
          if (!newTasksMap.has(task.id)) {
            hasChanges = true;
            break;
          }
        }
      }
      
      if (hasChanges) {
        setTasks(response.data);
      }
    } catch (error) {
      console.error('Silent fetch failed:', error);
    }
  }, [filters.status, filters.category, filters.priority, tasks]);

  // Fetch tasks on filter change
  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Polling fallback for real-time updates - check every 10 seconds
  useEffect(() => {
    const pollInterval = setInterval(() => {
      silentFetchTasks();
    }, 10000); // 10 seconds for faster status updates
    
    return () => clearInterval(pollInterval);
  }, [silentFetchTasks]);

  // Clear selection when exiting select mode
  useEffect(() => {
    if (!selectMode) {
      setSelectedTasks(new Set());
    }
  }, [selectMode]);

  // WebSocket event handlers for real-time updates
  const handleTaskCreated = useCallback((message) => {
    const newTask = message.data;
    // Check if this task matches current filters
    const matchesFilters = 
      (filters.status === 'ALL' || newTask.status === filters.status) &&
      (filters.category === 'ALL' || newTask.category === filters.category) &&
      (filters.priority === 'ALL' || newTask.priority === filters.priority);
    
    // For staff, also check if assigned to them
    if (user?.role === 'STAFF' && newTask.assigned_to !== user.id) {
      return;
    }
    
    if (matchesFilters) {
      setTasks(prev => [newTask, ...prev]);
      toast.info(`New task: ${newTask.title}`, { duration: 3000 });
    }
  }, [filters, user]);

  const handleTaskUpdated = useCallback((message) => {
    const updatedTask = message.data;
    setTasks(prev => {
      const index = prev.findIndex(t => t.id === updatedTask.id);
      if (index === -1) {
        // Task not in list, might need to add it if it matches filters now
        return prev;
      }
      
      // Check if updated task still matches filters
      const matchesFilters = 
        (filters.status === 'ALL' || updatedTask.status === filters.status) &&
        (filters.category === 'ALL' || updatedTask.category === filters.category) &&
        (filters.priority === 'ALL' || updatedTask.priority === filters.priority);
      
      if (!matchesFilters) {
        // Remove from list if doesn't match anymore
        return prev.filter(t => t.id !== updatedTask.id);
      }
      
      // Update the task in place
      const newTasks = [...prev];
      newTasks[index] = updatedTask;
      return newTasks;
    });
  }, [filters]);

  const handleTaskDeleted = useCallback((message) => {
    const { id } = message.data;
    setTasks(prev => prev.filter(t => t.id !== id));
    setSelectedTasks(prev => {
      const newSet = new Set(prev);
      newSet.delete(id);
      return newSet;
    });
  }, []);

  const handleTasksDeleted = useCallback((message) => {
    const { ids } = message.data;
    setTasks(prev => prev.filter(t => !ids.includes(t.id)));
    setSelectedTasks(prev => {
      const newSet = new Set(prev);
      ids.forEach(id => newSet.delete(id));
      return newSet;
    });
  }, []);

  // Handle recurring task activation (when scheduled time arrives)
  const handleRecurringTaskActivated = useCallback((message) => {
    console.log('handleRecurringTaskActivated called:', message);
    const newTask = message.data;
    if (!newTask) {
      console.error('No task data in message');
      return;
    }
    // Check if already in list
    setTasks(prev => {
      console.log('Current tasks count:', prev.length, 'New task:', newTask.id);
      if (prev.some(t => t.id === newTask.id)) {
        console.log('Task already exists in list');
        return prev; // Already exists
      }
      // Check if matches current filters
      const matchesFilters = 
        (filters.status === 'ALL' || newTask.status === filters.status) &&
        (filters.category === 'ALL' || newTask.category === filters.category) &&
        (filters.priority === 'ALL' || newTask.priority === filters.priority);
      
      console.log('Matches filters:', matchesFilters);
      if (matchesFilters) {
        toast.info(`Scheduled task now active: ${newTask.title}`, { duration: 5000 });
        return [newTask, ...prev];
      }
      return prev;
    });
  }, [filters]);

  // Subscribe to WebSocket events
  useWebSocketEvent('task_created', handleTaskCreated);
  useWebSocketEvent('task_update', handleTaskUpdated);
  useWebSocketEvent('task_deleted', handleTaskDeleted);
  useWebSocketEvent('tasks_deleted', handleTasksDeleted);
  useWebSocketEvent('recurring_task_activated', handleRecurringTaskActivated);

  const filteredTasks = tasks.filter(task => 
    task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    task.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    if (key === 'status') {
      if (value === 'ALL') {
        searchParams.delete('status');
      } else {
        searchParams.set('status', value);
      }
      setSearchParams(searchParams);
    }
  };

  // Multi-select handlers
  const toggleTaskSelection = (taskId) => {
    const newSelected = new Set(selectedTasks);
    if (newSelected.has(taskId)) {
      newSelected.delete(taskId);
    } else {
      newSelected.add(taskId);
    }
    setSelectedTasks(newSelected);
  };

  const selectAllTasks = () => {
    if (selectedTasks.size === filteredTasks.length) {
      // Deselect all
      setSelectedTasks(new Set());
    } else {
      // Select all
      setSelectedTasks(new Set(filteredTasks.map(t => t.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedTasks.size === 0) return;
    
    const confirmMessage = `Are you sure you want to delete ${selectedTasks.size} task${selectedTasks.size > 1 ? 's' : ''}? This action cannot be undone.`;
    if (!window.confirm(confirmMessage)) return;
    
    setDeleting(true);
    try {
      await api.post('/tasks/bulk-delete', {
        task_ids: Array.from(selectedTasks)
      });
      toast.success(`${selectedTasks.size} task${selectedTasks.size > 1 ? 's' : ''} deleted`);
      setSelectedTasks(new Set());
      setSelectMode(false);
      fetchTasks();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete tasks');
    } finally {
      setDeleting(false);
    }
  };

  const isAllSelected = filteredTasks.length > 0 && selectedTasks.size === filteredTasks.length;
  const isSomeSelected = selectedTasks.size > 0 && selectedTasks.size < filteredTasks.length;

  // Long press handler - enters select mode and selects the task
  const handleLongPress = (taskId) => {
    setSelectMode(true);
    setSelectedTasks(new Set([taskId]));
    toast.success('Selection mode activated', { duration: 1500 });
  };

  return (
    <Layout>
      <div className="space-y-4 pb-24 md:pb-6" data-testid="tasks-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-zinc-900">Tasks</h1>
            {/* Live connection indicator */}
            <div 
              className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
                isConnected ? 'bg-emerald-100 text-emerald-700' : 'bg-zinc-100 text-zinc-500'
              }`}
              title={isConnected ? 'Live updates active' : 'Connecting...'}
            >
              {isConnected ? (
                <Wifi className="h-3 w-3" />
              ) : (
                <WifiOff className="h-3 w-3" />
              )}
              <span className="hidden sm:inline">{isConnected ? 'Live' : 'Offline'}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Select Mode Toggle - Hidden on mobile, shown on desktop (Owner/Manager only) */}
            {(isOwner || isManager) && !selectMode && (
              <Button
                variant="outline"
                onClick={() => setSelectMode(true)}
                className="h-10 px-4 rounded-full border-zinc-200 hidden md:flex"
                data-testid="enter-select-mode"
              >
                <CheckSquare className="h-4 w-4 mr-2" />
                Select
              </Button>
            )}
            
            {(isOwner || isManager) && !selectMode && (
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
        </div>

        {/* Long press hint for mobile - shown only when not in select mode */}
        {(isOwner || isManager) && !selectMode && (
          <p className="text-xs text-zinc-400 text-center md:hidden">
            Long press a task to select and delete
          </p>
        )}

        {/* Selection Bar - Shows when in select mode */}
        {selectMode && (
          <div className="flex items-center justify-between bg-zinc-100 rounded-xl p-3 animate-slide-up" data-testid="selection-bar">
            <div className="flex items-center gap-3">
              {/* Select All Checkbox */}
              <button
                onClick={selectAllTasks}
                className="flex items-center gap-2 text-sm font-medium text-zinc-700 hover:text-zinc-900"
                data-testid="select-all-btn"
              >
                {isAllSelected ? (
                  <CheckSquare className="h-5 w-5 text-[#E23744]" />
                ) : isSomeSelected ? (
                  <div className="h-5 w-5 border-2 border-[#E23744] rounded bg-[#E23744]/20 flex items-center justify-center">
                    <div className="w-2 h-0.5 bg-[#E23744]" />
                  </div>
                ) : (
                  <Square className="h-5 w-5 text-zinc-400" />
                )}
                {isAllSelected ? 'Deselect All' : 'Select All'}
              </button>
              
              <span className="text-sm text-zinc-500">
                {selectedTasks.size} of {filteredTasks.length} selected
              </span>
            </div>
            
            <div className="flex items-center gap-2">
              {/* Delete Button */}
              <Button
                onClick={handleBulkDelete}
                disabled={selectedTasks.size === 0 || deleting}
                className="h-9 px-4 bg-red-500 hover:bg-red-600 text-white rounded-full disabled:opacity-50"
                data-testid="bulk-delete-btn"
              >
                {deleting ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                ) : (
                  <Trash2 className="h-4 w-4 mr-2" />
                )}
                Delete ({selectedTasks.size})
              </Button>
              
              {/* Cancel Button */}
              <Button
                variant="ghost"
                onClick={() => setSelectMode(false)}
                className="h-9 px-3 rounded-full"
                data-testid="cancel-select-btn"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Search Bar */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <Input
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-12 rounded-xl bg-white border-zinc-200"
              data-testid="search-input"
            />
          </div>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className={`h-12 px-4 rounded-xl border-zinc-200 ${showFilters ? 'bg-zinc-100' : ''}`}
            data-testid="filter-toggle"
          >
            <Filter className="h-4 w-4" />
          </Button>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="grid grid-cols-3 gap-2 animate-slide-up" data-testid="filters">
            <Select value={filters.status} onValueChange={(v) => handleFilterChange('status', v)}>
              <SelectTrigger className="h-10 rounded-xl" data-testid="status-filter">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filters.category} onValueChange={(v) => handleFilterChange('category', v)}>
              <SelectTrigger className="h-10 rounded-xl" data-testid="category-filter">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                {CATEGORY_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filters.priority} onValueChange={(v) => handleFilterChange('priority', v)}>
              <SelectTrigger className="h-10 rounded-xl" data-testid="priority-filter">
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                {PRIORITY_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Tasks List */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#E23744]"></div>
          </div>
        ) : filteredTasks.length > 0 ? (
          <div className="space-y-3" data-testid="tasks-list">
            {filteredTasks.map((task) => (
              <div key={task.id} className="flex items-start gap-3">
                {/* Checkbox for selection */}
                {selectMode && (
                  <div 
                    className="pt-4 cursor-pointer"
                    onClick={() => toggleTaskSelection(task.id)}
                    data-testid={`task-checkbox-${task.id}`}
                  >
                    {selectedTasks.has(task.id) ? (
                      <CheckSquare className="h-6 w-6 text-[#E23744]" />
                    ) : (
                      <Square className="h-6 w-6 text-zinc-300 hover:text-zinc-400" />
                    )}
                  </div>
                )}
                
                {/* Task Card */}
                <div className={`flex-1 ${selectMode ? 'pointer-events-none' : ''}`}>
                  <TaskCard 
                    task={task} 
                    onClick={selectMode ? () => toggleTaskSelection(task.id) : () => navigate(`/tasks/${task.id}`)}
                    onTaskUpdate={fetchTasks}
                    currentUser={user}
                    onLongPress={handleLongPress}
                    selectMode={selectMode}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm">
            <CardContent className="p-8 text-center">
              <ClipboardList className="h-12 w-12 text-zinc-300 mx-auto mb-3" />
              <p className="text-zinc-500">No tasks found</p>
              {(isOwner || isManager) && (
                <Button 
                  onClick={() => setShowCreateTask(true)}
                  className="mt-4 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full"
                  data-testid="empty-create-task"
                >
                  Create Task
                </Button>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      <CreateTaskModal 
        open={showCreateTask} 
        onClose={() => setShowCreateTask(false)}
        onSuccess={() => {
          setShowCreateTask(false);
          fetchTasks();
        }}
      />
    </Layout>
  );
}
