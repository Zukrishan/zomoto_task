import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Plus, Search, BookOpen, Trash2, Loader2, Calendar as CalendarIcon, Clock, Repeat, Power, PowerOff, User, Timer, Pencil } from 'lucide-react';
import { format, parseISO } from 'date-fns';
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
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover';
import { Calendar } from '../components/ui/calendar';

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
  allocated_time: '09:00',
  assigned_to: '',
  recurrence_start_date: null,
  recurrence_end_date: null,
  frequency_days: 1,
  is_infinite: true,
  weekdays: [],
  schedule_mode: 'frequency',
  weekday_times: [{ weekdays: [], time: '09:00' }],
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
    if (formData.is_recurring) {
      if (!formData.recurrence_start_date) {
        toast.error('Start date is required for recurring tasks');
        return;
      }
      if (!formData.frequency_days || formData.frequency_days < 1) {
        toast.error('Frequency must be at least 1 day');
        return;
      }
      if (!formData.is_infinite && formData.recurrence_end_date && formData.recurrence_end_date < formData.recurrence_start_date) {
        toast.error('End date must be after start date');
        return;
      }
    }
    setCreating(true);
    try {
      const payload = {
        title: formData.title,
        description: formData.description,
        category: formData.category,
        priority: formData.priority,
        time_interval: formData.time_interval,
        time_unit: formData.time_unit,
        is_recurring: formData.is_recurring,
        allocated_time: formData.allocated_time,
        assigned_to: formData.assigned_to || null,
        ...(formData.is_recurring && {
          recurrence_start_date: formData.recurrence_start_date ? format(formData.recurrence_start_date, 'yyyy-MM-dd') : null,
          recurrence_end_date: (!formData.is_infinite && formData.recurrence_end_date) ? format(formData.recurrence_end_date, 'yyyy-MM-dd') : null,
          ...(formData.schedule_mode === 'weekday_groups'
            ? {
                weekday_times: formData.weekday_times.filter(g => g.weekdays.length > 0),
                weekdays: null,
                frequency_days: null,
              }
            : {
                weekday_times: null,
                weekdays: formData.weekdays.length > 0 ? formData.weekdays : null,
                frequency_days: parseInt(formData.frequency_days) || 1,
              }
          ),
        }),
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
      allocated_time: template.allocated_time || '09:00',
      assigned_to: template.assigned_to || '',
      recurrence_start_date: template.recurrence_start_date ? parseISO(template.recurrence_start_date) : null,
      recurrence_end_date: template.recurrence_end_date ? parseISO(template.recurrence_end_date) : null,
      frequency_days: template.frequency_days || 1,
      is_infinite: template.recurrence_end_date == null,
      weekdays: template.weekdays || [],
      schedule_mode: (template.weekday_times && template.weekday_times.length > 0) ? 'weekday_groups' : 'frequency',
      weekday_times: (template.weekday_times && template.weekday_times.length > 0)
        ? template.weekday_times
        : [{ weekdays: [], time: '09:00' }],
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
                {/* Start Date */}
                <div className="space-y-1">
                  <Label className="flex items-center gap-1">
                    <CalendarIcon className="h-3.5 w-3.5" />
                    Start Date
                  </Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button type="button" variant="outline" className="w-full justify-start rounded-xl bg-white" data-testid="recurrence-start-date-btn">
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {formData.recurrence_start_date ? format(formData.recurrence_start_date, 'MMM d, yyyy') : 'Pick a start date'}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={formData.recurrence_start_date}
                        onSelect={(d) => setFormData({ ...formData, recurrence_start_date: d || null })}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                {/* End Date + Infinite toggle */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-1">
                      <CalendarIcon className="h-3.5 w-3.5" />
                      End Date
                    </Label>
                    <div className="flex items-center gap-2 text-sm text-blue-700">
                      <span>Runs forever</span>
                      <Switch
                        checked={formData.is_infinite}
                        onCheckedChange={(v) => setFormData({ ...formData, is_infinite: v, recurrence_end_date: v ? null : formData.recurrence_end_date })}
                        data-testid="infinite-toggle"
                      />
                    </div>
                  </div>
                  {!formData.is_infinite && (
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button type="button" variant="outline" className="w-full justify-start rounded-xl bg-white" data-testid="recurrence-end-date-btn">
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {formData.recurrence_end_date ? format(formData.recurrence_end_date, 'MMM d, yyyy') : 'Pick an end date'}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={formData.recurrence_end_date}
                          onSelect={(d) => setFormData({ ...formData, recurrence_end_date: d || null })}
                          disabled={(d) => formData.recurrence_start_date && d < formData.recurrence_start_date}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  )}
                </div>

                {/* Schedule Mode Toggle */}
                <div className="flex gap-2">
                  <button type="button"
                    onClick={() => setFormData({ ...formData, schedule_mode: 'frequency' })}
                    className={`flex-1 py-2 rounded-xl text-xs font-medium border transition-colors ${
                      formData.schedule_mode === 'frequency'
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-zinc-600 border-zinc-200'
                    }`}
                    data-testid="mode-frequency-btn"
                  >
                    Every N days
                  </button>
                  <button type="button"
                    onClick={() => setFormData({ ...formData, schedule_mode: 'weekday_groups' })}
                    className={`flex-1 py-2 rounded-xl text-xs font-medium border transition-colors ${
                      formData.schedule_mode === 'weekday_groups'
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-zinc-600 border-zinc-200'
                    }`}
                    data-testid="mode-weekday-btn"
                  >
                    By weekday
                  </button>
                </div>

                {/* Frequency mode */}
                {formData.schedule_mode === 'frequency' && (
                  <>
                    <div className="space-y-1">
                      <Label className="flex items-center gap-1">
                        <Repeat className="h-3.5 w-3.5" />
                        Repeat every
                      </Label>
                      <div className="flex items-center gap-2">
                        <Input
                          type="number"
                          min="1"
                          max="365"
                          value={formData.frequency_days}
                          onChange={(e) => setFormData({ ...formData, frequency_days: parseInt(e.target.value) || 1 })}
                          className="w-24 rounded-xl bg-white"
                          data-testid="frequency-days-input"
                        />
                        <span className="text-sm text-blue-700">
                          {formData.frequency_days === 1 ? 'day (daily)' : formData.frequency_days === 7 ? 'days (weekly)' : 'days'}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-1">
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
                  </>
                )}

                {/* Weekday groups mode */}
                {formData.schedule_mode === 'weekday_groups' && (
                  <div className="space-y-2">
                    {formData.weekday_times.map((group, gi) => (
                      <div key={gi} className="p-2 bg-white rounded-xl border border-zinc-200 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-zinc-500 font-medium">Group {gi + 1}</span>
                          {formData.weekday_times.length > 1 && (
                            <button type="button"
                              onClick={() => setFormData({ ...formData, weekday_times: formData.weekday_times.filter((_,i) => i !== gi) })}
                              className="text-xs text-red-400 hover:text-red-600"
                              data-testid={`remove-group-${gi}`}
                            >Remove</button>
                          )}
                        </div>
                        <div className="flex gap-1 flex-wrap">
                          {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((day, di) => (
                            <button key={di} type="button"
                              onClick={() => {
                                const newGroups = [...formData.weekday_times];
                                const days = newGroups[gi].weekdays.includes(di)
                                  ? newGroups[gi].weekdays.filter(d => d !== di)
                                  : [...newGroups[gi].weekdays, di];
                                newGroups[gi] = { ...newGroups[gi], weekdays: days };
                                setFormData({ ...formData, weekday_times: newGroups });
                              }}
                              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                                group.weekdays.includes(di)
                                  ? 'bg-blue-600 text-white'
                                  : 'bg-white text-zinc-600 border border-zinc-200 hover:border-blue-400'
                              }`}
                              data-testid={`group-${gi}-day-${di}`}
                            >{day}</button>
                          ))}
                        </div>
                        <div className="flex items-center gap-2">
                          <Clock className="h-3.5 w-3.5 text-zinc-400" />
                          <Input type="time" value={group.time}
                            onChange={(e) => {
                              const newGroups = [...formData.weekday_times];
                              newGroups[gi] = { ...newGroups[gi], time: e.target.value };
                              setFormData({ ...formData, weekday_times: newGroups });
                            }}
                            className="rounded-lg bg-white h-9 w-32"
                            data-testid={`group-${gi}-time`}
                          />
                          <span className="text-xs text-zinc-400">
                            {group.weekdays.length > 0
                              ? ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].filter((_,i) => group.weekdays.includes(i)).join(', ')
                              : 'No days selected'}
                          </span>
                        </div>
                      </div>
                    ))}
                    <button type="button"
                      onClick={() => setFormData({ ...formData, weekday_times: [...formData.weekday_times, { weekdays: [], time: '09:00' }] })}
                      className="w-full py-2 rounded-xl text-xs text-blue-600 border border-dashed border-blue-300 hover:bg-blue-50"
                      data-testid="add-group-btn"
                    >+ Add another time group</button>
                  </div>
                )}

                {/* Preview */}
                {formData.recurrence_start_date && (
                  formData.schedule_mode === 'weekday_groups'
                    ? formData.weekday_times.some(g => g.weekdays.length > 0) && (
                        <p className="text-xs text-blue-600 bg-blue-100 p-2 rounded-lg">
                          {formData.weekday_times.filter(g => g.weekdays.length > 0).map((g) =>
                            `${['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].filter((_,i) => g.weekdays.includes(i)).join('/')} at ${g.time}`
                          ).join(' · ')}
                          {formData.is_infinite ? ', forever' : formData.recurrence_end_date ? ` until ${format(formData.recurrence_end_date, 'MMM d, yyyy')}` : ''}
                        </p>
                      )
                    : formData.frequency_days && (
                        <p className="text-xs text-blue-600 bg-blue-100 p-2 rounded-lg">
                          Every {formData.frequency_days} day{formData.frequency_days !== 1 ? 's' : ''} from {format(formData.recurrence_start_date, 'MMM d, yyyy')}
                          {formData.is_infinite ? ', forever' : formData.recurrence_end_date ? ` until ${format(formData.recurrence_end_date, 'MMM d, yyyy')}` : ''}
                        </p>
                      )
                )}
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
              <div className="flex items-center gap-3 mt-1.5 text-xs text-blue-600 flex-wrap">
                {template.recurrence_start_date ? (
                  <span className="flex items-center gap-1">
                    <CalendarIcon className="h-3 w-3" />
                    {format(parseISO(template.recurrence_start_date), 'MMM d, yyyy')}
                    {template.recurrence_end_date
                      ? ` → ${format(parseISO(template.recurrence_end_date), 'MMM d, yyyy')}`
                      : ' → forever'}
                  </span>
                ) : template.day_intervals ? (
                  <span className="flex items-center gap-1">
                    <CalendarIcon className="h-3 w-3" />
                    Days: {template.day_intervals}
                  </span>
                ) : null}
                {template.weekday_times && template.weekday_times.length > 0 ? (
                  <span className="flex items-center gap-1 flex-wrap">
                    <Clock className="h-3 w-3" />
                    {template.weekday_times.map((g, i) => (
                      <span key={i}>
                        {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].filter((_,j) => g.weekdays.includes(j)).join('/')}
                        {' '}{g.time}
                        {i < template.weekday_times.length - 1 ? ' · ' : ''}
                      </span>
                    ))}
                  </span>
                ) : template.weekdays && template.weekdays.length > 0 ? (
                  <span>{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].filter((_,i) => template.weekdays.includes(i)).join(', ')}</span>
                ) : template.frequency_days ? (
                  <span>Every {template.frequency_days}d</span>
                ) : null}
                {!template.weekday_times?.length && template.allocated_time && (
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
