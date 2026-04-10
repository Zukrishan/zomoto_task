import { useState, useRef, useCallback, useEffect } from "react";
import { formatDistanceToNow } from "date-fns";
import {
  Clock,
  User,
  AlertCircle,
  Timer,
  Repeat,
  Play,
  CheckCircle2,
  Camera,
  ShieldCheck,
  Loader2,
  Eye,
  X,
  XCircle,
  Plus,
  Download,
  Maximize2,
  UserPlus,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import api, { getErrorMessage } from "../lib/api";
import Webcam from "react-webcam";
const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "").replace(
  /\/$/,
  "",
);
const getFullUrl = (url) => {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return `${BACKEND_URL}${url.startsWith("/") ? url : "/" + url}`;
};

const STATUS_CONFIG = {
  PENDING: { label: "Pending", color: "bg-blue-100 text-blue-700" },
  IN_PROGRESS: { label: "In Progress", color: "bg-amber-100 text-amber-700" },
  COMPLETED: { label: "Completed", color: "bg-emerald-100 text-emerald-700" },
  NOT_COMPLETED: { label: "Not Completed", color: "bg-red-100 text-red-700" },
  VERIFIED: { label: "Verified", color: "bg-purple-100 text-purple-700" },
  REJECTED: { label: "Rejected", color: "bg-red-100 text-red-700" },
};

const PRIORITY_CONFIG = {
  HIGH: { color: "border-l-red-500" },
  MEDIUM: { color: "border-l-amber-500" },
  LOW: { color: "border-l-green-500" },
};

// Long press duration in milliseconds
const LONG_PRESS_DURATION = 500;

export default function TaskCard({
  task,
  onClick,
  onTaskUpdate,
  currentUser,
  onLongPress,
  selectMode,
}) {
  const [loading, setLoading] = useState(false);
  const [uploadingProof, setUploadingProof] = useState(false);
  const [showProofModal, setShowProofModal] = useState(false);
  const [enlargedPhoto, setEnlargedPhoto] = useState(null);
  const [showAssignDropdown, setShowAssignDropdown] = useState(false);
const [showCamera, setShowCamera] = useState(false);
const webcamRef = useRef(null);
  const [staffList, setStaffList] = useState([]);
  const [assignLoading, setAssignLoading] = useState(false);
  const assignRef = useRef(null);
  const longPressTimer = useRef(null);
  const isLongPress = useRef(false);

  // Use the is_overdue flag from backend - only tasks that were started (IN_PROGRESS) can be overdue
  // PENDING tasks just haven't been started yet, they're not "overdue"
  const isOverdue =
    task.is_overdue ||
    (task.deadline &&
      new Date(task.deadline) < new Date() &&
      task.status === "IN_PROGRESS");

  const isNotCompleted = task.status === "NOT_COMPLETED";
  const isRecurring = task.task_type === "RECURRING";

  // Role checks
  const isStaff = currentUser?.role === "STAFF";
  const isOwner = currentUser?.role === "OWNER";
  const isManager = currentUser?.role === "MANAGER";
  const isSupervisor = currentUser?.role === "SUPERVISOR";
  const isAssignedToMe = task.assigned_to === currentUser?.id;
  const canSelect = isOwner || isManager;

  // Action visibility
  const canStart = task.status === "PENDING" && isAssignedToMe;
  const canUploadProof = ["IN_PROGRESS", "REJECTED"].includes(task.status) && isAssignedToMe;
  const canComplete =
    ["IN_PROGRESS", "REJECTED"].includes(task.status) &&
    isAssignedToMe &&
    task.proof_photos?.length > 0;
  const canVerify = task.status === "COMPLETED" && (isOwner || isManager || (isSupervisor && task.parent_task_id));
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [rejecting, setRejecting] = useState(false);
  const hasProofPhotos = task.proof_photos && task.proof_photos.length > 0;
  const canAssign =
    (isOwner || isManager) && !task.assigned_to && task.status === "PENDING";
  const canCreateSubTask = isSupervisor && task.assigned_to === currentUser?.id && !task.parent_task_id && task.status === "PENDING";
   const showRejectionReason = task.rejection_reason && isStaff && task.assigned_to === currentUser?.id;
  const canReassign = isSupervisor && !task.parent_task_id && task.assigned_to === currentUser?.id && task.status !== "PENDING" && !["VERIFIED", "COMPLETED", "REJECTED"].includes(task.status);
 const [showSubTaskModal, setShowSubTaskModal] = useState(false);
  const [subTaskData, setSubTaskData] = useState({ title: task.title, assigned_to: '' });
  const [creatingSubTask, setCreatingSubTask] = useState(false);
 const [showReassignModal, setShowReassignModal] = useState(false);
  const [showRejectionReasonModal, setShowRejectionReasonModal] = useState(false);
  const [reassignStaffList, setReassignStaffList] = useState([]);
  const [reassigning, setReassigning] = useState(false);
  // Close assign dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (assignRef.current && !assignRef.current.contains(e.target)) {
        setShowAssignDropdown(false);
      }
    };
    if (showAssignDropdown) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showAssignDropdown]);

  const handleOpenAssign = async (e) => {
    e.stopPropagation();
    if (staffList.length === 0) {
      try {
        const response = await api.get("/users/staff");
        setStaffList(response.data);
      } catch (error) {
        toast.error("Failed to load staff list");
        return;
      }
    }
    setShowAssignDropdown(true);
  };

  const handleAssignStaff = async (e, staffId, staffName) => {
    e.stopPropagation();
    setAssignLoading(true);
    try {
      await api.put(`/tasks/${task.id}`, { assigned_to: staffId });
      toast.success(`Assigned to ${staffName}`);
      setShowAssignDropdown(false);
      onTaskUpdate?.();
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to assign staff"));
    } finally {
      setAssignLoading(false);
    }
  };

  // Long press handlers for touch devices
  const handleTouchStart = useCallback(
    (e) => {
      if (!canSelect || selectMode) return;
      isLongPress.current = false;
      longPressTimer.current = setTimeout(() => {
        isLongPress.current = true;
        // Vibrate on mobile if supported
        if (navigator.vibrate) {
          navigator.vibrate(50);
        }
        onLongPress?.(task.id);
      }, LONG_PRESS_DURATION);
    },
    [canSelect, selectMode, onLongPress, task.id],
  );

  const handleTouchEnd = useCallback((e) => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
    }
    // If it was a long press, prevent the click
    if (isLongPress.current) {
      e.preventDefault();
    }
  }, []);

  const handleTouchMove = useCallback(() => {
    // Cancel long press if user moves finger
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
    }
  }, []);

  const handleClick = (e) => {
    // Don't navigate if it was a long press
    if (isLongPress.current) {
      isLongPress.current = false;
      return;
    }
    onClick?.();
  };

  // Format time remaining or overdue
  const getTimeDisplay = () => {
    if (!task.deadline) return null;
    const deadline = new Date(task.deadline);
    if (isOverdue || isNotCompleted) {
      return `Overdue`;
    }
    return formatDistanceToNow(deadline, { addSuffix: true });
  };

  const handleStartTask = async (e) => {
    e.stopPropagation();
    setLoading(true);
    try {
      await api.post(`/tasks/${task.id}/start`);
      toast.success("Task started!");
      onTaskUpdate?.();
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to start task"));
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteTask = async (e) => {
    e.stopPropagation();
    if (!hasProofPhotos) {
      toast.error("Please upload proof photo first");
      return;
    }
    setLoading(true);
    try {
      await api.post(`/tasks/${task.id}/complete`);
      toast.success("Task completed!");
      onTaskUpdate?.();
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to complete task"));
    } finally {
      setLoading(false);
    }
  };

const handleRejectTask = async () => {
    setRejecting(true);
    try {
      await api.post(`/tasks/${task.id}/reject?reason=${encodeURIComponent(rejectReason)}`);
      setShowRejectModal(false);
      setRejectReason('');
      toast.success('Proof rejected');
      setTimeout(() => { if (onUpdate) onTaskUpdate?.(); }, 500);
    } catch (error) {
      console.error('Reject error:', error);
      toast.error('Failed to reject proof');
    } finally {
      setRejecting(false);
    }
  };

    const handleOpenSubTask = async (e) => {
    e.stopPropagation();
    if (staffList.length === 0) {
      await handleOpenAssign(e);
      setShowAssignDropdown(false);
    }
    setShowSubTaskModal(true);
  };

const handleOpenReassign = async (e) => {
    e.stopPropagation();
    try {
      const response = await api.get('/users/subtask-staff');
      setReassignStaffList(response.data);
    } catch (error) {
      toast.error('Failed to load staff');
    }
    setShowReassignModal(true);
  };

  const handleReassignTask = async (staffId, staffName) => {
    setReassigning(true);
    try {
      await api.put(`/tasks/${task.id}`, { assigned_to: staffId });
      toast.success(`Task reassigned to ${staffName}`);
      setShowReassignModal(false);
      if (onUpdate) onTaskUpdate?.();
    } catch (error) {
      toast.error('Failed to reassign task');
    } finally {
      setReassigning(false);
    }
  };

   const handleCreateSubTask = async () => {
    if (!subTaskData.title || !subTaskData.assigned_to) {
      toast.error('Please fill all fields');
      return;
    }
    setCreatingSubTask(true);
    try {
      await api.post(`/tasks/${task.id}/subtasks`, {
        title: subTaskData.title,
        assigned_to: subTaskData.assigned_to,
        priority: task.priority,
        category: task.category,
        time_interval: task.time_interval,
        time_unit: task.time_unit,
        allocated_datetime: task.allocated_datetime,
        deadline: task.deadline
      });
      toast.success('Sub-task created');
      setShowSubTaskModal(false);
      setSubTaskData({ title: '', assigned_to: '' });
      if (onUpdate) onTaskUpdate?.();
    } catch (error) {
      toast.error('Failed to create sub-task');
    } finally {
      setCreatingSubTask(false);
    }
  };

  const handleVerifyTask = async (e) => {
    e.stopPropagation();
    setLoading(true);
    try {
      await api.post(`/tasks/${task.id}/verify`);
      toast.success("Task verified!");
      onTaskUpdate?.();
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to verify task"));
    } finally {
      setLoading(false);
    }
  };

  const handleProofUpload = async (e) => {
    e.stopPropagation();
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingProof(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      await api.post(`/tasks/${task.id}/proof`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Proof photo uploaded!");
      onTaskUpdate?.();
    } catch (error) {
      toast.error("Failed to upload proof photo");
    } finally {
      setUploadingProof(false);
    }
  };

const handleCapturePhoto = useCallback(async () => {
  const imageSrc = webcamRef.current?.getScreenshot();
  if (!imageSrc) return;
  
  setUploadingProof(true);
  
  try {
    const res = await fetch(imageSrc);
    const blob = await res.blob();
    const file = new File([blob], "proof.jpg", { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", file);
    await api.post(`/tasks/${task.id}/proof`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    toast.success("Proof photo uploaded!");
     if (onUpdate) onTaskUpdate?.();
  } catch (error) {
    toast.error("Failed to upload proof photo");
  } finally {
    setUploadingProof(false);
  }
}, [webcamRef, task.id, onTaskUpdate]);

  const handleViewProof = (e) => {
    e.stopPropagation();
    setShowProofModal(true);
  };

  const closeProofModal = (e) => {
    e?.stopPropagation();
    setShowProofModal(false);
    setEnlargedPhoto(null);
  };

  const handleEnlargePhoto = (photo) => {
    setEnlargedPhoto(photo);
  };

  const closeEnlargedPhoto = (e) => {
    e?.stopPropagation();
    setEnlargedPhoto(null);
  };

  const handleDownloadPhoto = async (photoUrl, index) => {
    try {
      const fullUrl = getFullUrl(photoUrl); // ADD THIS
      const response = await fetch(fullUrl); // USE fullUrl
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `proof_${task.title.replace(/\s+/g, "_")}_${index + 1}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("Photo downloaded!");
    } catch (error) {
      window.open(getFullUrl(photoUrl), "_blank"); // USE getFullUrl here too
    }
  };

  return (
    <Card
      className={`rounded-2xl border shadow-sm hover:shadow-md transition-all cursor-pointer border-l-4 select-none
        ${isNotCompleted || isOverdue ? "bg-red-50 border-red-200" : "bg-white border-zinc-100"} 
        ${PRIORITY_CONFIG[task.priority]?.color || "border-l-zinc-300"}`}
      onClick={handleClick}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onTouchMove={handleTouchMove}
      data-testid={`task-card-${task.id}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3
                className={`font-semibold line-clamp-1 ${isNotCompleted || isOverdue ? "text-red-700" : "text-zinc-900"}`}
                data-testid="task-card-title"
              >
                {task.title}
              </h3>
              {isRecurring && (
                <Repeat
                  className="h-4 w-4 text-blue-500 flex-shrink-0"
                  title="Recurring Task"
                />
              )}
            </div>
            {task.description && (
              <p
                className={`text-sm line-clamp-1 mt-1 ${isNotCompleted || isOverdue ? "text-red-600" : "text-zinc-500"}`}
              >
                {task.description}
              </p>
            )}
          </div>
          <Badge
            className={STATUS_CONFIG[task.status]?.color}
            data-testid="task-card-status"
          >
            {STATUS_CONFIG[task.status]?.label}
          </Badge>
          {task.is_late && (
            <Badge
              className="bg-orange-100 text-orange-700"
              data-testid="task-late-badge"
            >
              Late
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-4 mt-3 text-sm text-zinc-500 flex-wrap">
          {task.assigned_to_name && (
            <div className="flex items-center gap-1">
              <User className="h-3.5 w-3.5" />
              <span className="truncate max-w-[100px]">
                {task.assigned_to_name}
              </span>
            </div>
          )}

          {/* Time interval display */}
          <div className="flex items-center gap-1">
            <Timer className="h-3.5 w-3.5" />
            <span>
              {task.time_interval} {task.time_unit?.toLowerCase() || "minutes"}
            </span>
          </div>

          {/* Deadline / Time remaining */}
          {task.deadline && (
            <div
              className={`flex items-center gap-1 ${isOverdue || isNotCompleted ? "text-red-600 font-medium" : ""}`}
            >
              {isOverdue || isNotCompleted ? (
                <AlertCircle className="h-3.5 w-3.5" />
              ) : (
                <Clock className="h-3.5 w-3.5" />
              )}
              <span>{getTimeDisplay()}</span>
            </div>
          )}

          <Badge variant="outline" className="text-xs">
            {task.category}
          </Badge>
        </div>

        {/* Action Buttons Row */}
         {(canStart ||
          canUploadProof ||
          canComplete ||
          canVerify ||
          hasProofPhotos ||
          canAssign ||
          canCreateSubTask ||
          canReassign ||
          showRejectionReason) && (
          <div
            className="flex items-center gap-2 mt-4 pt-3 border-t border-zinc-100 flex-wrap"
            onClick={(e) => e.stopPropagation()}
          >
          {showRejectionReason && (
              <Button
                size="sm"
                onClick={(e) => { e.stopPropagation(); setShowRejectionReasonModal(true); }}
                className="bg-red-100 hover:bg-red-200 text-red-700 rounded-full h-8 px-4"
              >
                <XCircle className="h-3.5 w-3.5 mr-1" />
                Rejection Reason
              </Button>
            )}

            {/* Assign to Staff Button */}
            {canAssign && (
              <div className="relative" ref={assignRef}>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleOpenAssign}
                  disabled={assignLoading}
                  className="rounded-full h-8 px-4 border-blue-500 text-blue-600 hover:bg-blue-50"
                  data-testid={`assign-task-${task.id}`}
                >
                  {assignLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
                  ) : (
                    <UserPlus className="h-3.5 w-3.5 mr-1" />
                  )}
                  Assign
                </Button>
                {showAssignDropdown && (
                  <div
                    className="absolute left-0 top-full mt-1 w-48 bg-white rounded-xl shadow-lg border border-zinc-200 z-[60] py-1 max-h-48 overflow-y-auto"
                    data-testid="assign-dropdown"
                  >
                    {staffList.length > 0 ? (
                      staffList.map((staff) => (
                        <button
                          key={staff.id}
                          onClick={(e) =>
                            handleAssignStaff(e, staff.id, staff.name)
                          }
                          className="w-full text-left px-3 py-2 text-sm hover:bg-zinc-50 flex items-center gap-2"
                          data-testid={`assign-option-${staff.id}`}
                        >
                          <User className="h-3.5 w-3.5 text-zinc-400" />
                          <span>{staff.name}</span>
                          <Badge
                            variant="outline"
                            className="ml-auto text-[10px]"
                          >
                            {staff.role}
                          </Badge>
                        </button>
                      ))
                    ) : (
                      <div className="px-3 py-2 text-sm text-zinc-400">
                        No staff available
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Start Task Button */}
            {canStart && (
              <Button
                size="sm"
                onClick={handleStartTask}
                disabled={loading}
                className="bg-amber-500 hover:bg-amber-600 text-white rounded-full h-8 px-4"
                data-testid={`start-task-${task.id}`}
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Play className="h-3.5 w-3.5 mr-1" />
                )}
                Start
              </Button>
            )}

            {/* Upload Proof Button (when IN_PROGRESS) */}
           {canUploadProof && (
  <Button
    size="sm"
    variant="outline"
    onClick={(e) => { e.stopPropagation(); setShowCamera(true); }}
    disabled={uploadingProof}
    className={`rounded-full h-8 px-4 ${hasProofPhotos ? "border-emerald-500 text-emerald-600" : "border-amber-500 text-amber-600"}`}
    data-testid={`upload-proof-${task.id}`}
  >
    {uploadingProof ? (
      <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
    ) : (
      <Camera className="h-3.5 w-3.5 mr-1" />
    )}
    {hasProofPhotos
      ? `${task.proof_photos.length} Photo${task.proof_photos.length > 1 ? "s" : ""}`
      : "Add Proof"}
  </Button>
)}

            {/* View Proof Button - visible when there are proof photos */}
            {hasProofPhotos && !canUploadProof && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleViewProof}
                className="rounded-full h-8 px-4 border-blue-500 text-blue-600 hover:bg-blue-50"
                data-testid={`view-proof-${task.id}`}
              >
                <Eye className="h-3.5 w-3.5 mr-1" />
                View Proof ({task.proof_photos.length})
              </Button>
            )}

            {/* Complete Task Button */}
            {canComplete && (
              <Button
                size="sm"
                onClick={handleCompleteTask}
                disabled={loading}
                className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-full h-8 px-4"
                data-testid={`complete-task-${task.id}`}
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                )}
                Complete
              </Button>
            )}

            {/* Cannot complete without proof hint */}
            {task.status === "IN_PROGRESS" &&
              isAssignedToMe &&
              !hasProofPhotos && (
                <span className="text-xs text-amber-600 ml-2">
                  Upload proof to complete
                </span>
              )}
{canReassign && (
              <Button
                size="sm"
                onClick={handleOpenReassign}
                className="bg-blue-500 hover:bg-blue-600 text-white rounded-full h-8 px-4"
              >
                <UserPlus className="h-3.5 w-3.5 mr-1" />
                Reassign
              </Button>
            )}

{canCreateSubTask && (
              <Button
                size="sm"
                onClick={handleOpenSubTask}
                className="bg-orange-500 hover:bg-orange-600 text-white rounded-full h-8 px-4"
              >
                <Plus className="h-3.5 w-3.5 mr-1" />
                Assign Sub-task
              </Button>
            )}

            {/* Verify Task Button (Manager/Owner only) */}
            {canVerify && (
              <Button
                size="sm"
                onClick={handleVerifyTask}
                disabled={loading}
                className="bg-purple-500 hover:bg-purple-600 text-white rounded-full h-8 px-4"
                data-testid={`verify-task-${task.id}`}
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ShieldCheck className="h-3.5 w-3.5 mr-1" />
                )}
                Verify
              </Button>
            )}

{canVerify && (
              <Button
                size="sm"
                onClick={() => setShowRejectModal(true)}
                disabled={loading}
                className="bg-red-500 hover:bg-red-600 text-white rounded-full h-8 px-4"
              >
                <XCircle className="h-3.5 w-3.5 mr-1" />
                Reject
              </Button>
            )}
          </div>
        )}
      </CardContent>

{/* Rejection Reason Modal */}
      {showRejectionReasonModal && (
        <div
          className="fixed inset-0 bg-black/70 z-[200] flex items-center justify-center p-4"
          onClick={(e) => e.stopPropagation()}
        >
          <div
            className="bg-white rounded-2xl p-6 w-full max-w-sm space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-500" />
              <h3 className="text-lg font-semibold text-zinc-900">Proof Rejected</h3>
            </div>
            <p className="text-sm text-zinc-500">Your proof was rejected by the manager. Please re-upload a valid proof.</p>
            <div className="bg-red-50 border border-red-200 rounded-xl p-3">
              <p className="text-sm font-medium text-red-700 mb-1">Reason:</p>
              <p className="text-sm text-red-600">{task.rejection_reason}</p>
            </div>
            <Button
              className="w-full rounded-full bg-zinc-900 hover:bg-zinc-800 text-white"
              onClick={(e) => { e.stopPropagation(); setShowRejectionReasonModal(false); }}
            >
              Got it
            </Button>
          </div>
        </div>
      )}

{/* Reassign Modal */}
      {showReassignModal && (
        <div
          className="fixed inset-0 bg-black/70 z-[200] flex items-center justify-center p-4"
          onClick={(e) => e.stopPropagation()}
        >
          <div
            className="bg-white rounded-2xl p-6 w-full max-w-sm space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-zinc-900">Reassign Task</h3>
            <p className="text-sm text-zinc-500">Select a staff member to reassign this task to.</p>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {reassignStaffList.map(s => (
                <button
                  key={s.id}
                  onClick={(e) => { e.stopPropagation(); handleReassignTask(s.id, s.name); }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-zinc-50 rounded-xl flex items-center gap-2 border border-zinc-100"
                  disabled={reassigning}
                >
                  <User className="h-4 w-4 text-zinc-400" />
                  <span>{s.name}</span>
                  <Badge variant="outline" className="ml-auto text-[10px]">{s.role}</Badge>
                </button>
              ))}
            </div>
            <Button
              variant="outline"
              className="w-full rounded-full"
              onClick={(e) => { e.stopPropagation(); setShowReassignModal(false); }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

{/* Sub-task Modal */}
      {showSubTaskModal && (
        <div
          className="fixed inset-0 bg-black/70 z-[200] flex items-center justify-center p-4"
          onClick={(e) => e.stopPropagation()}
        >
          <div
            className="bg-white rounded-2xl p-6 w-full max-w-sm space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-zinc-900">Create Sub-task</h3>
            <p className="text-sm font-medium text-zinc-700">Task: {task.title}</p>
            <select
              className="w-full border border-zinc-200 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
              value={subTaskData.assigned_to}
              onChange={(e) => setSubTaskData({...subTaskData, assigned_to: e.target.value})}
              onClick={(e) => e.stopPropagation()}
            >
              <option value="">Select staff...</option>
              {staffList.map(s => (
                <option key={s.id} value={s.id}>{s.name} ({s.role})</option>
              ))}
            </select>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1 rounded-full"
                onClick={(e) => { e.stopPropagation(); setShowSubTaskModal(false); setSubTaskData({ title: '', assigned_to: '' }); }}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-orange-500 hover:bg-orange-600 text-white rounded-full"
                onClick={(e) => { e.stopPropagation(); handleCreateSubTask(); }}
                disabled={creatingSubTask}
              >
                {creatingSubTask ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                Create
              </Button>
            </div>
          </div>
        </div>
      )}

{/* Reject Proof Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/70 z-[200] flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm space-y-4">
            <h3 className="text-lg font-semibold text-zinc-900">Reject Proof</h3>
            <p className="text-sm text-zinc-500">Provide a reason for rejecting this proof. The staff member will be notified.</p>
            <textarea
              className="w-full border border-zinc-200 rounded-xl p-3 text-sm resize-none h-24 focus:outline-none focus:ring-2 focus:ring-red-500"
              placeholder="Enter reason..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              onTouchStart={(e) => e.stopPropagation()}
            />
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1 rounded-full"
                onClick={() => { setShowRejectModal(false); setRejectReason(''); }}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-red-500 hover:bg-red-600 text-white rounded-full"
                onClick={(e) => { e.stopPropagation(); handleRejectTask(); }}
                disabled={rejecting}
              >
                {rejecting ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                Reject
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Proof Photos Modal */}
      {showProofModal && hasProofPhotos && (
        <div
          className="fixed inset-0 bg-black/70 z-[200] flex items-center justify-center p-4"
          onClick={closeProofModal}
          data-testid="proof-modal"
        >
          <div
            className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-zinc-100">
              <h3 className="font-semibold text-zinc-900">
                Proof Photos ({task.proof_photos.length})
              </h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={closeProofModal}
                className="rounded-full h-8 w-8"
                data-testid="close-proof-modal"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* Modal Body - Photos Grid */}
            <div className="p-4 overflow-y-auto max-h-[70vh]">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {task.proof_photos.map((photo, index) => (
                  <div key={index} className="relative group">
                    <div className="aspect-video bg-zinc-100 rounded-xl overflow-hidden">
                      <img
                        src={getFullUrl(photo)}
                        alt={`Proof ${index + 1}`}
                        className="w-full h-full object-cover"
                        data-testid={`proof-photo-${index}`}
                      />
                    </div>
                    {/* Action buttons overlay */}
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all rounded-xl flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                      <Button
                        size="sm"
                        onClick={() => handleEnlargePhoto(photo)}
                        className="bg-white text-zinc-900 hover:bg-zinc-100 rounded-full h-10 w-10 p-0"
                        data-testid={`enlarge-photo-${index}`}
                        title="Enlarge"
                      >
                        <Maximize2 className="h-5 w-5" />
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleDownloadPhoto(photo, index)}
                        className="bg-white text-zinc-900 hover:bg-zinc-100 rounded-full h-10 w-10 p-0"
                        data-testid={`download-photo-${index}`}
                        title="Download"
                      >
                        <Download className="h-5 w-5" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Enlarged Photo Lightbox */}
      {enlargedPhoto && (
        <div
          className="fixed inset-0 bg-black/90 z-[250] flex items-center justify-center p-4"
          onClick={closeEnlargedPhoto}
          data-testid="enlarged-photo-modal"
        >
          <div className="relative max-w-[95vw] max-h-[95vh]">
            <img
              src={getFullUrl(enlargedPhoto)}
              alt="Enlarged proof"
              className="max-w-full max-h-[90vh] object-contain rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
            {/* Close button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={closeEnlargedPhoto}
              className="absolute top-2 right-2 bg-black/50 hover:bg-black/70 text-white rounded-full h-10 w-10"
              data-testid="close-enlarged-photo"
            >
              <X className="h-6 w-6" />
            </Button>
            {/* Download button */}
            <Button
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                const index = task.proof_photos.indexOf(enlargedPhoto);
                handleDownloadPhoto(enlargedPhoto, index >= 0 ? index : 0);
              }}
              className="absolute bottom-4 right-4 bg-white text-zinc-900 hover:bg-zinc-100 rounded-full px-4"
              data-testid="download-enlarged-photo"
            >
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          </div>
        </div>
      )}
{showCamera && (
  <div
    className="fixed inset-0 bg-black/90 z-[300] flex flex-col items-center justify-center p-4"
    onClick={(e) => e.stopPropagation()}
  >
    <div className="bg-white rounded-2xl overflow-hidden w-full max-w-lg">
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-semibold">Take Proof Photo</h3>
        <Button
          variant="ghost"
          size="icon"
          onClick={(e) => { e.stopPropagation(); setShowCamera(false); }}
          className="rounded-full h-8 w-8"
        >
          <X className="h-5 w-5" />
        </Button>
      </div>
      <Webcam
        ref={webcamRef}
        screenshotFormat="image/jpeg"
        videoConstraints={{ facingMode: "environment" }}
        className="w-full"
      />
      <div className="p-4 flex justify-center">
        <Button
          onClick={handleCapturePhoto}
          className="bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full px-8"
        >
          <Camera className="h-4 w-4 mr-2" />
          Capture Photo
        </Button>
      </div>
    </div>
  </div>
)}
    </Card>
  );
}
