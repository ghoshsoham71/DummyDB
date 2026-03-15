"use client"

import { CheckCircle, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useRef, useEffect } from "react";

interface ProgressStageProps {
  jobStatus: { status: string, progress: number, message: string } | null;
  streamLog: string[];
  downloadLink: string | null;
}

export function ProgressStage({ jobStatus, streamLog, downloadLink }: ProgressStageProps) {
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [streamLog]);

  return (
    <div className="space-y-6">
      <div className="bg-card p-6 rounded-lg border">
        <h2 className="text-xl font-semibold mb-4">Step 3: Generating Data</h2>
        {jobStatus && (
          <div className="space-y-4">
            <div className="flex justify-between items-center text-sm">
              <span className="font-medium text-primary uppercase">{jobStatus.status}</span>
              <span>{Math.round(jobStatus.progress)}%</span>
            </div>
            <Progress value={jobStatus.progress} className="h-2" />
            <p className="text-sm text-muted-foreground">{jobStatus.message}</p>
          </div>
        )}
        <div className="mt-6 bg-black/40 rounded-xl border border-white/5 p-4 font-mono text-xs overflow-y-auto max-h-[300px]">
          {streamLog.map((log, i) => <div key={i} className="py-1 border-b border-white/5 last:border-0">{log}</div>)}
          <div ref={logEndRef} />
        </div>
      </div>

      {downloadLink && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 p-6 rounded-2xl flex flex-col items-center text-center gap-4">
          <div className="h-16 w-16 bg-emerald-500/20 rounded-full flex items-center justify-center"><CheckCircle className="h-8 w-8 text-emerald-400" /></div>
          <div><h3 className="text-xl font-bold text-emerald-400">Generation Complete!</h3><p className="text-muted-foreground">Your synthetic data is ready for download.</p></div>
          <Button asChild className="bg-emerald-500 hover:bg-emerald-600 text-white gap-2 px-8 py-6 text-lg rounded-xl shadow-lg transition-transform hover:scale-105">
            <a href={downloadLink} download><Download className="h-5 w-5" />Download Bundle (.zip)</a>
          </Button>
        </div>
      )}
    </div>
  );
}
