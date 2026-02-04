import { format } from 'date-fns';
import { Clock, User, AlertCircle } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';

const STATUS_CONFIG = {
  CREATED: { label: 'Created', color: 'bg-zinc-100 text-zinc-700' },
  ASSIGNED: { label: 'Assigned', color: 'bg-blue-100 text-blue-700' },
  IN_PROGRESS: { label: 'In Progress', color: 'bg-amber-100 text-amber-700' },
  COMPLETED: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700' },
  VERIFIED: { label: 'Verified', color: 'bg-purple-100 text-purple-700' },
};

const PRIORITY_CONFIG = {
  HIGH: { color: 'border-l-red-500' },
  MEDIUM: { color: 'border-l-amber-500' },
  LOW: { color: 'border-l-green-500' },
};

export default function TaskCard({ task, onClick }) {
  const isOverdue = task.due_date && new Date(task.due_date) < new Date() && 
    !['COMPLETED', 'VERIFIED'].includes(task.status);

  return (
    <Card 
      className={`bg-white rounded-2xl border border-zinc-100 shadow-sm hover:shadow-md transition-all cursor-pointer border-l-4 ${PRIORITY_CONFIG[task.priority]?.color || 'border-l-zinc-300'}`}
      onClick={onClick}
      data-testid={`task-card-${task.id}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-zinc-900 line-clamp-1" data-testid="task-card-title">
              {task.title}
            </h3>
            {task.description && (
              <p className="text-sm text-zinc-500 line-clamp-1 mt-1">
                {task.description}
              </p>
            )}
          </div>
          <Badge className={STATUS_CONFIG[task.status]?.color} data-testid="task-card-status">
            {STATUS_CONFIG[task.status]?.label}
          </Badge>
        </div>

        <div className="flex items-center gap-4 mt-3 text-sm text-zinc-500">
          {task.assigned_to_name && (
            <div className="flex items-center gap-1">
              <User className="h-3.5 w-3.5" />
              <span className="truncate max-w-[100px]">{task.assigned_to_name}</span>
            </div>
          )}
          {task.due_date && (
            <div className={`flex items-center gap-1 ${isOverdue ? 'text-red-500' : ''}`}>
              {isOverdue ? <AlertCircle className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
              <span>{format(new Date(task.due_date), 'MMM d')}</span>
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
