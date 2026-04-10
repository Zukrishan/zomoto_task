import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Plus, Search, BookOpen, Trash2, Loader2, Calendar, Clock, Repeat, Power, PowerOff, User, Timer, Pencil } from 'lucide-react';
import api, { getErrorMessage } from '../lib/api';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue 
} from '../components/ui/select';
import { Switch } from '../components/ui/switch';

const PRIORITY_OPTIONS = ['HIGH', 'MEDIUM', 'LOW'];
const PRIORITY_COLORS = {
  HIGH: 'bg-red-100 text-red-700',
  MEDIUM: 'bg-amber-100 text-amber-700',
  LOW: 'bg-green-100 text-green-700',
  high: 'bg-red-100 text-red-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-green-100 text-green-700',
};

const DEFAULT_FORM = {
  title: '',
  description: '',
  category: 'Other',
  priority: 'MEDIUM',
  time_interval: 30,
  time_unit: 'MINUTES',
  is_recurring: false,
  day_intervals: '',
  allocated_time: '09:00',
  assigned_to: '',
};

export default function TaskLibraryPage() {
  const [templates, setTemplates] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [creating, setCreating] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [formData, setFormData] = useState({ ...DEFAULT_FORM });

  useEffect(() => {
    fetchTemplates();
    fetchStaff();
    fetchCategories();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await api.get('/task-templates');
      setTemplates(response.data);
    } catch (error) {
      toast.error('Failed to load task library');
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await api.get('/categories');
      setCategories(response.data.map(c => c.name));
    } catch { /* ignore */ }
  };

  const fetchStaff = async () => {
    try {
      const response = await api.get('/users');
      setStaffList(response.data);
    } catch { /* ignore */ }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      toast.error('Task name is required');
      return;
    }
    if (formData.is_recurring && !formData.day_intervals.trim()) {
      toast.error('Day intervals are required for recurring tasks');
      return;
    }
    setCreating(true);
    try {
      const payload = {
        ...formData,
        assigned_to: formData.assigned_to || null,
      };
      if (editingTemplate) {
        await api.put(`/task-templates/${editingTemplate.id}`, payload);
        toast.success('Template updated');
      } else {
        await api.post('/task-templates', payload);
        toast.success('Template created');
      }
      setShowCreate(false);
      setEditingTemplate(null);
      setFormData({ ...DEFAULT_FORM });
      fetchTemplates();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to save template'));
    } finally {
      setCreating(false);
    }
  };

  const handleEdit = (template) => {
    setEditingTemplate(template);
    setFormData({
      title: template.title || '',
      description: template.description || '',
      category: template.category || 'Other',
      priority: template.priority || 'MEDIUM',
      time_interval: template.time_interval || 30,
      time_unit: template.time_unit || 'MINUTES',
      is_recurring: template.is_recurring || false,
      day_intervals: template.day_intervals || '',
      allocated_time: template.allocated_time || '09:00',
      assigned_to: template.assigned_to || '',
    });
    setShowCreate(true);
  };

  const handleDelete = async (templateId) => {
    try {
      await api.delete(`/task-templates/${templateId}`);
      toast.success('Template deleted');
      fetchTemplates();
    } catch (error) {
      toast.error('Failed to delete template');
    }
  };

  const handleToggleActive = async (template) => {
    try {
      await api.put(`/task-templates/${template.id}`, { is_active: !template.is_active });
      toast.success(template.is_active ? 'Rule paused' : 'Rule activated');
      fetchTemplates();
    } catch (error) {
      toast.error('Failed to update template');
    }
  };

  const handleGenerateNow = async () => {
    setGenerating(true);
    try {
      const res = await api.post('/task-templates/generate-now');
      toast.success(res.data.message);
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to generate tasks'));
    } finally {
      setGenerating(false);
    }
  };

  const filteredTemplates = templates.filter(t => 
    (t.title || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const recurringTemplates = filteredTemplates.filter(t => t.is_recurring);
  const simpleTemplates = filteredTemplates.filter(t => !t.is_recurring);

  const openCreateModal = () => {
    setEditingTemplate(null);
    setFormData({ ...DEFAULT_FORM });
    setShowCreate(true);
  };

  return (
    <Layout>
      <div className="space-y-4 pb-24 md:pb-6" data-testid="task-library-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-zinc-900">Task Library</h1>
          <div className="flex gap-2">
            {recurringTemplates.length > 0 && (
              <Button
                variant="outline"
                onClick={handleGenerateNow}
                disabled={generating}
                className="h-10 px-4 rounded-full"
                data-testid="generate-now-btn"
              >
                {generating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Repeat className="h-4 w-4 mr-2" />}
                Generate Now
              </Button>
            )}
            <Button 
              onClick={openCreateModal}
              className="h-10 px-4 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full shadow-md"
              data-testid="add-template-btn"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Task
            </Button>
          </div>
        </div>

        <p className="text-sm text-zinc-500">
          Manage task templates and recurring rules. Recurring rules auto-generate daily tasks on scheduled days.
        </p>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
          <Input
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-12 rounded-xl bg-white border-zinc-200"
            data-testid="search-templates-input"
          />
        </div>

        {/* Recurring Rules Section */}
        {recurringTemplates.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-zinc-800 flex items-center gap-2">
              <Repeat className="h-5 w-5 text-blue-500" />
              Recurring Rules ({recurringTemplates.length})
            </h2>
            {recurringTemplates.map(template => (
              <TemplateCard
                key={template.id}
                template={template}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onToggle={handleToggleActive}
              />
            ))}
          </div>
        )}

        {/* Simple Templates */}
        {simpleTemplates.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-zinc-800 flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-zinc-500" />
              Quick Templates ({simpleTemplates.length})
            </h2>
            {simpleTemplates.map(template => (
              <TemplateCard
                key={template.id}
                template={template}
                onEdit={handleEdit}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && filteredTemplates.length === 0 && (
          <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm">
            <CardContent className="p-8 text-center">
              <BookOpen className="h-12 w-12 text-zinc-300 mx-auto mb-3" />
              <p className="text-zinc-500">No task templates yet</p>
              <p className="text-sm text-zinc-400 mt-1">Create recurring rules or quick templates</p>
              <Button 
                onClick={openCreateModal}
                className="mt-4 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full"
              >
                Add First Template
              </Button>
            </CardContent>
          </Card>
        )}

        {loading && (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#E23744]"></div>
          </div>
        )}
      </div>

      {/* Create/Edit Template Modal */}
      <Dialog open={showCreate} onOpenChange={(open) => { setShowCreate(open); if (!open) setEditingTemplate(null); }}>
        <DialogContent className="sm:max-w-lg rounded-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingTemplate ? 'Edit Template' : 'Add Task Template'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Task Name</Label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="e.g., Clean Kitchen"
                className="rounded-xl"
                required
                data-testid="template-name-input"
              />
            </div>
	     
	    <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Optional description..."
                className="rounded-xl resize-none h-20"
              />
            </div>


            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Category</Label>
                <Select value={formData.category} onValueChange={(v) => setFormData({ ...formData, category: v })}>
                  <SelectTrigger className="rounded-xl" data-testid="template-category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map(cat => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Priority</Label>
                <Select value={formData.priority} onValueChange={(v) => setFormData({ ...formData, priority: v })}>
                  <SelectTrigger className="rounded-xl" data-testid="template-priority">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORITY_OPTIONS.map(pri => (
                      <SelectItem key={pri} value={pri}>{pri}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Time Allowed</Label>
                <Input
                  type="number"
                  min="1"
                  value={formData.time_interval}
                  onChange={(e) => setFormData({ ...formData, time_interval: parseInt(e.target.value) || 30 })}
                  className="rounded-xl"
                />
              </div>
              <div className="space-y-2">
                <Label>Unit</Label>
                <Select value={formData.time_unit} onValueChange={(v) => setFormData({ ...formData, time_unit: v })}>
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MINUTES">Minutes</SelectItem>
                    <SelectItem value="HOURS">Hours</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Assign To</Label>
              <Select value={formData.assigned_to || 'unassigned'} onValueChange={(v) => setFormData({ ...formData, assigned_to: v === 'unassigned' ? '' : v })}>
                <SelectTrigger className="rounded-xl">
                  <SelectValue placeholder="Select staff" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="unassigned">Unassigned</SelectItem>
                  {staffList.map(s => (
                    <SelectItem key={s.id} value={s.id}>{s.name} ({s.role})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Recurring toggle */}
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-xl border border-blue-100">
              <div className="flex items-center gap-2">
                <Repeat className="h-4 w-4 text-blue-600" />
                <Label className="font-medium text-blue-800 cursor-pointer">Recurring Rule</Label>
              </div>
              <Switch
                checked={formData.is_recurring}
                onCheckedChange={(v) => setFormData({ ...formData, is_recurring: v })}
                data-testid="recurring-toggle"
              />
            </div>

            {/* Recurring fields */}
            {formData.is_recurring && (
              <div className="space-y-3 p-3 bg-blue-50/50 rounded-xl border border-blue-100">
                <div className="space-y-2">
                  <Label className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    Day Intervals (days of month)
                  </Label>
                  <Input
                    value={formData.day_intervals}
                    onChange={(e) => setFormData({ ...formData, day_intervals: e.target.value })}
                    placeholder="e.g., 1-5, 10-15, 20"
                    className="rounded-xl bg-white"
                    data-testid="day-intervals-input"
                  />
                  <p className="text-xs text-zinc-400">
                    Enter day ranges. Example: "1-5, 10-15" means days 1-5 and 10-15 of every month
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" />
                    Task Time
                  </Label>
                  <Input
                    type="time"
                    value={formData.allocated_time}
                    onChange={(e) => setFormData({ ...formData, allocated_time: e.target.value })}
                    className="rounded-xl bg-white"
                    data-testid="allocated-time-input"
                  />
                </div>
              </div>
            )}

            <Button
              type="submit"
              disabled={creating}
              className="w-full bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full"
              data-testid="submit-template"
            >
              {creating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              {editingTemplate ? 'Update Template' : 'Add Template'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}

function TemplateCard({ template, onEdit, onDelete, onToggle }) {
  const isRecurring = template.is_recurring;
  const isActive = template.is_active !== false;

  return (
    <Card className={`bg-white rounded-2xl border shadow-sm ${!isActive ? 'opacity-60' : ''} ${isRecurring ? 'border-l-4 border-l-blue-400' : 'border-zinc-100'}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-medium text-zinc-900 line-clamp-1">{template.title}</p>
              {isRecurring && (
                <Badge className={isActive ? 'bg-blue-100 text-blue-700' : 'bg-zinc-100 text-zinc-500'}>
                  {isActive ? 'Active' : 'Paused'}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-3 mt-2 text-sm text-zinc-500 flex-wrap">
              {template.category && <Badge variant="outline">{template.category}</Badge>}
              {template.priority && (
                <Badge className={PRIORITY_COLORS[template.priority]}>{template.priority}</Badge>
              )}
              {template.time_interval > 0 && (
                <span className="flex items-center gap-1">
                  <Timer className="h-3 w-3" />
                  {template.time_interval} {(template.time_unit || 'MINUTES').toLowerCase()}
                </span>
              )}
              {template.assigned_to_name && (
                <span className="flex items-center gap-1">
                  <User className="h-3 w-3" />
                  {template.assigned_to_name}
                </span>
              )}
            </div>
            {isRecurring && (
              <div className="flex items-center gap-3 mt-1.5 text-xs text-blue-600">
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  Days: {template.day_intervals || 'Not set'}
                </span>
                {template.allocated_time && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {template.allocated_time}
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            {isRecurring && onToggle && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onToggle(template)}
                className="h-8 w-8"
                title={isActive ? 'Pause rule' : 'Activate rule'}
                data-testid={`toggle-template-${template.id}`}
              >
                {isActive ? <Power className="h-4 w-4 text-green-500" /> : <PowerOff className="h-4 w-4 text-zinc-400" />}
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onEdit(template)}
              className="h-8 w-8 text-zinc-400 hover:text-blue-500"
              data-testid={`edit-template-${template.id}`}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(template.id)}
              className="h-8 w-8 text-zinc-400 hover:text-red-500"
              data-testid={`delete-template-${template.id}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
