"use client"

import { useState, useEffect } from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

interface JobProgress {
  progress: number;
  message: string;
  status: "pending" | "running" | "completed" | "failed";
}

export function JobProcessMonitor({ jobId }: { jobId: string }) {
  const [data, setData] = useState<JobProgress>({
    progress: 0,
    message: "Initializing job...",
    status: "pending"
  });

  useEffect(() => {
    if (!jobId) return;

    // Simulate WebSocket / Polling for now
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/jobs/${jobId}`);
        const json = await res.json();
        setData({
          progress: json.progress || 0,
          message: json.message || "Processing...",
          status: json.status
        });
        
        if (json.status === "completed" || json.status === "failed") {
          clearInterval(interval);
        }
      } catch (e) {
        console.error("Failed to fetch job", e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId]);

  return (
    <div className="bg-card p-4 rounded-xl border shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium flex items-center gap-2">
          {data.status === "running" && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
          {data.status === "completed" && <CheckCircle2 className="w-4 h-4 text-green-500" />}
          {data.status === "failed" && <XCircle className="w-4 h-4 text-destructive" />}
          Generation Job: {jobId.slice(0, 8)}...
        </h3>
        <Badge variant={data.status === "completed" ? "success" : "secondary"}>
          {data.status.toUpperCase()}
        </Badge>
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{data.message}</span>
          <span>{Math.round(data.progress)}%</span>
        </div>
        <Progress value={data.progress} className="h-2" />
      </div>
    </div>
  );
}
