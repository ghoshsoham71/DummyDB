"use client"

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, AlertTriangle } from "lucide-react";

interface DangerZoneProps {
  deleteConfirm: string; setDeleteConfirm: (v: string) => void;
  deleting: boolean; onDeleteAccount: () => void;
}

export function DangerZone({ deleteConfirm, setDeleteConfirm, deleting, onDeleteAccount }: DangerZoneProps) {
  return (
    <div className="space-y-4 pt-2">
      <h3 className="text-sm font-medium text-destructive border-b border-destructive/20 pb-2 flex items-center gap-2"><AlertTriangle className="h-4 w-4" />Danger Zone</h3>
      <div className="bg-destructive/10 p-4 rounded-lg border border-destructive/20 space-y-3">
        <p className="text-xs">Once deleted, there's no going back.</p>
        <div className="space-y-2"><Label className="text-xs text-destructive font-semibold">Type "DELETE" to confirm</Label><Input value={deleteConfirm} onChange={(e) => setDeleteConfirm(e.target.value)} placeholder="DELETE" /></div>
        <Button variant="destructive" onClick={onDeleteAccount} disabled={deleteConfirm !== "DELETE" || deleting} className="w-full">{deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Permanently Delete Account</Button>
      </div>
    </div>
  );
}
