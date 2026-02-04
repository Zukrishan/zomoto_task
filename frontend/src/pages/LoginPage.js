import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import api from '../lib/api';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email'),
  password: z.string().min(1, 'Password is required'),
});

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  // Seed data on first load
  useEffect(() => {
    const seedData = async () => {
      try {
        await api.post('/seed');
      } catch (error) {
        // Ignore if already seeded
      }
    };
    seedData();
  }, []);

  const onSubmit = async (data) => {
    setIsLoading(true);
    try {
      const user = await login(data.email, data.password);
      toast.success(`Welcome back, ${user.name}!`);
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F4F5] flex flex-col" data-testid="login-page">
      {/* Header */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
        {/* Logo */}
        <div className="mb-8 animate-slide-up">
          <img 
            src="https://customer-assets.emergentagent.com/job_task-tracker-735/artifacts/kinqp8ij_Zomoto_Logo-1.png"
            alt="Zomoto Logo"
            className="h-24 w-auto"
            data-testid="logo"
          />
        </div>

        {/* Login Card */}
        <Card className="w-full max-w-sm bg-white rounded-2xl shadow-lg border-0 animate-slide-up" style={{ animationDelay: '0.1s' }}>
          <CardContent className="p-6">
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-zinc-900" data-testid="login-title">Welcome Back</h1>
              <p className="text-sm text-zinc-500 mt-1">Sign in to manage tasks</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-zinc-700 font-medium">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  className="h-12 rounded-xl bg-zinc-50/50 border-zinc-200 focus:ring-[#E23744] focus:border-[#E23744]"
                  data-testid="email-input"
                  {...register('email')}
                />
                {errors.email && (
                  <p className="text-sm text-red-500" data-testid="email-error">{errors.email.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-zinc-700 font-medium">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    className="h-12 rounded-xl bg-zinc-50/50 border-zinc-200 focus:ring-[#E23744] focus:border-[#E23744] pr-10"
                    data-testid="password-input"
                    {...register('password')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                    data-testid="toggle-password"
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-sm text-red-500" data-testid="password-error">{errors.password.message}</p>
                )}
              </div>

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-12 bg-[#E23744] hover:bg-[#C42B37] text-white rounded-full font-medium shadow-md active:scale-95 transition-transform"
                data-testid="login-button"
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>

            {/* Demo Credentials */}
            <div className="mt-6 p-4 bg-zinc-50 rounded-xl" data-testid="demo-credentials">
              <p className="text-xs font-medium text-zinc-500 mb-2">Demo Accounts:</p>
              <div className="space-y-1 text-xs text-zinc-600">
                <p><span className="font-medium">Owner:</span> owner@zomoto.lk / 123456</p>
                <p><span className="font-medium">Manager:</span> manager@zomoto.lk / 123456</p>
                <p><span className="font-medium">Staff:</span> staff@zomoto.lk / 123456</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="mt-8 text-sm text-zinc-400">
          Zomoto Tasks • Restaurant Management
        </p>
      </div>
    </div>
  );
}
