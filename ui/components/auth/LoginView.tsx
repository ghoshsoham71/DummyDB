"use client"

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Eye, EyeOff } from "lucide-react";

interface LoginViewProps {
  email: string; setEmail: (v: string) => void;
  password: string; setPassword: (v: string) => void;
  showPassword: boolean; setShowPassword: (v: boolean) => void;
  loading: boolean;
  onForgotPassword: () => void;
  onSubmit: (e: React.FormEvent) => void;
  captchaToken: string | null;
}

export function LoginView({ email, setEmail, password, setPassword, showPassword, setShowPassword, loading, onForgotPassword, onSubmit, captchaToken }: LoginViewProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-2"><Label htmlFor="email">Email</Label><Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={loading} required /></div>
      <div className="space-y-2">
        <div className="flex justify-between"><Label htmlFor="password">Password</Label><button type="button" onClick={onForgotPassword} className="text-sm text-primary hover:underline">Forgot?</button></div>
        <div className="relative">
          <Input id="password" type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} disabled={loading} required />
          <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>
        </div>
      </div>
      <Button type="submit" className="w-full" disabled={loading || !captchaToken}>{loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Sign In</Button>
    </form>
  );
}
