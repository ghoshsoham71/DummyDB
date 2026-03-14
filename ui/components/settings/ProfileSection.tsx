"use client"

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Save, Check, X } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface ProfileSectionProps {
  username: string; setUsername: (v: string) => void;
  usernameAvailable: boolean | null; checkingUsername: boolean;
  updatingUsername: boolean; usernameMessage: string;
  onUpdateUsername: (e: React.FormEvent) => void;
  currentUsername: string;
}

export function ProfileSection({ username, setUsername, usernameAvailable, checkingUsername, updatingUsername, usernameMessage, onUpdateUsername, currentUsername }: ProfileSectionProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium border-b pb-2">Profile Information</h3>
      <form onSubmit={onUpdateUsername} className="space-y-3">
        <div className="flex gap-2 items-end">
          <div className="space-y-2 flex-1">
            <Label htmlFor="settings-username">Username</Label>
            <div className="relative">
              <Input id="settings-username" value={username} onChange={(e) => setUsername(e.target.value)} className={usernameAvailable === false && username !== currentUsername ? "border-destructive" : ""} />
              {username !== "" && username !== currentUsername && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  {checkingUsername ? <Loader2 className="h-4 w-4 animate-spin" /> : usernameAvailable === true ? <Check className="h-4 w-4 text-green-500" /> : usernameAvailable === false ? <X className="h-4 w-4 text-destructive" /> : null}
                </div>
              )}
            </div>
          </div>
          <Button type="submit" size="icon" disabled={updatingUsername}>{updatingUsername ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}</Button>
        </div>
        {usernameMessage && <p className={`text-sm ${usernameMessage.includes("success") ? "text-green-500" : "text-destructive"}`}>{usernameMessage}</p>}
      </form>
    </div>
  );
}
