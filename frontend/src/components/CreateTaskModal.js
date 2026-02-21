import { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Loader2, Plus, Calendar as CalendarIcon, X, Clock, Repeat, Trash2 } from 'lucide-react';
import { format, addHours, addMinutes, addMonths } from 'date-fns';
import api, { getErrorMessage } from '../lib/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue 
} from './ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from './ui/popover';
import { Calendar } from './ui/calendar';

const taskSchema = z.object({
  title: z.string().min(1, 'Task title is required'),
  description: z.string().optional(),
  category: z.string().min(1, 'Category is required'),
  priority: z.string().min(1, 'Priority is required'),
});

const PRIORITY_OPTIONS = [
  { value: 'HIGH', label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
];
const TIME_UNIT_OPTIONS = [
  { value: 'MINUTES', label: 'Minutes' },
  { value: 'HOURS', label: 'Hours' },
];
const TASK_TYPE_OPTIONS = [
  { value: 'INSTANT', label: 'Instant Task' },
  { value: 'RECURRING', label: 'Recurring Task' },
];

export default function CreateTaskModal({ open, onClose, onSuccess }) {
  const modalRef = useRef(null);
  const [templates, setTemplates] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(() => new Date());
  const [selectedTime, setSelectedTime] = useState(() => {
    try {
      return format(new Date(), 'HH:mm');
    } catch {
      return '09:00';
    }
  });
  const [selectedStaff, setSelectedStaff] = useState('');
  const [showTemplateList, setShowTemplateList] = useState(false);
  const [category, setCategory] = useState('Other');
  const [priority, setPriority] = useState('MEDIUM');
  const [taskType, setTaskType] = useState('INSTANT');
  const [timeInterval, setTimeInterval] = useState(30);
  const [timeUnit, setTimeUnit] = useState('MINUTES');
  
  // Recurring task state
  const [recurrenceIntervals, setRecurrenceIntervals] = useState([
    { start_day: 1, end_day: 5 }
  ]);

  const { register, handleSubmit, setValue, watch, reset, formState: { errors } } = useForm({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: '',
      description: '',
      category: 'Other',
      priority: 'MEDIUM',
    },
  });

  const titleValue = watch('title');

  useEffect(() => {
    if (open) {
      fetchTemplates();
      fetchStaff();
      fetchCategories();
      document.body.style.overflow = 'hidden';
      // Set default allocated time to now
      setSelectedDate(new Date());
      try {
        setSelectedTime(format(new Date(), 'HH:mm'));
      } catch {
        setSelectedTime('09:00');
      }
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  const fetchTemplates = async (search = '') => {
    try {
      const response = await api.get(`/task-templates?search=${search}`);
      setTemplates(response.data);
    } catch (error) {
      console.error('Failed to fetch templates:', error);
    }
  };

  const fetchStaff = async () => {
    try {
      const response = await api.get('/users/staff');
      setStaffList(response.data);
    } catch (error) {
      console.error('Failed to fetch staff:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await api.get('/categories');
      setCategories(response.data);
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    }
  };

  const handleTemplateSelect = (template) => {
    setValue('title', template.title);
    if (template.category) {
      setValue('category', template.category);
      setCategory(template.category);
    }
    if (template.priority) {
      setValue('priority', template.priority);
      setPriority(template.priority);
    }
    setShowTemplateList(false);
  };

  const handleAddNewTemplate = async () => {
    if (!titleValue?.trim()) return;
    
    try {
      await api.post('/task-templates', { title: titleValue });
      toast.success('Task added to library');
      fetchTemplates();
    } catch (error) {
      // If already exists, that's fine
    }
    setShowTemplateList(false);
  };

  // Recurring interval management
  const addInterval = () => {
    if (recurrenceIntervals.length >= 5) {
      toast.error('Maximum 5 intervals allowed');
      return;
    }
    setRecurrenceIntervals([...recurrenceIntervals, { start_day: 1, end_day: 5 }]);
  };

  const removeInterval = (index) => {
    if (recurrenceIntervals.length <= 1) {
      toast.error('At least one interval is required');
      return;
    }
    setRecurrenceIntervals(recurrenceIntervals.filter((_, i) => i !== index));
  };

  const updateInterval = (index, field, value) => {
    const newIntervals = [...recurrenceIntervals];
    newIntervals[index] = { ...newIntervals[index], [field]: parseInt(value) || 1 };
    setRecurrenceIntervals(newIntervals);
  };

  const validateIntervals = () => {
    for (const interval of recurrenceIntervals) {
      if (interval.start_day < 1 || interval.start_day > 31) {
        toast.error('Start day must be between 1 and 31');
        return false;
      }
      if (interval.end_day < 1 || interval.end_day > 31) {
        toast.error('End day must be between 1 and 31');
        return false;
      }
      if (interval.start_day > interval.end_day) {
        toast.error('Start day cannot be greater than end day');
        return false;
      }
    }
    return true;
  };

  const onSubmit = async (data) => {
    // Validate recurring intervals if task type is RECURRING
    if (taskType === 'RECURRING' && !validateIntervals()) {
      return;
    }
    
    setLoading(true);
    try {
      // Combine date and time for allocated_datetime
      const [hours, minutes] = selectedTime.split(':');
      const allocatedDateTime = new Date(selectedDate);
      allocatedDateTime.setHours(parseInt(hours), parseInt(minutes), 0, 0);
      
      const taskData = {
        title: data.title,
        description: data.description || '',
        category: category,
        priority: priority,
        task_type: taskType,
        time_interval: parseInt(timeInterval),
        time_unit: timeUnit,
        allocated_datetime: allocatedDateTime.toISOString(),
        assigned_to: selectedStaff || null,
      };
      
      // Add recurring fields if task type is RECURRING
      if (taskType === 'RECURRING') {
        taskData.recurrence_type = 'MONTHLY';
        // Convert interval ranges to flat list of day numbers
        const daysList = [];
        recurrenceIntervals.forEach(interval => {
          const startDay = parseInt(interval.start_day) || 1;
          const endDay = parseInt(interval.end_day) || startDay;
          for (let day = Math.min(startDay, endDay); day <= Math.max(startDay, endDay); day++) {
            if (day >= 1 && day <= 31 && !daysList.includes(day)) {
              daysList.push(day);
            }
          }
        });
        taskData.recurrence_intervals = daysList.sort((a, b) => a - b);
        taskData.recurrence_end_date = addMonths(new Date(), 1).toISOString();
      }
      
      await api.post('/tasks', taskData);
      toast.success('Task created successfully');
      handleClose();
      onSuccess();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to create task'));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    reset();
    setSelectedDate(new Date());
    try {
      setSelectedTime(format(new Date(), 'HH:mm'));
    } catch {
      setSelectedTime('09:00');
    }
    setSelectedStaff('');
    setCategory('Other');
    setPriority('MEDIUM');
    setTaskType('INSTANT');
    setTimeInterval(30);
    setTimeUnit('MINUTES');
    setRecurrenceIntervals([{ start_day: 1, end_day: 5 }]);
    setShowTemplateList(false);
    onClose();
  };

  // Calculate deadline preview
  const getDeadlinePreview = () => {
    try {
      if (!selectedTime || !selectedDate) return new Date();
      const timeParts = selectedTime.split(':');
      if (timeParts.length !== 2) return new Date();
      
      const hours = parseInt(timeParts[0]) || 0;
      const minutes = parseInt(timeParts[1]) || 0;
      const allocatedDateTime = new Date(selectedDate);
      
      if (isNaN(allocatedDateTime.getTime())) return new Date();
      
      allocatedDateTime.setHours(hours, minutes, 0, 0);
      
      const interval = parseInt(timeInterval) || 30;
      if (timeUnit === 'HOURS') {
        return addHours(allocatedDateTime, interval);
      }
      return addMinutes(allocatedDateTime, interval);
    } catch (e) {
      return new Date();
    }
  };

  const filteredTemplates = templates.filter(t => 
    (t.title || '').toLowerCase().includes(titleValue?.toLowerCase() || '')
  );

  const showAddToLibrary = titleValue && 
    !templates.some(t => (t.title || '').toLowerCase() === titleValue.toLowerCase());

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="create-task-modal">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm" 
        onClick={handleClose}
        data-testid="modal-backdrop"
      />
      
      {/* Modal Content */}
      <div 
        ref={modalRef}
        className="relative z-50 w-full max-w-md mx-4 bg-white rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white px-6 py-4 border-b border-zinc-100 flex items-center justify-between z-10">
          <h2 className="text-lg font-semibold text-zinc-900">Create New Task</h2>
          <button 
            onClick={handleClose}
            className="p-2 hover:bg-zinc-100 rounded-full transition-colors"
            data-testid="close-modal-btn"
          >
            <X className="h-5 w-5 text-zinc-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
          {/* Task Type */}
          <div className="space-y-2">
            <Label>Task Type</Label>
            <Select value={taskType} onValueChange={setTaskType}>
              <SelectTrigger className="rounded-xl" data-testid="task-type-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TASK_TYPE_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>
                    <div className="flex items-center gap-2">
                      {opt.value === 'RECURRING' && <Repeat className="h-4 w-4" />}
                      {opt.label}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Recurring Task Schedule */}
          {taskType === 'RECURRING' && (
            <div className="space-y-3 p-4 bg-blue-50 rounded-xl border border-blue-200">
              <div className="flex items-center justify-between">
                <Label className="text-blue-800 flex items-center gap-2">
                  <Repeat className="h-4 w-4" />
                  Monthly Schedule (Day Intervals)
                </Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addInterval}
                  className="h-8 text-blue-600 border-blue-300 hover:bg-blue-100"
                  data-testid="add-interval-btn"
                >
                  <Plus className="h-3 w-3 mr-1" />
                  Add
                </Button>
              </div>
              
              <p className="text-xs text-blue-600">
                Task will be visible to assigned staff during these day intervals each month
              </p>
              
              <div className="space-y-2">
                {recurrenceIntervals.map((interval, index) => (
                  <div key={index} className="flex items-center gap-2 bg-white p-2 rounded-lg">
                    <span className="text-sm text-zinc-500 w-16">Day</span>
                    <Input
                      type="number"
                      min="1"
                      max="31"
                      value={interval.start_day}
                      onChange={(e) => updateInterval(index, 'start_day', e.target.value)}
                      className="w-16 h-9 text-center rounded-lg"
                      data-testid={`interval-${index}-start`}
                    />
                    <span className="text-zinc-400">to</span>
                    <Input
                      type="number"
                      min="1"
                      max="31"
                      value={interval.end_day}
                      onChange={(e) => updateInterval(index, 'end_day', e.target.value)}
                      className="w-16 h-9 text-center rounded-lg"
                      data-testid={`interval-${index}-end`}
                    />
                    {recurrenceIntervals.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeInterval(index)}
                        className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                        data-testid={`remove-interval-${index}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
              
              {/* Schedule Preview */}
              <div className="text-xs text-blue-700 bg-blue-100 p-2 rounded-lg">
                <strong>Preview:</strong> Task visible on days{' '}
                {recurrenceIntervals.map((interval, i) => (
                  <span key={i}>
                    {interval.start_day}-{interval.end_day}
                    {i < recurrenceIntervals.length - 1 ? ', ' : ''}
                  </span>
                ))}
                {' '}of each month
              </div>
            </div>
          )}

          {/* Task Title with Autocomplete */}
          <div className="space-y-2">
            <Label htmlFor="title">Task Name</Label>
            <div className="relative">
              <Input
                id="title"
                placeholder="Start typing or select from library..."
                className="rounded-xl"
                {...register('title')}
                onFocus={() => setShowTemplateList(true)}
                onBlur={() => setTimeout(() => setShowTemplateList(false), 200)}
                data-testid="task-title-input"
              />
              
              {showTemplateList && titleValue && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-zinc-200 rounded-xl shadow-lg z-[60] max-h-48 overflow-y-auto">
                  {filteredTemplates.map(template => (
                    <div
                      key={template.id}
                      className="px-4 py-2 hover:bg-zinc-50 cursor-pointer text-sm"
                      onClick={() => handleTemplateSelect(template)}
                      data-testid={`template-option-${template.id}`}
                    >
                      {template.name}
                    </div>
                  ))}
                  {showAddToLibrary && (
                    <div
                      className="px-4 py-2 hover:bg-zinc-50 cursor-pointer text-sm text-[#E23744] border-t border-zinc-100 flex items-center gap-2"
                      onClick={handleAddNewTemplate}
                      data-testid="add-to-library-btn"
                    >
                      <Plus className="h-4 w-4" />
                      Add "{titleValue}" to Task Library
                    </div>
                  )}
                  {filteredTemplates.length === 0 && !showAddToLibrary && (
                    <div className="px-4 py-2 text-sm text-zinc-400">
                      No templates found
                    </div>
                  )}
                </div>
              )}
            </div>
            {errors.title && (
              <p className="text-sm text-red-500">{errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              placeholder="Add task details..."
              className="rounded-xl resize-none"
              rows={2}
              {...register('description')}
              data-testid="task-description-input"
            />
          </div>

          {/* Category & Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Category</Label>
              <Select 
                value={category}
                onValueChange={(v) => {
                  setCategory(v);
                  setValue('category', v);
                }}
              >
                <SelectTrigger className="rounded-xl" data-testid="task-category-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {categories.length > 0 ? categories.map(cat => (
                    <SelectItem key={cat.id} value={cat.name}>{cat.name}</SelectItem>
                  )) : (
                    <>
                      <SelectItem value="Kitchen">Kitchen</SelectItem>
                      <SelectItem value="Cleaning">Cleaning</SelectItem>
                      <SelectItem value="Maintenance">Maintenance</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </>
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select 
                value={priority}
                onValueChange={(v) => {
                  setPriority(v);
                  setValue('priority', v);
                }}
              >
                <SelectTrigger className="rounded-xl" data-testid="task-priority-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITY_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Time Interval */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Time Allowed (Required)
            </Label>
            <div className="grid grid-cols-2 gap-2">
              <Input
                type="number"
                min="1"
                max="1440"
                value={timeInterval}
                onChange={(e) => setTimeInterval(e.target.value)}
                className="rounded-xl"
                data-testid="time-interval-input"
              />
              <Select value={timeUnit} onValueChange={setTimeUnit}>
                <SelectTrigger className="rounded-xl" data-testid="time-unit-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIME_UNIT_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Allocated Date & Time - Only for Instant tasks */}
          {taskType === 'INSTANT' && (
            <>
              <div className="space-y-2">
                <Label>Start Date & Time</Label>
                <div className="grid grid-cols-2 gap-2">
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full justify-start text-left font-normal rounded-xl h-12"
                        data-testid="task-date-btn"
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {format(selectedDate, 'MMM d, yyyy')}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={selectedDate}
                        onSelect={(date) => date && setSelectedDate(date)}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                  <Input
                    type="time"
                    value={selectedTime}
                    onChange={(e) => setSelectedTime(e.target.value)}
                    className="rounded-xl h-12"
                    data-testid="task-time-input"
                  />
                </div>
              </div>

              {/* Deadline Preview */}
              <div className="bg-zinc-50 rounded-xl p-3 text-sm">
                <div className="flex items-center gap-2 text-zinc-600">
                  <Clock className="h-4 w-4" />
                  <span>Deadline will be:</span>
                  <span className="font-medium text-zinc-900">
                    {format(getDeadlinePreview(), 'MMM d, yyyy h:mm a')}
                  </span>
                </div>
              </div>
            </>
          )}

          {/* For recurring tasks, show daily time */}
          {taskType === 'RECURRING' && (
            <div className="space-y-2">
              <Label>Daily Start Time</Label>
              <Input
                type="time"
                value={selectedTime}
                onChange={(e) => setSelectedTime(e.target.value)}
                className="rounded-xl h-12"
                data-testid="recurring-time-input"
              />
              <p className="text-xs text-zinc-500">
                Task will appear at this time each scheduled day with {timeInterval} {timeUnit.toLowerCase()} to complete
              </p>
            </div>
          )}

          {/* Assign To */}
          <div className="space-y-2">
            <Label>Assign To (Optional)</Label>
            <Select value={selectedStaff} onValueChange={setSelectedStaff}>
              <SelectTrigger className="rounded-xl" data-testid="task-assign-select">
                <SelectValue placeholder="Select staff member" />
              </SelectTrigger>
              <SelectContent>
                {staffList.map(staff => (
                  <SelectItem key={staff.id} value={staff.id}>
                    {staff.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={loading}
            className="w-full h-12 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full"
            data-testid="submit-task-btn"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              'Create Task'
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
