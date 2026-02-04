import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Loader2, Plus, Calendar as CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';
import api from '../lib/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
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
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from './ui/command';
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

export default function CreateTaskModal({ open, onClose, onSuccess }) {
  const [templates, setTemplates] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedStaff, setSelectedStaff] = useState('');
  const [templateSearch, setTemplateSearch] = useState('');
  const [showTemplateList, setShowTemplateList] = useState(false);

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
    }
  }, [open]);

  useEffect(() => {
    if (templateSearch) {
      fetchTemplates(templateSearch);
    }
  }, [templateSearch]);

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

  const handleTemplateSelect = (template) => {
    setValue('title', template.name);
    if (template.default_category) {
      setValue('category', template.default_category);
    }
    if (template.default_priority) {
      setValue('priority', template.default_priority);
    }
    setShowTemplateList(false);
  };

  const handleAddNewTemplate = async () => {
    if (!titleValue.trim()) return;
    
    try {
      const response = await api.post('/task-templates', { name: titleValue });
      toast.success('Task added to library');
      fetchTemplates();
    } catch (error) {
      // If already exists, that's fine
    }
    setShowTemplateList(false);
  };

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      const taskData = {
        ...data,
        due_date: selectedDate ? selectedDate.toISOString() : null,
        assigned_to: selectedStaff || null,
      };
      
      await api.post('/tasks', taskData);
      toast.success('Task created successfully');
      reset();
      setSelectedDate(null);
      setSelectedStaff('');
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create task');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    reset();
    setSelectedDate(null);
    setSelectedStaff('');
    onClose();
  };

  const filteredTemplates = templates.filter(t => 
    t.name.toLowerCase().includes(titleValue?.toLowerCase() || '')
  );

  const showAddToLibrary = titleValue && 
    !templates.some(t => t.name.toLowerCase() === titleValue.toLowerCase());

  return (
    <Dialog open={open} onOpenChange={handleClose} modal={true}>
      <DialogContent className="sm:max-w-md rounded-2xl max-h-[90vh] overflow-y-auto" onPointerDownOutside={(e) => e.preventDefault()} onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>Create New Task</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-zinc-200 rounded-xl shadow-lg z-50 max-h-48 overflow-y-auto">
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
                defaultValue="Other"
                onValueChange={(v) => setValue('category', v)}
              >
                <SelectTrigger className="rounded-xl" data-testid="task-category-select">
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
              <Select 
                defaultValue="MEDIUM"
                onValueChange={(v) => setValue('priority', v)}
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

          {/* Due Date */}
          <div className="space-y-2">
            <Label>Due Date (Optional)</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-start text-left font-normal rounded-xl h-12"
                  data-testid="task-due-date-btn"
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {selectedDate ? format(selectedDate, 'PPP') : 'Select date'}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={setSelectedDate}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>

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
      </DialogContent>
    </Dialog>
  );
}
