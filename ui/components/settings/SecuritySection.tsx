"use client"

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Save, Eye, EyeOff } from "lucide-react";

interface SecuritySectionProps {
  password: string; setPassword: (v: string) => void;
  confirmPassword: string; setConfirmPassword: (v: string) => void;
  showPassword: boolean; setShowPassword: (v: boolean) => void;
  showConfirmPassword: boolean; setShowConfirmPassword: (v: boolean) => void;
  updatingPassword: boolean; passwordMessage: string;
  onUpdatePassword: (e: React.FormEvent) => void;
  provider: string;
}

export function SecuritySection({ password, setPassword, confirmPassword, setConfirmPassword, showPassword, setShowPassword, showConfirmPassword, setShowConfirmPassword, updatingPassword, passwordMessage, onUpdatePassword, provider }: SecuritySectionProps) {
  const isEmail = provider === 'email';
  return (
    <div className="space-y-4 relative">
      <h3 className="text-sm font-medium border-b pb-2">Security</h3>
      {!isEmail && <div className="absolute inset-0 z-10 bg-background/40 flex items-center justify-center"><span className="text-xs bg-background p-1 border rounded">Managed via {provider}</span></div>}
      <form onSubmit={onUpdatePassword} className={`space-y-3 ${!isEmail ? 'opacity-40 pointer-events-none' : ''}`}>
        <div className="space-y-2">
          <Label htmlFor="new-pw">New Password</Label>
          <div className="relative"><Input id="new-pw" type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} /><button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2">{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div>
        </div>
        <div className="flex gap-2 items-end">
          <div className="space-y-2 flex-1"><Label htmlFor="confirm-pw">Confirm Password</Label><div className="relative"><Input id="confirm-pw" type={showConfirmPassword ? "text" : "password"} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} /><button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-3 top-1/2 -translate-y-1/2">{showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div></div>
          <Button type="submit" size="icon" disabled={updatingPassword}>{updatingPassword ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}</Button>
        </div>
        {passwordMessage && <p className={`text-sm ${passwordMessage.includes("success") ? "text-green-500" : "text-destructive"}`}>{passwordMessage}</p>}
      </form>
    </div>
  );
}
