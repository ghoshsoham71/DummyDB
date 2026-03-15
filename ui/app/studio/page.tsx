"use client"

import { useState } from "react";
import { useSchemaStore } from "@/stores/schema-store";
import { useJobStore } from "@/stores/job-store";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useJobStream } from "@/hooks/use-job-stream";
import { ImportSchemaDialog } from "@/components/generate/ImportSchemaDialog";
import { generateSyntheticData } from "@/lib/api";
import {
  Database, Plus, Search, Settings, FolderSymlink,
  Layers, Activity, Share2
} from "lucide-react";

export default function StudioPage() {
  const [activeTab, setActiveTab] = useState("seeders");
  const { currentSchema } = useSchemaStore();
  const [dataCount, setDataCount] = useState<number>(100);
  const [loading, setLoading] = useState(false);
  const { activeJobs, addJob } = useJobStore();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  // Stream updates the activeJobs store globally
  useJobStream(activeJobId || undefined);

  // Derived state from store for the active job
  const currentJob = activeJobId ? activeJobs[activeJobId] : null;
  const jobProgress = currentJob?.progress ? currentJob.progress * 100 : null;
  const jobMessage = currentJob?.status === "running" ? "Generating..." : currentJob?.status || null;

  const tabs = [
    { id: "seeders", label: "Seeders", icon: <Database className="w-5 h-5" /> },
    { id: "schemas", label: "Schemas", icon: <FolderSymlink className="w-5 h-5" /> },
    { id: "relates", label: "Relates", icon: <Share2 className="w-5 h-5" /> },
    { id: "connect", label: "Connect", icon: <Settings className="w-5 h-5" /> },
  ];

  const handleGenerateData = async () => {
    if (!currentSchema) return;
    try {
      setLoading(true);

      const targetSchemaId = currentSchema.id || "current-schema";
      
      const { success, generation_id } = await generateSyntheticData({
        schema_id: targetSchemaId,
        num_rows: { "*": dataCount },
        synthesizer_type: "ctgan",
      });

      if (success) {
        addJob({
            id: generation_id,
            schema_id: targetSchemaId,
            job_type: "synthetic_generation",
            status: "pending",
            progress: 0,
            parameters: {},
            created_at: new Date().toISOString()
        });
        setActiveJobId(generation_id);
      }
    } catch (e) {
      console.error("Generation error:", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="font-sans min-h-screen flex flex-col bg-background text-foreground pb-20 overflow-x-hidden">
        
        {/* Main Interface Wrapper */}
        <div className="flex-1 w-full max-w-[1600px] mx-auto flex flex-col px-4 sm:px-8 pt-8 sm:pt-12">
          
          {/* Top Header / Navigation Tabs */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 mb-8 sm:mb-12">
            <h1 className="text-2xl sm:text-3xl font-normal tracking-tight text-foreground flex items-center gap-3 animate-in-fade">
              <span className="w-8 h-8 rounded-md bg-primary flex p-1.5 shrink-0 shadow-lg dark:shadow-[0_0_15px_rgba(108,43,238,0.4)]">
                <Layers className="w-full h-full text-primary-foreground" />
              </span>
              Studio <span className="font-semibold text-primary">AI</span>
            </h1>
            
            <div className="flex flex-wrap items-center gap-4">
              <button 
                onClick={() => setImportDialogOpen(true)}
                className="inline-flex items-center justify-center bg-card border border-border hover:bg-muted text-foreground/80 px-6 py-2.5 rounded-sm text-xs tracking-[0.1em] font-medium uppercase transition-all"
              >
                Import Schema
              </button>
              <div className="relative hidden sm:block">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input 
                  type="text" 
                  placeholder="Search assets..." 
                  className="bg-card border border-border text-foreground text-xs font-normal rounded-sm pl-9 pr-4 py-2.5 w-64 focus:outline-none focus:ring-1 focus:ring-primary transition-premium" 
                />
              </div>
            </div>
          </div>

          <ImportSchemaDialog open={importDialogOpen} onOpenChange={setImportDialogOpen} />

          <div className="flex overflow-x-auto pb-4 sm:pb-8 scrollbar-hide gap-3 sm:gap-6 w-full -mx-4 px-4 sm:mx-0 sm:px-0 scroll-smooth animate-in-slide" style={{ animationDelay: '100ms' }}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex flex-col items-center justify-center gap-2 
                  w-24 sm:w-32 py-4 sm:py-6 rounded-xl border transition-premium shrink-0
                  ${activeTab === tab.id 
                    ? "bg-primary border-transparent text-primary-foreground shadow-lg dark:shadow-[0_0_20px_rgba(108,43,238,0.3)]" 
                    : "bg-card border-border text-muted-foreground hover:bg-muted"}
                `}
              >
                {tab.icon}
                <span className="text-[11px] sm:text-xs tracking-wider uppercase font-semibold mt-1">{tab.label}</span>
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 min-h-[500px] sm:min-h-[600px] w-full">
            
            {/* Canvas Environment Area */}
            <div className="xl:col-span-8 flex flex-col w-full h-full">
               <div className="flex items-center justify-between mb-4 sm:mb-6 animate-in-fade" style={{ animationDelay: '200ms' }}>
                  <h2 className="text-sm font-semibold tracking-[0.2em] uppercase text-primary/80">Canvas Environment</h2>
                 <span className="text-[10px] font-medium tracking-widest uppercase border border-green-500/30 text-green-500 bg-green-500/10 px-3 py-1 rounded-sm">Live</span>
              </div>

               <div className="flex-1 w-full min-h-[400px] relative bg-card border border-border rounded-2xl overflow-hidden shadow-sm isolated group outline-none focus:outline-none cursor-crosshair animate-in-slide" style={{ animationDelay: '300ms' }}>
                  
                  {/* Dot background pattern */}
                  <div className="absolute inset-0 opacity-10 dark:opacity-20" style={{ backgroundImage: 'radial-gradient(circle at center, currentColor 1px, transparent 1px)', backgroundSize: '32px 32px' }} />
                  
                  {/* Visual Connection Nodes Component */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center p-4">
                     
                     <div className="flex flex-col sm:flex-row items-center justify-center gap-12 sm:gap-32 relative z-10 w-full mb-16 sm:mb-24">
                        
                        {/* Source Node */}
                        <div className="w-48 sm:w-56 bg-background border border-primary/20 rounded-xl p-4 sm:p-5 shadow-sm backdrop-blur-md">
                           <div className="flex items-center gap-3 mb-4">
                             <FolderSymlink className="w-4 h-4 text-primary" />
                             <span className="text-[10px] sm:text-xs font-semibold tracking-[0.1em] uppercase text-foreground">Source_DB</span>
                           </div>
                           <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                              <div className="h-full bg-primary w-[60%]" />
                           </div>
                        </div>

                        {/* AI Engine Node */}
                        <div className="w-48 sm:w-56 bg-background border border-border rounded-xl p-4 sm:p-5 shadow-sm backdrop-blur-md">
                           <div className="flex items-center gap-3 mb-4">
                             <Activity className="w-4 h-4 text-primary" />
                             <span className="text-[10px] sm:text-xs font-semibold tracking-[0.1em] uppercase text-foreground">AI_Engine_V2</span>
                           </div>
                           <div className="flex gap-1.5">
                              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse delay-75" />
                              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse delay-150" />
                           </div>
                        </div>

                     </div>

                     {/* Connection Line (CSS Visual Trick) hidden on narrow mobile */}
                     <div className="hidden sm:block absolute top-[40%] left-[25%] right-[25%] h-px bg-gradient-to-r from-transparent via-primary to-transparent opacity-60 pointer-events-none">
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-primary rounded-full shadow-[0_0_20px_4px_rgba(108,43,238,0.8)] dark:bg-white" />
                     </div>

                     {/* Target Sink Node */}
                     <div className="w-56 sm:w-64 bg-background border border-green-500/30 rounded-xl p-4 sm:p-5 shadow-sm backdrop-blur-md relative z-10">
                           <div className="flex items-center justify-between mb-4">
                             <div className="flex items-center gap-3">
                               <Database className="w-4 h-4 text-green-500" />
                               <span className="text-[10px] sm:text-xs font-semibold tracking-[0.1em] uppercase text-foreground">Target_Sink</span>
                             </div>
                             <span className="text-[8px] sm:text-[9px] font-medium tracking-widest text-green-500 uppercase">Active</span>
                           </div>
                           <div className="grid grid-cols-4 gap-2 h-1.5">
                              <div className="bg-green-500/30 rounded-full" />
                              <div className="bg-green-500/30 rounded-full" />
                              <div className="bg-green-500 rounded-full shadow-[0_0_10px_rgba(34,197,94,0.8)]" />
                              <div className="bg-green-500/10 rounded-full" />
                           </div>
                     </div>

                  </div>

              </div>
            </div>

            {/* Right Column - Generation Configuration & Jobs */}
            <div className="xl:col-span-4 flex flex-col space-y-6 w-full h-full mt-8 xl:mt-0">
               <div className="flex items-center justify-between mb-4 sm:mb-6">
                 <h2 className="text-sm font-semibold tracking-[0.2em] uppercase text-primary/80">Control Panel</h2>
               </div>
               
               <div className="bg-card border border-border rounded-2xl p-6 relative overflow-hidden shadow-sm">
                  <h3 className="text-[10px] font-medium tracking-[0.1em] uppercase text-muted-foreground mb-6 border-b border-border pb-4 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                    Generation Parameters
                  </h3>
                  
                  <div className="space-y-6 relative z-10">
                     <div className="space-y-3">
                        <label className="text-[10px] font-medium tracking-widest uppercase text-muted-foreground block">Scale (Rows)</label>
                        <input 
                            type="number" 
                            value={dataCount} 
                            onChange={(e) => setDataCount(Number(e.target.value))}
                            className="w-full bg-background border border-border rounded-sm px-4 py-2.5 text-sm text-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/50 font-normal transition-premium"
                        />
                     </div>

                     <div className="pt-4">
                        <Button 
                          onClick={handleGenerateData}
                          disabled={!currentSchema || loading}
                          className={`w-full h-12 rounded-sm text-sm font-medium tracking-wide shadow-lg transition-all uppercase ${
                             loading ? 'bg-primary/50 cursor-not-allowed text-primary-foreground/70' : 'bg-primary hover:bg-primary/90 text-primary-foreground dark:hover:bg-[#7a34e0] hover:shadow-[0_0_20px_rgba(139,60,255,0.4)]'
                          }`}
                       >
                          {loading ? "Initializing..." : "Seed Synthetic Data"}
                       </Button>
                     </div>
                  </div>
               </div>

               {/* Active Generation Jobs Section Mini */}
               <div className="flex-1 min-h-[250px] bg-card border border-border rounded-2xl p-6 shadow-sm">
                 <div className="flex justify-between items-center mb-6">
                    <h3 className="text-[10px] font-medium tracking-[0.1em] uppercase text-muted-foreground">Active Jobs</h3>
                    <Button variant="link" className="text-[10px] h-auto p-0 font-medium tracking-widest uppercase text-primary hover:text-primary/80 transition-colors">View All</Button>
                 </div>
                 
                 {(jobProgress !== null || jobMessage) ? (
                    <div className="space-y-4">
                      {/* Live Job Card */}
                      <div className="bg-background border border-border rounded-xl p-4">
                         <div className="flex justify-between items-start mb-4">
                            <div>
                              <h4 className="text-xs font-medium tracking-wide text-foreground">Active Simulation</h4>
                              <p className="text-[9px] font-light tracking-widest text-muted-foreground mt-1 uppercase">Job ID: #SE-LIVE</p>
                            </div>
                            <span className="text-sm font-light text-primary">{Math.round(jobProgress || 0)}%</span>
                         </div>
                         
                         <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden mb-3 border border-border">
                            <div className="h-full bg-primary rounded-full shadow-[0_0_10px_rgba(108,43,238,0.5)] transition-all" style={{ width: `${jobProgress || 0}%` }} />
                         </div>

                         <div className="text-[9px] font-light text-muted-foreground tracking-wide truncate">
                            {jobMessage || "Synthesizing data models..."}
                         </div>
                      </div>
                    </div>
                 ) : (
                    <div className="flex flex-col items-center justify-center h-[150px] opacity-40">
                      <Plus className="w-6 h-6 text-muted-foreground mb-3" />
                      <p className="text-[10px] uppercase tracking-[0.2em] font-light text-muted-foreground">No active generation job</p>
                    </div>
                 )}
               </div>

            </div>
          </div>

        </div>

      </div>
    </ProtectedRoute>
  );
}
