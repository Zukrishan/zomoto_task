import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { 
  ArrowLeft, 
  Calendar, 
  User, 
  Clock, 
  MessageSquare,
  Paperclip,
  History,
  Send,
  CheckCircle2,
  Play,
  ShieldCheck,
  Loader2,
  Upload,
  Pencil,
  Trash2,
  MoreVertical,
  Timer,
  AlertCircle,
  Camera,
  Repeat
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue 
} from '../components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import EditTaskModal from '../components/EditTaskModal';
import ImageViewer from '../components/ImageViewer';

const STATUS_CONFIG = {
  PENDING: { label: 'Pending', color: 'bg-blue-100 text-blue-700' },
  IN_PROGRESS: { label: 'In Progress', color: 'bg-amber-100 text-amber-700' },
  COMPLETED: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700' },
  NOT_COMPLETED: { label: 'Not Completed', color: 'bg-red-100 text-red-700' },
  VERIFIED: { label: 'Verified', color: 'bg-purple-100 text-purple-700' },
};

const PRIORITY_CONFIG = {
  HIGH: { label: 'High', color: 'bg-red-100 text-red-700' },
  MEDIUM: { label: 'Medium', color: 'bg-amber-100 text-amber-700' },
  LOW: { label: 'Low', color: 'bg-green-100 text-green-700' },
};

export default function TaskDetailPage() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { user, isOwner, isManager, isStaff } = useAuth();
  const [task, setTask] = useState(null);
  const [comments, setComments] = useState([]);
  const [activityLog, setActivityLog] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newComment, setNewComment] = useState('');
  const [showEditModal, setShowEditModal] = useState(false);
  const [viewerImage, setViewerImage] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    fetchTaskData();
    if (isOwner || isManager) {
      fetchStaffList();
    }
  }, [taskId]);

  const fetchTaskData = async () => {
    try {
      const [taskRes, commentsRes, activityRes, attachmentsRes] = await Promise.all([
        api.get(`/tasks/${taskId}`),
        api.get(`/tasks/${taskId}/comments`),
        api.get(`/tasks/${taskId}/activity`),
        api.get(`/tasks/${taskId}/attachments`),
      ]);
      setTask(taskRes.data);
      setComments(commentsRes.data);
      setActivityLog(activityRes.data);
      setAttachments(attachmentsRes.data);
    } catch (error) {
      toast.error('Failed to load task');
      navigate('/tasks');
    } finally {
      setLoading(false);
    }
  };

  const fetchStaffList = async () => {
    try {
      const response = await api.get('/users/staff');
      setStaffList(response.data);
    } catch (error) {
      console.error('Failed to fetch staff:', error);
    }
  };

  const handleStatusUpdate = async (newStatus) => {
    setUpdating(true);
    try {
      await api.put(`/tasks/${taskId}`, { status: newStatus });
      toast.success(`Task marked as ${newStatus.replace('_', ' ').toLowerCase()}`);
      fetchTaskData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    } finally {
      setUpdating(false);
    }
  };

  const handleVerify = async () => {
    setUpdating(true);
    try {
      await api.post(`/tasks/${taskId}/verify`);
      toast.success('Task verified successfully');
      fetchTaskData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify task');
    } finally {
      setUpdating(false);
    }
  };

  const handleReassign = async (staffId) => {
    setUpdating(true);
    try {
      await api.put(`/tasks/${taskId}`, { assigned_to: staffId });
      toast.success('Task reassigned');
      fetchTaskData();
    } catch (error) {
      toast.error('Failed to reassign task');
    } finally {
      setUpdating(false);
    }
  };

  const handleDeleteTask = async () => {
    if (!window.confirm('Are you sure you want to delete this task? This action cannot be undone.')) return;
    try {
      await api.delete(`/tasks/${taskId}`);
      toast.success('Task deleted');
      navigate('/tasks');
    } catch (error) {
      toast.error('Failed to delete task');
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;
    setSubmitting(true);
    try {
      await api.post(`/tasks/${taskId}/comments`, { content: newComment });
      setNewComment('');
      fetchTaskData();
      toast.success('Comment added');
    } catch (error) {
      toast.error('Failed to add comment');
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post(`/tasks/${taskId}/attachments`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('File uploaded');
      fetchTaskData();
    } catch (error) {
      toast.error('Failed to upload file');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#E23744]"></div>
        </div>
      </Layout>
    );
  }

  if (!task) return null;

  const canStartTask = isStaff && task.status === 'ASSIGNED';
  const canCompleteTask = isStaff && task.status === 'IN_PROGRESS';
  const canVerify = (isOwner || isManager) && task.status === 'COMPLETED';
  const canReassign = (isOwner || isManager) && !['VERIFIED'].includes(task.status);
  const canEdit = (isOwner || isManager) && !['VERIFIED'].includes(task.status);
  const canDelete = (isOwner || isManager);

  return (
    <Layout>
      <div className="space-y-4 pb-24 md:pb-6" data-testid="task-detail-page">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => navigate('/tasks')}
            className="rounded-full"
            data-testid="back-button"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-zinc-900 line-clamp-1" data-testid="task-title">
              {task.title}
            </h1>
          </div>
          {/* Edit/Delete Dropdown */}
          {(canEdit || canDelete) && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-full" data-testid="task-menu-btn">
                  <MoreVertical className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {canEdit && (
                  <DropdownMenuItem onClick={() => setShowEditModal(true)} data-testid="edit-task-btn">
                    <Pencil className="h-4 w-4 mr-2" />
                    Edit Task
                  </DropdownMenuItem>
                )}
                {canDelete && (
                  <DropdownMenuItem onClick={handleDeleteTask} className="text-red-600" data-testid="delete-task-btn">
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete Task
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>

        {/* Status & Priority Badges */}
        <div className="flex gap-2 flex-wrap">
          <Badge className={STATUS_CONFIG[task.status]?.color} data-testid="task-status">
            {STATUS_CONFIG[task.status]?.label}
          </Badge>
          <Badge className={PRIORITY_CONFIG[task.priority]?.color} data-testid="task-priority">
            {PRIORITY_CONFIG[task.priority]?.label} Priority
          </Badge>
          <Badge variant="outline" data-testid="task-category">{task.category}</Badge>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2 flex-wrap">
          {canStartTask && (
            <Button
              onClick={() => handleStatusUpdate('IN_PROGRESS')}
              disabled={updating}
              className="bg-amber-500 hover:bg-amber-600 text-white rounded-full"
              data-testid="start-task-btn"
            >
              {updating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              Start Task
            </Button>
          )}
          {canCompleteTask && (
            <Button
              onClick={() => handleStatusUpdate('COMPLETED')}
              disabled={updating}
              className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-full"
              data-testid="complete-task-btn"
            >
              {updating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CheckCircle2 className="h-4 w-4 mr-2" />}
              Mark Complete
            </Button>
          )}
          {canVerify && (
            <Button
              onClick={handleVerify}
              disabled={updating}
              className="bg-purple-500 hover:bg-purple-600 text-white rounded-full"
              data-testid="verify-task-btn"
            >
              {updating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <ShieldCheck className="h-4 w-4 mr-2" />}
              Verify Task
            </Button>
          )}
        </div>

        {/* Task Details Card */}
        <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm">
          <CardContent className="p-5 space-y-4">
            <p className="text-zinc-600" data-testid="task-description">
              {task.description || 'No description'}
            </p>

            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-zinc-100">
              <div className="flex items-center gap-2 text-sm">
                <User className="h-4 w-4 text-zinc-400" />
                <span className="text-zinc-500">Created by:</span>
                <span className="font-medium text-zinc-900">{task.created_by_name}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <User className="h-4 w-4 text-zinc-400" />
                <span className="text-zinc-500">Assigned to:</span>
                <span className="font-medium text-zinc-900">{task.assigned_to_name || 'Unassigned'}</span>
              </div>
              {task.due_date && (
                <div className="flex items-center gap-2 text-sm col-span-2">
                  <Calendar className="h-4 w-4 text-zinc-400" />
                  <span className="text-zinc-500">Due:</span>
                  <span className="font-medium text-zinc-900">
                    {format(new Date(task.due_date), 'PPp')}
                  </span>
                </div>
              )}
              <div className="flex items-center gap-2 text-sm col-span-2">
                <Clock className="h-4 w-4 text-zinc-400" />
                <span className="text-zinc-500">Created:</span>
                <span className="font-medium text-zinc-900">
                  {format(new Date(task.created_at), 'PPp')}
                </span>
              </div>
            </div>

            {/* Reassign Select */}
            {canReassign && (
              <div className="pt-4 border-t border-zinc-100">
                <label className="text-sm font-medium text-zinc-700 mb-2 block">
                  Reassign to:
                </label>
                <Select 
                  value={task.assigned_to || ''} 
                  onValueChange={handleReassign}
                  data-testid="reassign-select"
                >
                  <SelectTrigger className="rounded-xl">
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
            )}
          </CardContent>
        </Card>

        {/* Tabs for Comments, Attachments, Activity */}
        <Tabs defaultValue="comments" className="w-full">
          <TabsList className="grid w-full grid-cols-3 rounded-xl bg-zinc-100 p-1">
            <TabsTrigger value="comments" className="rounded-lg" data-testid="comments-tab">
              <MessageSquare className="h-4 w-4 mr-2" />
              Comments
            </TabsTrigger>
            <TabsTrigger value="attachments" className="rounded-lg" data-testid="attachments-tab">
              <Paperclip className="h-4 w-4 mr-2" />
              Files
            </TabsTrigger>
            <TabsTrigger value="activity" className="rounded-lg" data-testid="activity-tab">
              <History className="h-4 w-4 mr-2" />
              Activity
            </TabsTrigger>
          </TabsList>

          <TabsContent value="comments" className="mt-4 space-y-4">
            {/* Add Comment */}
            <div className="flex gap-2">
              <Textarea
                placeholder="Add a comment..."
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                className="rounded-xl resize-none"
                rows={2}
                data-testid="comment-input"
              />
              <Button
                onClick={handleAddComment}
                disabled={submitting || !newComment.trim()}
                className="bg-[#E23744] hover:bg-[#C42B37] rounded-xl"
                data-testid="submit-comment-btn"
              >
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>

            {/* Comments List */}
            <div className="space-y-3" data-testid="comments-list">
              {comments.length > 0 ? comments.map(comment => (
                <Card key={comment.id} className="bg-zinc-50 rounded-xl border-0">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-medium text-zinc-900">{comment.user_name}</span>
                      <span className="text-xs text-zinc-400">
                        {format(new Date(comment.created_at), 'PPp')}
                      </span>
                    </div>
                    <p className="text-sm text-zinc-600">{comment.content}</p>
                  </CardContent>
                </Card>
              )) : (
                <p className="text-center text-zinc-400 py-8">No comments yet</p>
              )}
            </div>
          </TabsContent>

          <TabsContent value="attachments" className="mt-4 space-y-4">
            {/* Upload Button */}
            <label className="cursor-pointer">
              <div className="flex items-center justify-center gap-2 p-4 border-2 border-dashed border-zinc-200 rounded-xl hover:border-[#E23744] transition-colors">
                <Upload className="h-5 w-5 text-zinc-400" />
                <span className="text-zinc-500">Upload proof / files</span>
              </div>
              <input 
                type="file" 
                className="hidden" 
                onChange={handleFileUpload}
                accept="image/*,.pdf,.doc,.docx"
                data-testid="file-upload-input"
              />
            </label>

            {/* Attachments List */}
            <div className="space-y-2" data-testid="attachments-list">
              {attachments.length > 0 ? attachments.map(attachment => {
                const isImage = attachment.content_type?.startsWith('image/');
                const backendUrl = process.env.REACT_APP_BACKEND_URL;
                const fileUrl = `${backendUrl}${attachment.url}`;
                const thumbUrl = attachment.thumbnail_url ? `${backendUrl}${attachment.thumbnail_url}` : fileUrl;
                
                return (
                  <Card key={attachment.id} className="bg-zinc-50 rounded-xl border-0 overflow-hidden">
                    {/* Preview for images */}
                    {isImage && (
                      <div className="relative">
                        <img 
                          src={thumbUrl}
                          alt={attachment.filename}
                          className="w-full h-48 object-cover cursor-pointer hover:opacity-90 transition-opacity"
                          onClick={() => setViewerImage({ url: fileUrl, filename: attachment.filename })}
                          data-testid={`attachment-preview-${attachment.id}`}
                        />
                        <div className="absolute top-2 right-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => setViewerImage({ url: fileUrl, filename: attachment.filename })}
                            className="bg-white/90 hover:bg-white"
                          >
                            View Full
                          </Button>
                        </div>
                      </div>
                    )}
                    <CardContent className="p-4 flex items-center gap-3">
                      <Paperclip className="h-5 w-5 text-zinc-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-zinc-900 text-sm truncate">{attachment.filename}</p>
                        <p className="text-xs text-zinc-400">
                          Uploaded by {attachment.uploaded_by_name} • {format(new Date(attachment.created_at), 'MMM d, h:mm a')}
                        </p>
                      </div>
                      <a
                        href={fileUrl}
                        download={attachment.filename}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-[#E23744] hover:underline font-medium"
                        data-testid={`download-${attachment.id}`}
                      >
                        Download
                      </a>
                    </CardContent>
                  </Card>
                );
              }) : (
                <p className="text-center text-zinc-400 py-8">No attachments yet. Upload proof of task completion.</p>
              )}
            </div>
          </TabsContent>

          <TabsContent value="activity" className="mt-4">
            <div className="space-y-3" data-testid="activity-list">
              {activityLog.length > 0 ? activityLog.map(log => (
                <div key={log.id} className="flex gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-[#E23744] mt-2 flex-shrink-0"></div>
                  <div>
                    <p className="text-zinc-900">
                      <span className="font-medium">{log.user_name}</span>
                      {' '}{log.details}
                    </p>
                    <p className="text-xs text-zinc-400">
                      {format(new Date(log.created_at), 'PPp')}
                    </p>
                  </div>
                </div>
              )) : (
                <p className="text-center text-zinc-400 py-8">No activity yet</p>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Edit Task Modal */}
      {showEditModal && (
        <EditTaskModal
          open={showEditModal}
          onClose={() => setShowEditModal(false)}
          onSuccess={() => {
            setShowEditModal(false);
            fetchTaskData();
          }}
          task={task}
        />
      )}

      {/* Image Viewer */}
      {viewerImage && (
        <ImageViewer
          open={!!viewerImage}
          onClose={() => setViewerImage(null)}
          imageUrl={viewerImage.url}
          filename={viewerImage.filename}
        />
      )}
    </Layout>
  );
}
