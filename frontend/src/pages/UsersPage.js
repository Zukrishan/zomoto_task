import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { 
  Plus, 
  Search, 
  Users, 
  MoreVertical,
  UserCheck,
  UserX,
  KeyRound,
  Loader2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api, { getErrorMessage } from '../lib/api';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
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

export default function UsersPage() {
  const { isOwner } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newUser, setNewUser] = useState({
    name: '',
    email: '',
    phone: '',
    password: '123456',
    role: 'STAFF'
  });

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.get('/users');
      setUsers(response.data);
    } catch (error) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post('/users', newUser);
      toast.success('User created successfully');
      setShowCreateUser(false);
      setNewUser({ name: '', email: '', phone: '', password: '123456', role: 'STAFF' });
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    } finally {
      setCreating(false);
    }
  };

  const handleToggleStatus = async (userId, currentStatus) => {
    const newStatus = currentStatus === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await api.put(`/users/${userId}`, { status: newStatus });
      toast.success(`User ${newStatus.toLowerCase()}`);
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update user status');
    }
  };

  const handleResetPassword = async (userId) => {
    try {
      await api.post(`/users/${userId}/reset-password`);
      toast.success('Password reset to 123456');
    } catch (error) {
      toast.error('Failed to reset password');
    }
  };

  const filteredUsers = users.filter(user => 
    user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const ROLE_COLORS = {
    MANAGER: 'bg-blue-100 text-blue-700',
    STAFF: 'bg-green-100 text-green-700',
  };

  return (
    <Layout>
      <div className="space-y-4 pb-24 md:pb-6" data-testid="users-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-zinc-900">Team Members</h1>
          <Button 
            onClick={() => setShowCreateUser(true)}
            className="h-10 px-4 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full shadow-md"
            data-testid="create-user-btn"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add User
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
          <Input
            placeholder="Search users..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-12 rounded-xl bg-white border-zinc-200"
            data-testid="search-users-input"
          />
        </div>

        {/* Users List */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#E23744]"></div>
          </div>
        ) : filteredUsers.length > 0 ? (
          <div className="space-y-3" data-testid="users-list">
            {filteredUsers.map(user => (
              <Card 
                key={user.id} 
                className="bg-white rounded-2xl border border-zinc-100 shadow-sm"
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-[#E23744]/10 flex items-center justify-center">
                        <span className="text-[#E23744] font-semibold">
                          {user.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-zinc-900">{user.name}</p>
                        <p className="text-sm text-zinc-500">{user.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={ROLE_COLORS[user.role] || 'bg-zinc-100 text-zinc-700'}>
                        {user.role}
                      </Badge>
                      <Badge 
                        variant="outline"
                        className={user.status === 'ACTIVE' ? 'border-green-500 text-green-600' : 'border-zinc-300 text-zinc-500'}
                      >
                        {user.status}
                      </Badge>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem 
                            onClick={() => handleToggleStatus(user.id, user.status)}
                            data-testid={`toggle-status-${user.id}`}
                          >
                            {user.status === 'ACTIVE' ? (
                              <>
                                <UserX className="h-4 w-4 mr-2" />
                                Deactivate
                              </>
                            ) : (
                              <>
                                <UserCheck className="h-4 w-4 mr-2" />
                                Activate
                              </>
                            )}
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => handleResetPassword(user.id)}
                            data-testid={`reset-password-${user.id}`}
                          >
                            <KeyRound className="h-4 w-4 mr-2" />
                            Reset Password
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-zinc-100 flex gap-4 text-sm text-zinc-500">
                    <span>📱 {user.phone}</span>
                    {user.employee_id && <span>ID: {user.employee_id}</span>}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm">
            <CardContent className="p-8 text-center">
              <Users className="h-12 w-12 text-zinc-300 mx-auto mb-3" />
              <p className="text-zinc-500">No users found</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Create User Modal */}
      <Dialog open={showCreateUser} onOpenChange={setShowCreateUser}>
        <DialogContent className="sm:max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle>Add New User</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateUser} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Full Name</Label>
              <Input
                id="name"
                value={newUser.name}
                onChange={(e) => setNewUser({...newUser, name: e.target.value})}
                className="rounded-xl"
                required
                data-testid="new-user-name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={newUser.email}
                onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                className="rounded-xl"
                required
                data-testid="new-user-email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input
                id="phone"
                value={newUser.phone}
                onChange={(e) => setNewUser({...newUser, phone: e.target.value})}
                className="rounded-xl"
                required
                data-testid="new-user-phone"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select 
                value={newUser.role} 
                onValueChange={(v) => setNewUser({...newUser, role: v})}
              >
                <SelectTrigger className="rounded-xl" data-testid="new-user-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MANAGER">Manager</SelectItem>
                  <SelectItem value="STAFF">Staff</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={newUser.password}
                onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                placeholder="Enter password"
                className="rounded-xl"
                required
                data-testid="new-user-password"
              />
              <p className="text-xs text-zinc-500">
                Minimum 6 characters
              </p>
            </div>
            <Button
              type="submit"
              disabled={creating}
              className="w-full bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full"
              data-testid="submit-new-user"
            >
              {creating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Create User
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
