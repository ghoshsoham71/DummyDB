"use client"

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Save, Check, X } from "lucide-react";

interface ProfileSectionProps {
  username: string; setUsername: (v: string) => void;
  usernameAvailable: boolean | null; checkingUsername: boolean;
  updatingUsername: boolean; usernameMessage: string;
  onUpdateUsername: (e: React.FormEvent) => void;
  currentUsername: string;
}

export function ProfileSection({ username, setUsername, usernameAvailable, checkingUsername, updatingUsername, usernameMessage, onUpdateUsername, currentUsername }: ProfileSectionProps) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold tracking-[0.1em] uppercase text-muted-foreground">Profile Overview</h3>
        <p className="text-[10px] font-light text-muted-foreground/60 uppercase tracking-widest">Identify your architectural presence.</p>
      </div>
      
      <form onSubmit={onUpdateUsername} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="settings-username" className="text-[10px] uppercase tracking-wider font-medium text-muted-foreground">Identity Handle</Label>
          <div className="relative">
            <Input 
               id="settings-username" 
               value={username} 
               onChange={(e) => setUsername(e.target.value)} 
               className={`h-10 bg-background border-border text-xs font-light rounded-sm focus-visible:ring-1 focus-visible:ring-primary ${usernameAvailable === false && username !== currentUsername ? "border-destructive/50" : ""}`} 
            />
            {username !== "" && username !== currentUsername && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                {checkingUsername ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : usernameAvailable === true ? <Check className="h-4 w-4 text-green-500" /> : usernameAvailable === false ? <X className="h-4 w-4 text-destructive" /> : null}
              </div>
            )}
          </div>
        </div>
        
        <Button type="submit" size="sm" disabled={updatingUsername} className="w-full bg-primary hover:bg-primary/90 text-primary-foreground h-9 rounded-sm uppercase tracking-widest text-[10px] font-medium transition-all">
          {updatingUsername ? <Loader2 className="h-3 w-3 animate-spin mr-2" /> : <Save className="h-3 w-3 mr-2" />}
          Commit Changes
        </Button>
        
        {usernameMessage && (
          <p className={`text-[10px] font-medium tracking-wide uppercase ${usernameMessage.includes("success") ? "text-green-500" : "text-destructive"}`}>
            {usernameMessage}
          </p>
        )}
      </form>
    </div>
  );
}
