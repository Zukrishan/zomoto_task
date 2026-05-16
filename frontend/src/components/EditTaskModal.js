import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Loader2, Calendar as CalendarIcon, X, Clock } from 'lucide-react';
import { format, addHours, addMinutes } from 'date-fns';
import api from '../lib/api';
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

const CATEGORY_OPTIONS = ['Kitchen', 'Cleaning', 'Maintenance', 'Other'];
const PRIORITY_OPTIONS = [
  { value: 'HIGH', label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
];
const TIME_UNIT_OPTIONS = [
  { value: 'MINUTES', label: 'Minutes' },
  { value: 'HOURS', label: 'Hours' },
];

export default function EditTaskModal({ open, onClose, onSuccess, task }) {
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Parse allocated datetime from task
  const getInitialDate = () => {
    if (task?.allocated_datetime) {
      return new Date(task.allocated_datetime);
    }
    return new Date();
  };
  
  const getInitialTime = () => {
    if (task?.allocated_datetime) {
      return format(new Date(task.allocated_datetime), 'HH:mm');
    }
    return format(new Date(), 'HH:mm');
  };
  
  const [selectedDate, setSelectedDate] = useState(getInitialDate());
  const [selectedTime, setSelectedTime] = useState(getInitialTime());
  const [selectedStaff, setSelectedStaff] = useState(task?.assigned_to || '');
  const [category, setCategory] = useState(task?.category || 'Other');
  const [priority, setPriority] = useState(task?.priority || 'MEDIUM');
  const [timeInterval, setTimeInterval] = useState(task?.time_interval || 30);
  const [timeUnit, setTimeUnit] = useState(task?.time_unit || 'MINUTES');

  const { register, handleSubmit, setValue, reset, formState: { errors } } = useForm({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: task?.title || '',
      description: task?.description || '',
      category: task?.category || 'Other',
      priority: task?.priority || 'MEDIUM',
    },
  });

  useEffect(() => {
    if (open && task) {
      setValue('title', task.title);
      setValue('description', task.description || '');
      setValue('category', task.category);
      setValue('priority', task.priority);
      setCategory(task.category);
      setPriority(task.priority);
      setTimeInterval(task.time_interval || 30);
      setTimeUnit(task.time_unit || 'MINUTES');
      
      if (task.allocated_datetime) {
        const allocatedDate = new Date(task.allocated_datetime);
        setSelectedDate(allocatedDate);
        setSelectedTime(format(allocatedDate, 'HH:mm'));
      }
      
      setSelectedStaff(task.assigned_to || '');
      fetchStaff();
    }
  }, [open, task]);

  const fetchStaff = async () => {
    try {
      const response = await api.get('/users/staff');
      setStaffList(response.data);
    } catch (error) {
      console.error('Failed to fetch staff:', error);
    }
  };

  const onSubmit = async (data) => {
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
        time_interval: parseInt(timeInterval),
        time_unit: timeUnit,
        allocated_datetime: allocatedDateTime.toISOString(),
        assigned_to: selectedStaff || null,
      };
      
      await api.put(`/tasks/${task.id}`, taskData);
      toast.success('Task updated successfully');
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update task');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  // Calculate deadline preview
  const getDeadlinePreview = () => {
    const [hours, minutes] = selectedTime.split(':');
    const allocatedDateTime = new Date(selectedDate);
    allocatedDateTime.setHours(parseInt(hours), parseInt(minutes), 0, 0);
    
    if (timeUnit === 'HOURS') {
      return addHours(allocatedDateTime, parseInt(timeInterval));
    }
    return addMinutes(allocatedDateTime, parseInt(timeInterval));
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="edit-task-modal">
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={handleClose} />
      
      <div className="relative z-50 w-full max-w-md mx-4 bg-white rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto animate-slide-up">
        <div className="sticky top-0 bg-white px-6 py-4 border-b border-zinc-100 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900">Edit Task</h2>
          <button onClick={handleClose} className="p-2 hover:bg-zinc-100 rounded-full" data-testid="close-edit-modal">
            <X className="h-5 w-5 text-zinc-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Task Name</Label>
            <Input
              id="title"
              className="rounded-xl"
              {...register('title')}
              data-testid="edit-task-title"
            />
            {errors.title && <p className="text-sm text-red-500">{errors.title.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              className="rounded-xl resize-none"
              rows={3}
              {...register('description')}
              data-testid="edit-task-description"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="rounded-xl" data-testid="edit-task-category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORY_OPTIONS.map(cat => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger className="rounded-xl" data-testid="edit-task-priority">
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
              Time Allowed
            </Label>
            <div className="grid grid-cols-2 gap-2">
              <Input
                type="number"
                min="1"
                max="1440"
                value={timeInterval}
                onChange={(e) => setTimeInterval(e.target.value)}
                className="rounded-xl"
                data-testid="edit-time-interval"
              />
              <Select value={timeUnit} onValueChange={setTimeUnit}>
                <SelectTrigger className="rounded-xl" data-testid="edit-time-unit">
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

          {/* Allocated Date & Time */}
          <div className="space-y-2">
            <Label>Start Date & Time</Label>
            <div className="grid grid-cols-2 gap-2">
              <Popover>
                <PopoverTrigger asChild>
                  <Button type="button" variant="outline" className="w-full justify-start text-left font-normal rounded-xl h-12" data-testid="edit-task-date">
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
                data-testid="edit-task-time"
              />
            </div>
          </div>

          {/* Deadline Preview */}
          <div className="bg-zinc-50 rounded-xl p-3 text-sm">
            <div className="flex items-center gap-2 text-zinc-600">
              <Clock className="h-4 w-4" />
              <span>New deadline will be:</span>
              <span className="font-medium text-zinc-900">
                {format(getDeadlinePreview(), 'MMM d, yyyy h:mm a')}
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Assign To</Label>
            <Select value={selectedStaff} onValueChange={setSelectedStaff}>
              <SelectTrigger className="rounded-xl" data-testid="edit-task-assign">
                <SelectValue placeholder="Select staff member" />
              </SelectTrigger>
              <SelectContent>
                {staffList.map(staff => (
                  <SelectItem key={staff.id} value={staff.id}>{staff.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button type="submit" disabled={loading} className="w-full h-12 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full" data-testid="save-task-btn">
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Save Changes'}
          </Button>
        </form>
      </div>
    </div>
  );
}
