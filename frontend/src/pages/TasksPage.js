import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Plus, Filter, Search, ClipboardList } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
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
  const { isOwner, isManager } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  const [filters, setFilters] = useState({
    status: searchParams.get('status') || 'ALL',
    category: 'ALL',
    priority: 'ALL',
  });

  useEffect(() => {
    fetchTasks();
  }, [filters]);

  const fetchTasks = async () => {
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
  };

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

  return (
    <Layout>
      <div className="space-y-4 pb-24 md:pb-6" data-testid="tasks-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-zinc-900">Tasks</h1>
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
              <TaskCard 
                key={task.id} 
                task={task} 
                onClick={() => navigate(`/tasks/${task.id}`)} 
              />
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
