// ui/stores/job-store.ts

import { create } from 'zustand';

export interface Job {
  id: string;
  schema_id: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  parameters: any;
  error_message?: string;
  created_at: string;
}

interface JobState {
  activeJobs: Record<string, Job>;
  jobHistory: Job[];
  addJob: (job: Job) => void;
  updateJob: (id: string, updates: Partial<Job>) => void;
  setJobHistory: (jobs: Job[]) => void;
}

export const useJobStore = create<JobState>((set) => ({
  activeJobs: {},
  jobHistory: [],
  addJob: (job) => set((state) => ({ 
    activeJobs: { ...state.activeJobs, [job.id]: job } 
  })),
  updateJob: (id, updates) => set((state) => {
    const job = state.activeJobs[id];
    if (!job) return state;
    return {
      activeJobs: { ...state.activeJobs, [id]: { ...job, ...updates } }
    };
  }),
  setJobHistory: (jobs) => set({ jobHistory: jobs }),
}));
