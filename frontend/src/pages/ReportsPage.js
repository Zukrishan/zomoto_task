import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { BarChart3, Calendar, Clock, User, Filter, Download, CheckCircle2, AlertCircle, Timer, Eye, ShieldCheck, XCircle } from 'lucide-react';
import api, { getErrorMessage } from '../lib/api';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

const STATUS_CONFIG = {
  PENDING: { label: 'Pending', color: 'bg-blue-100 text-blue-700' },
  IN_PROGRESS: { label: 'In Progress', color: 'bg-amber-100 text-amber-700' },
  COMPLETED: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700' },
  NOT_COMPLETED: { label: 'Not Completed', color: 'bg-red-100 text-red-700' },
  VERIFIED: { label: 'Verified', color: 'bg-purple-100 text-purple-700' },
};

const getStatus = (s) => STATUS_CONFIG[s] || STATUS_CONFIG[(s || '').toUpperCase()] || { label: s || 'Unknown', color: 'bg-zinc-100 text-zinc-600' };

const formatSLTime = (dateStr) => {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleString('en-LK', { 
    timeZone: 'Asia/Colombo',
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true
  });
};

const formatSLDate = (dateStr) => {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-LK', { timeZone: 'Asia/Colombo', day: '2-digit', month: 'short', year: 'numeric' });
};

export default function ReportsPage() {
  const [data, setData] = useState({ tasks: [], summary: {} });
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 10;
  const [loading, setLoading] = useState(true);
  const [staffList, setStaffList] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState({
    status: 'ALL',
    category: 'ALL',
    assigned_to: 'ALL',
    date_from: '',
    date_to: '',
  });

  useEffect(() => {
    fetchStaff();
    fetchCategories();
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters]);

  useEffect(() => {
    fetchReport();
  }, [filters, currentPage]);

  const fetchStaff = async () => {
    try { const r = await api.get('/users'); setStaffList(r.data); } catch {}
  };
  const fetchCategories = async () => {
    try { const r = await api.get('/categories'); setCategories(r.data); } catch {}
  };

  const fetchReport = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('include_archived', 'true');
      if (filters.status !== 'ALL') params.append('status', filters.status);
      if (filters.category !== 'ALL') params.append('category', filters.category);
      if (filters.assigned_to !== 'ALL') params.append('assigned_to', filters.assigned_to);
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);

      params.append('limit', PAGE_SIZE);
      params.append('offset', (currentPage - 1) * PAGE_SIZE);
      const response = await api.get(`/reports/tasks?${params.toString()}`);
      setData(response.data);
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load report'));
    } finally {
      setLoading(false);
    }
  };

  const s = data.summary || {};

  return (
    <Layout>
      <div className="space-y-4 pb-24 md:pb-6" data-testid="reports-page">
        <h1 className="text-2xl font-bold text-zinc-900">Task Reports</h1>
        <p className="text-sm text-zinc-500">View all tasks including verified and archived. All times in Sri Lanka timezone.</p>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SummaryCard label="Total" value={s.total || 0} color="bg-zinc-100 text-zinc-700" />
          <SummaryCard label="Verified" value={s.verified || 0} color="bg-purple-100 text-purple-700" icon={<ShieldCheck className="h-4 w-4" />} />
          <SummaryCard label="Late" value={s.late || 0} color="bg-orange-100 text-orange-700" icon={<AlertCircle className="h-4 w-4" />} />
          <SummaryCard label="Pending" value={s.pending || 0} color="bg-blue-100 text-blue-700" icon={<Clock className="h-4 w-4" />} />
        </div>

        {/* Filters */}
        <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Filter className="h-4 w-4 text-zinc-500" />
              <span className="text-sm font-medium text-zinc-700">Filters</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <Select value={filters.status} onValueChange={(v) => setFilters({ ...filters, status: v })}>
                <SelectTrigger className="rounded-xl" data-testid="report-filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Status</SelectItem>
                  {Object.keys(STATUS_CONFIG).map(k => <SelectItem key={k} value={k}>{STATUS_CONFIG[k].label}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={filters.category} onValueChange={(v) => setFilters({ ...filters, category: v })}>
                <SelectTrigger className="rounded-xl"><SelectValue placeholder="Category" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Categories</SelectItem>
                  {categories.map(c => <SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={filters.assigned_to} onValueChange={(v) => setFilters({ ...filters, assigned_to: v })}>
                <SelectTrigger className="rounded-xl"><SelectValue placeholder="Staff" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Staff</SelectItem>
                  {staffList.map(u => <SelectItem key={u.id} value={u.id}>{u.name}</SelectItem>)}
                </SelectContent>
              </Select>
              <Input
                type="date"
                value={filters.date_from}
                onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
                className="rounded-xl"
                placeholder="From"
              />
              <Input
                type="date"
                value={filters.date_to}
                onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
                className="rounded-xl"
                placeholder="To"
              />
            </div>
          </CardContent>
        </Card>

        {/* Task List */}
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#E23744]" />
          </div>
        ) : data.tasks.length === 0 ? (
          <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm">
            <CardContent className="p-8 text-center">
              <BarChart3 className="h-12 w-12 text-zinc-300 mx-auto mb-3" />
              <p className="text-zinc-500">No tasks found for the selected filters</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-zinc-400">{data.tasks.length} tasks found</p>
            {data.tasks.map(task => (
              <ReportTaskRow key={task.id} task={task} />
            ))}

  {/* Pagination */}
        {data.total > PAGE_SIZE && (
          <div className="flex items-center justify-center gap-2 py-4">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-4 py-2 rounded-full border border-zinc-200 text-sm disabled:opacity-40 hover:bg-zinc-50"
            >
              Previous
            </button>
            <span className="text-sm text-zinc-500">
              Page {currentPage} of {Math.ceil(data.total / PAGE_SIZE)}
            </span>
            <button
              onClick={() => setCurrentPage(p => p + 1)}
              disabled={currentPage >= Math.ceil(data.total / PAGE_SIZE)}
              className="px-4 py-2 rounded-full border border-zinc-200 text-sm disabled:opacity-40 hover:bg-zinc-50"
            >
              Next
            </button>
          </div>
        )}

          </div>
        )}
      </div>
    </Layout>
  );
}

function SummaryCard({ label, value, color, icon }) {
  return (
    <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm">
      <CardContent className="p-4 flex items-center gap-3">
        {icon && <div className={`p-2 rounded-lg ${color}`}>{icon}</div>}
        <div>
          <p className="text-2xl font-bold text-zinc-900">{value}</p>
          <p className="text-xs text-zinc-500">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function ReportTaskRow({ task }) {
  const st = getStatus(task.status);
  return (
    <Card className={`bg-white rounded-xl border shadow-sm ${task.is_archived ? 'border-l-4 border-l-purple-300' : 'border-zinc-100'}`}>
      <CardContent className="p-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-medium text-zinc-900 text-sm line-clamp-1">{task.title}</p>
              <Badge className={st.color + ' text-xs'}>{st.label}</Badge>
              {task.is_late && <Badge className="bg-orange-100 text-orange-700 text-xs">Late</Badge>}
              {task.is_overdue && <Badge className="bg-red-100 text-red-700 text-xs">Overdue</Badge>}
              {task.task_type === 'RECURRING' && <Badge variant="outline" className="text-xs">Recurring</Badge>}
            </div>
            <div className="flex items-center gap-4 mt-1.5 text-xs text-zinc-500 flex-wrap">
              {task.category && <span>{task.category}</span>}
              {task.assigned_to_name && (
                <span className="flex items-center gap-1"><User className="h-3 w-3" />{task.assigned_to_name}</span>
              )}
              <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />{formatSLDate(task.created_at)}</span>
              {task.time_interval > 0 && (
                <span className="flex items-center gap-1"><Timer className="h-3 w-3" />Allowed: {task.time_interval} {(task.time_unit || 'MIN').toLowerCase()}</span>
              )}
              {task.actual_time_taken > 0 && (
                <span className={`flex items-center gap-1 font-medium ${task.is_late ? 'text-orange-600' : 'text-emerald-600'}`}>
                  <Clock className="h-3 w-3" />Took: {task.actual_time_taken} min
                </span>
              )}
            </div>
            {/* Timestamps */}
            <div className="flex items-center gap-4 mt-1 text-xs text-zinc-400 flex-wrap">
              {task.started_at && <span>Started: {formatSLTime(task.started_at)}</span>}
              {task.completed_at && <span>Completed: {formatSLTime(task.completed_at)}</span>}
              {task.verified_at && <span>Verified: {formatSLTime(task.verified_at)}</span>}
            </div>
           {/* Rejection Reason */}
            {task.rejection_reason && (
              <div className="mt-1.5 flex items-start gap-1 text-xs text-red-600 bg-red-50 rounded-lg px-2 py-1">
                <XCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                <span><strong>Rejection reason:</strong> {task.rejection_reason}</span>
              </div>
            )}
            {/* Proof thumbnails */}
            {task.proof_photos && task.proof_photos.length > 0 && (
              <div className="flex items-center gap-1 mt-1.5">
                <Eye className="h-3 w-3 text-zinc-400" />
                <span className="text-xs text-zinc-400">{task.proof_photos.length} proof photo(s)</span>
              </div>
            )}
          </div>
          <div className="text-right flex-shrink-0">
            <Badge variant="outline" className="text-xs">{task.priority}</Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
