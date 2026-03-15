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
    <div className="space-y-6 relative">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold tracking-[0.1em] uppercase text-muted-foreground">Security Layer</h3>
        <p className="text-[10px] font-light text-muted-foreground/60 uppercase tracking-widest">Enforce cryptographic integrity.</p>
      </div>

      {!isEmail && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pt-8">
           <div className="bg-muted/80 backdrop-blur-sm border border-border px-4 py-2 rounded-sm shadow-xl">
             <span className="text-[10px] font-medium tracking-widest uppercase text-foreground/70">Managed via {provider}</span>
           </div>
        </div>
      )}

      <form onSubmit={onUpdatePassword} className={`space-y-4 ${!isEmail ? 'opacity-20 pointer-events-none grayscale' : ''}`}>
        <div className="space-y-2">
          <Label htmlFor="new-pw" className="text-[10px] uppercase tracking-wider font-medium text-muted-foreground">New Cipher</Label>
          <div className="relative">
            <Input 
              id="new-pw" 
              type={showPassword ? "text" : "password"} 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              className="h-10 bg-background border-border text-xs font-light rounded-sm focus-visible:ring-1 focus-visible:ring-primary pl-4 pr-10"
            />
            <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors">
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirm-pw" className="text-[10px] uppercase tracking-wider font-medium text-muted-foreground">Confirm Cipher</Label>
          <div className="relative">
            <Input 
              id="confirm-pw" 
              type={showConfirmPassword ? "text" : "password"} 
              value={confirmPassword} 
              onChange={(e) => setConfirmPassword(e.target.value)} 
              className="h-10 bg-background border-border text-xs font-light rounded-sm focus-visible:ring-1 focus-visible:ring-primary pl-4 pr-10"
            />
            <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors">
              {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <Button type="submit" size="sm" disabled={updatingPassword} className="w-full bg-primary hover:bg-primary/90 text-primary-foreground h-9 rounded-sm uppercase tracking-widest text-[10px] font-medium transition-all">
          {updatingPassword ? <Loader2 className="h-3 w-3 animate-spin mr-2" /> : <Save className="h-3 w-3 mr-2" />}
          Rotate Keys
        </Button>

        {passwordMessage && (
          <p className={`text-[10px] font-medium tracking-wide uppercase ${passwordMessage.includes("success") ? "text-green-500" : "text-destructive"}`}>
            {passwordMessage}
          </p>
        )}
      </form>
    </div>
  );
}
