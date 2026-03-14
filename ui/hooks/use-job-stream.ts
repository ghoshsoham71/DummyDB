// ui/hooks/use-job-stream.ts

import { useEffect } from 'react';
import { useJobStore } from '@/stores/job-store';

export function useJobStream(jobId?: string) {
  const updateJob = useJobStore((state) => state.updateJob);

  useEffect(() => {
    if (!jobId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_WS_BASE_URL || 'localhost:8000';
    const ws = new WebSocket(`${protocol}//${host}/api/v1/jobs/${jobId}/stream`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      updateJob(jobId, {
        status: data.status,
        progress: data.progress,
        error_message: data.error_message
      });
    };

    return () => ws.close();
  }, [jobId, updateJob]);
}
