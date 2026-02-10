import { format, formatDistanceToNow } from 'date-fns';
import { Clock, User, AlertCircle, Timer, Repeat } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';

const STATUS_CONFIG = {
  PENDING: { label: 'Pending', color: 'bg-blue-100 text-blue-700' },
  IN_PROGRESS: { label: 'In Progress', color: 'bg-amber-100 text-amber-700' },
  COMPLETED: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700' },
  NOT_COMPLETED: { label: 'Not Completed', color: 'bg-red-100 text-red-700' },
  VERIFIED: { label: 'Verified', color: 'bg-purple-100 text-purple-700' },
};

const PRIORITY_CONFIG = {
  HIGH: { color: 'border-l-red-500' },
  MEDIUM: { color: 'border-l-amber-500' },
  LOW: { color: 'border-l-green-500' },
};

export default function TaskCard({ task, onClick }) {
  // Use the is_overdue flag from backend or check deadline
  const isOverdue = task.is_overdue || (task.deadline && new Date(task.deadline) < new Date() && 
    !['COMPLETED', 'VERIFIED', 'NOT_COMPLETED'].includes(task.status));
  
  const isNotCompleted = task.status === 'NOT_COMPLETED';
  const isRecurring = task.task_type === 'RECURRING';

  // Format time remaining or overdue
  const getTimeDisplay = () => {
    if (!task.deadline) return null;
    const deadline = new Date(task.deadline);
    if (isOverdue || isNotCompleted) {
      return `Overdue`;
    }
    return formatDistanceToNow(deadline, { addSuffix: true });
  };

  return (
    <Card 
      className={`rounded-2xl border shadow-sm hover:shadow-md transition-all cursor-pointer border-l-4 
        ${isNotCompleted || isOverdue ? 'bg-red-50 border-red-200' : 'bg-white border-zinc-100'} 
        ${PRIORITY_CONFIG[task.priority]?.color || 'border-l-zinc-300'}`}
      onClick={onClick}
      data-testid={`task-card-${task.id}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className={`font-semibold line-clamp-1 ${isNotCompleted || isOverdue ? 'text-red-700' : 'text-zinc-900'}`} data-testid="task-card-title">
                {task.title}
              </h3>
              {isRecurring && (
                <Repeat className="h-4 w-4 text-blue-500 flex-shrink-0" title="Recurring Task" />
              )}
            </div>
            {task.description && (
              <p className={`text-sm line-clamp-1 mt-1 ${isNotCompleted || isOverdue ? 'text-red-600' : 'text-zinc-500'}`}>
                {task.description}
              </p>
            )}
          </div>
          <Badge className={STATUS_CONFIG[task.status]?.color} data-testid="task-card-status">
            {STATUS_CONFIG[task.status]?.label}
          </Badge>
        </div>

        <div className="flex items-center gap-4 mt-3 text-sm text-zinc-500 flex-wrap">
          {task.assigned_to_name && (
            <div className="flex items-center gap-1">
              <User className="h-3.5 w-3.5" />
              <span className="truncate max-w-[100px]">{task.assigned_to_name}</span>
            </div>
          )}
          
          {/* Time interval display */}
          <div className="flex items-center gap-1">
            <Timer className="h-3.5 w-3.5" />
            <span>{task.time_interval} {task.time_unit?.toLowerCase() || 'minutes'}</span>
          </div>
          
          {/* Deadline / Time remaining */}
          {task.deadline && (
            <div className={`flex items-center gap-1 ${isOverdue || isNotCompleted ? 'text-red-600 font-medium' : ''}`}>
              {isOverdue || isNotCompleted ? <AlertCircle className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
              <span>{getTimeDisplay()}</span>
            </div>
          )}
          
          <Badge variant="outline" className="text-xs">
            {task.category}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
