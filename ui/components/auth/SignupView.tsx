"use client"

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Eye, EyeOff, Check, X } from "lucide-react";

interface SignupViewProps {
  email: string; setEmail: (v: string) => void;
  username: string; setUsername: (v: string) => void;
  usernameAvailable: boolean | null; checkingUsername: boolean;
  password: string; setPassword: (v: string) => void;
  showPassword: boolean; setShowPassword: (v: boolean) => void;
  loading: boolean;
  onSubmit: (e: React.FormEvent) => void;
  captchaToken: string | null;
}

export function SignupView({ email, setEmail, username, setUsername, usernameAvailable, checkingUsername, password, setPassword, showPassword, setShowPassword, loading, onSubmit, captchaToken }: SignupViewProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="username">Username</Label>
        <div className="relative">
          <Input id="username" value={username} onChange={(e) => setUsername(e.target.value)} disabled={loading} required />
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            {checkingUsername ? <Loader2 className="h-4 w-4 animate-spin" /> : usernameAvailable === true ? <Check className="h-4 w-4 text-green-500" /> : usernameAvailable === false ? <X className="h-4 w-4 text-destructive" /> : null}
          </div>
        </div>
      </div>
      <div className="space-y-2"><Label htmlFor="email">Email</Label><Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={loading} required /></div>
      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <div className="relative">
          <Input id="password" type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} disabled={loading} required />
          <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>
        </div>
      </div>
      <Button type="submit" className="w-full" disabled={loading || !captchaToken}>{loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Sign Up</Button>
    </form>
  );
}
