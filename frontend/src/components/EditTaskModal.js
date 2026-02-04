import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Loader2, Calendar as CalendarIcon, X } from 'lucide-react';
import { format } from 'date-fns';
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

export default function EditTaskModal({ open, onClose, onSuccess, task }) {
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(task?.due_date ? new Date(task.due_date) : null);
  const [selectedStaff, setSelectedStaff] = useState(task?.assigned_to || '');
  const [category, setCategory] = useState(task?.category || 'Other');
  const [priority, setPriority] = useState(task?.priority || 'MEDIUM');

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
      setSelectedDate(task.due_date ? new Date(task.due_date) : null);
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
      const taskData = {
        title: data.title,
        description: data.description || '',
        category: category,
        priority: priority,
        due_date: selectedDate ? selectedDate.toISOString() : null,
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

          <div className="space-y-2">
            <Label>Due Date</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button type="button" variant="outline" className="w-full justify-start text-left font-normal rounded-xl h-12" data-testid="edit-task-due-date">
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {selectedDate ? format(selectedDate, 'PPP') : 'Select date'}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar mode="single" selected={selectedDate} onSelect={setSelectedDate} initialFocus />
              </PopoverContent>
            </Popover>
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
