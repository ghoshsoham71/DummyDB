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
    <div className="space-y-6 pt-4 border-t border-border/50">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold tracking-[0.1em] uppercase text-destructive flex items-center gap-2">
          <AlertTriangle className="h-3.5 w-3.5" /> Termination Sequence
        </h3>
        <p className="text-[10px] font-light text-muted-foreground/60 uppercase tracking-widest">Permanent erasure of all local data nodes.</p>
      </div>

      <div className="bg-destructive/5 border border-destructive/20 rounded-md p-6 space-y-6">
        <p className="text-[11px] leading-relaxed text-foreground/70 font-light">
          Account termination is irreversible. All synthetic archives, relational mappings, and cryptographic identities will be permanently purged.
        </p>
        
        <div className="space-y-3">
          <Label className="text-[9px] text-destructive/80 font-bold uppercase tracking-[0.2em]">Verification String: &quot;DELETE&quot;</Label>
          <Input 
            value={deleteConfirm} 
            onChange={(e) => setDeleteConfirm(e.target.value)} 
            placeholder="TYPE TO CONFIRM" 
            className="h-10 bg-background border-destructive/20 text-foreground font-mono text-xs rounded-sm focus-visible:ring-1 focus-visible:ring-destructive placeholder:text-muted-foreground/30"
          />
        </div>
        
        <Button 
          variant="destructive" 
          onClick={onDeleteAccount} 
          disabled={deleteConfirm !== "DELETE" || deleting} 
          className="w-full h-10 rounded-sm uppercase tracking-widest text-[10px] font-semibold shadow-lg shadow-destructive/10"
        >
          {deleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Initiate account shredding"}
        </Button>
      </div>
    </div>
  );
}
