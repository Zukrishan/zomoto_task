import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Plus, Search, BookOpen, Trash2, Loader2 } from 'lucide-react';
import api from '../lib/api';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
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

const CATEGORY_OPTIONS = ['Kitchen', 'Cleaning', 'Maintenance', 'Other'];
const PRIORITY_OPTIONS = ['HIGH', 'MEDIUM', 'LOW'];

export default function TaskLibraryPage() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    default_category: '',
    default_priority: ''
  });

  useEffect(() => {
    fetchTemplates();
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

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newTemplate.name.trim()) {
      toast.error('Task name is required');
      return;
    }
    setCreating(true);
    try {
      await api.post('/task-templates', newTemplate);
      toast.success('Task template added');
      setShowCreate(false);
      setNewTemplate({ name: '', default_category: '', default_priority: '' });
      fetchTemplates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create template');
    } finally {
      setCreating(false);
    }
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

  const filteredTemplates = templates.filter(t => 
    t.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const PRIORITY_COLORS = {
    HIGH: 'bg-red-100 text-red-700',
    MEDIUM: 'bg-amber-100 text-amber-700',
    LOW: 'bg-green-100 text-green-700',
  };

  return (
    <Layout>
      <div className="space-y-4 pb-24 md:pb-6" data-testid="task-library-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-zinc-900">Task Library</h1>
          <Button 
            onClick={() => setShowCreate(true)}
            className="h-10 px-4 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full shadow-md"
            data-testid="add-template-btn"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Task
          </Button>
        </div>

        <p className="text-sm text-zinc-500">
          Manage common task templates for quick task creation
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

        {/* Templates List */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#E23744]"></div>
          </div>
        ) : filteredTemplates.length > 0 ? (
          <div className="space-y-3" data-testid="templates-list">
            {filteredTemplates.map(template => (
              <Card 
                key={template.id} 
                className="bg-white rounded-2xl border border-zinc-100 shadow-sm"
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-zinc-900">{template.name}</p>
                      <div className="flex gap-2 mt-2">
                        {template.default_category && (
                          <Badge variant="outline">{template.default_category}</Badge>
                        )}
                        {template.default_priority && (
                          <Badge className={PRIORITY_COLORS[template.default_priority]}>
                            {template.default_priority}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(template.id)}
                      className="h-8 w-8 text-zinc-400 hover:text-red-500"
                      data-testid={`delete-template-${template.id}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="bg-white rounded-2xl border border-zinc-100 shadow-sm">
            <CardContent className="p-8 text-center">
              <BookOpen className="h-12 w-12 text-zinc-300 mx-auto mb-3" />
              <p className="text-zinc-500">No task templates yet</p>
              <Button 
                onClick={() => setShowCreate(true)}
                className="mt-4 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full"
              >
                Add First Template
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Create Template Modal */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle>Add Task Template</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Task Name</Label>
              <Input
                id="name"
                value={newTemplate.name}
                onChange={(e) => setNewTemplate({...newTemplate, name: e.target.value})}
                placeholder="e.g., Clean Kitchen"
                className="rounded-xl"
                required
                data-testid="template-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="category">Default Category (Optional)</Label>
              <Select 
                value={newTemplate.default_category} 
                onValueChange={(v) => setNewTemplate({...newTemplate, default_category: v})}
              >
                <SelectTrigger className="rounded-xl" data-testid="template-category">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORY_OPTIONS.map(cat => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="priority">Default Priority (Optional)</Label>
              <Select 
                value={newTemplate.default_priority} 
                onValueChange={(v) => setNewTemplate({...newTemplate, default_priority: v})}
              >
                <SelectTrigger className="rounded-xl" data-testid="template-priority">
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITY_OPTIONS.map(pri => (
                    <SelectItem key={pri} value={pri}>{pri}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              type="submit"
              disabled={creating}
              className="w-full bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full"
              data-testid="submit-template"
            >
              {creating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Add Template
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
