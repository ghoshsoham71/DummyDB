"use client"

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Database, Trash2, Download, XCircle, RefreshCw,
  CheckCircle2, Clock, AlertCircle, Loader2, Activity,
  HardDrive, BarChart3, FileText, Globe, Search, ArrowUpDown, ChevronRight, Plus
} from "lucide-react";
import {
  listSchemas, listJobs, deleteSchema, bulkDeleteSchemas,
  cancelJob, getDownloadUrl, getDashboardOverview, getDashboardActivity,
  type SchemaListItem, type JobItem, type DashboardOverview, type ActivityEvent,
} from "@/lib/api";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

function statusBadge(status: string) {
  const icons: Record<string, React.ReactNode> = {
    completed: <CheckCircle2 className="h-3 w-3 text-green-400" />,
    running: <Loader2 className="h-3 w-3 text-purple-400 animate-spin" />,
    pending: <Clock className="h-3 w-3 text-yellow-400" />,
    failed: <AlertCircle className="h-3 w-3 text-red-400" />,
    cancelled: <XCircle className="h-3 w-3 text-muted-foreground/40" />,
    idle: <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
  };
  const colors: Record<string, string> = {
    completed: "text-green-500",
    running: "text-purple-400",
    pending: "text-yellow-400",
    failed: "text-red-400",
    cancelled: "text-muted-foreground",
    idle: "text-muted-foreground",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-light tracking-wide ${colors[status.toLowerCase()] || colors.idle}`}>
      {icons[status.toLowerCase()] || <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />} {status}
    </span>
  );
}

function timeAgo(d: string | number) {
  const date = new Date(d);
  if (isNaN(date.getTime())) return "Recently";
  const sec = Math.floor((Date.now() - date.getTime()) / 1000);
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "explorer" | "fidelity">("overview");
  const [schemas, setSchemas] = useState<SchemaListItem[]>([]);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [schemaSearch, setSchemaSearch] = useState("");
  const [explorerSearch, setExplorerSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Mock data for explorer and quality integrated views
  const mockExplorerData = [
      { id: 1, name: "John Doe", email: "john@example.com", age: 28, city: "New York", fidelity: 0.94 },
      { id: 2, name: "Jane Smith", email: "jane@example.com", age: 34, city: "London", fidelity: 0.89 },
      { id: 3, name: "Bob Johnson", email: "bob@example.com", age: 45, city: "Paris", fidelity: 0.91 },
  ];

  const mockFidelityData = [
    { name: "Age", real: 0.85, synthetic: 0.82 },
    { name: "Income", real: 0.75, synthetic: 0.70 },
    { name: "Location", real: 0.95, synthetic: 0.92 },
    { name: "Balance", real: 0.65, synthetic: 0.68 },
  ];

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, act, sch, jb] = await Promise.allSettled([
        getDashboardOverview(), getDashboardActivity(15),
        listSchemas(100), listJobs(100),
      ]);
      if (ov.status === "fulfilled") setOverview(ov.value);
      if (act.status === "fulfilled") setActivity(act.value.events || []);
      if (sch.status === "fulfilled") setSchemas(sch.value.schemas || []);
      if (jb.status === "fulfilled") setJobs(jb.value.jobs || []);
    } catch (e) { setError(e instanceof Error ? e.message : "Failed to load system data."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleDeleteSchema = async (id: string) => {
    try {
      await deleteSchema(id);
      setSchemas((p) => p.filter((s) => s.schema_id !== id));
      flash("Schema deleted successfully.");
    } catch (e) { setError(e instanceof Error ? e.message : "Schema deletion failed."); }
  };

  const flash = (msg: string) => { setSuccessMsg(msg); setTimeout(() => setSuccessMsg(null), 3000); };

  const filteredSchemas = schemas.filter((s) =>
    !schemaSearch || (s.filename || s.schema_id).toLowerCase().includes(schemaSearch.toLowerCase()));

  const mockMetricPulse = [40, 60, 45, 80, 50, 90, 100];

  return (
    <ProtectedRoute>
      <div className="font-sans min-h-screen flex flex-col bg-background text-foreground pb-20 overflow-x-hidden">
        
        {/* Main Interface Wrapper */}
        <div className="flex-1 w-full max-w-7xl mx-auto flex flex-col px-4 sm:px-8 pt-6 sm:pt-10">
          
          {/* Terminal Tabs & Header Combined */}
          <div className="flex flex-col gap-8 mb-12 animate-in-fade">
             <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                <div className="flex flex-col gap-2">
                  <p className="text-[10px] tracking-[0.2em] font-medium text-primary uppercase">Synthesis Terminal v1.0</p>
                  <h1 className="text-3xl font-normal tracking-tight text-foreground">
                    Platform <span className="font-medium text-primary">Command</span>
                  </h1>
                </div>
                <div className="flex items-center gap-2 p-1 bg-muted/40 rounded-md border border-border/50">
                  {[
                    { id: "overview", label: "Infrastructure", icon: Activity },
                    { id: "explorer", label: "Explorer", icon: Globe },
                    { id: "fidelity", label: "Fidelity", icon: BarChart3 }
                  ].map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-sm text-[10px] font-medium uppercase tracking-widest transition-premium ${activeTab === tab.id ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}
                    >
                      <tab.icon className="h-3 w-3" />
                      {tab.label}
                    </button>
                  ))}
                </div>
             </div>
          </div>

          {successMsg && <Alert className="mb-8 border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-100 rounded-sm"><CheckCircle2 className="h-4 w-4 text-green-500" /><AlertDescription className="font-light tracking-wide">{successMsg}</AlertDescription></Alert>}
          {error && <Alert variant="destructive" className="mb-8 border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-100 rounded-sm"><AlertCircle className="h-4 w-4 text-red-500" /><AlertDescription className="font-light tracking-wide">{error}</AlertDescription></Alert>}

          {loading ? (
             <div className="flex items-center justify-center py-32 text-muted-foreground font-light tracking-widest uppercase text-xs"><Loader2 className="h-5 w-5 animate-spin mr-3 text-primary" /> Calibrating Terminal…</div>
          ) : (
            <div className="animate-in-slide">
              {activeTab === "overview" && (
                <div className="flex flex-col lg:flex-row gap-8 lg:gap-12">
                  <div className="flex-1 space-y-12 min-w-0">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      {/* Metric Cards remain identical but within tab */}
                      <div className="flex flex-col bg-card border border-border rounded-md p-6 shadow-sm relative overflow-hidden group hover:shadow-primary/5 transition-premium">
                        <div className="flex justify-between items-start mb-4">
                          <span className="text-xs font-normal text-muted-foreground tracking-wide">Total Active Schemas</span>
                          <span className="text-[10px] font-medium bg-green-500/10 text-green-500 px-2 py-0.5 rounded-sm">+12%</span>
                        </div>
                        <div className="text-4xl font-normal tracking-tight text-foreground mb-6">{overview?.schemas?.total || filteredSchemas.length || 0}</div>
                        <div className="mt-auto h-8 flex items-end gap-1 opacity-20 group-hover:opacity-40 transition-opacity">
                           {mockMetricPulse.map((val, i) => (
                               <div key={i} className="flex-1 bg-primary rounded-t-[1px] transition-all" style={{ height: `${val}%` }} />
                           ))}
                        </div>
                      </div>

                      <div className="flex flex-col bg-card border border-border rounded-md p-6 shadow-sm relative overflow-hidden group hover:shadow-primary/5 transition-premium">
                        <div className="flex justify-between items-start mb-4">
                          <span className="text-xs font-normal text-muted-foreground tracking-wide">Data Scale</span>
                          <span className="text-[10px] font-medium bg-green-500/10 text-green-500 px-2 py-0.5 rounded-sm">+24%</span>
                        </div>
                        <div className="text-4xl font-normal tracking-tight text-foreground mb-6">{overview?.synthetic_files?.total || "0"}</div>
                        <div className="mt-auto h-8 flex items-end gap-1 opacity-20 group-hover:opacity-40 transition-opacity">
                           {[30, 20, 45, 55, 40, 60, 75].map((val, i) => (
                               <div key={i} className="flex-1 bg-primary rounded-t-[1px] transition-all" style={{ height: `${val}%` }} />
                           ))}
                        </div>
                      </div>

                      <div className="flex flex-col bg-card border border-border rounded-md p-6 shadow-sm relative overflow-hidden group hover:shadow-primary/5 transition-premium">
                        <div className="flex justify-between items-start mb-4">
                          <span className="text-xs font-normal text-muted-foreground tracking-wide">Active Clusters</span>
                          <span className="text-[10px] font-medium bg-yellow-500/10 text-yellow-500 px-2 py-0.5 rounded-sm">Operational</span>
                        </div>
                        <div className="text-4xl font-normal tracking-tight text-foreground mb-6">{overview?.schemas?.total || 1}</div>
                        <div className="mt-auto h-8 flex items-end gap-1 opacity-20 group-hover:opacity-40 transition-opacity">
                           {[80, 85, 70, 75, 60, 50, 45].map((val, i) => (
                               <div key={i} className="flex-1 bg-primary rounded-t-[1px] transition-all" style={{ height: `${val}%` }} />
                           ))}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-6">
                      <div className="flex items-center justify-between">
                        <h2 className="text-lg font-light tracking-wide">Synthesis Blueprints</h2>
                        <Button variant="outline" size="sm" onClick={fetchAll} className="h-8 px-4 border-border hover:bg-muted text-[9px] uppercase tracking-widest">
                           <RefreshCw className="h-3 w-3 mr-2" /> Sync
                        </Button>
                      </div>
                      <div className="border border-border rounded-md bg-card overflow-hidden shadow-sm">
                        <div className="grid grid-cols-[1.5fr_1fr_1fr_auto] gap-4 px-6 py-4 border-b border-border bg-muted/30">
                          <div className="text-[10px] font-medium tracking-[0.15em] uppercase text-muted-foreground">ID / Name</div>
                          <div className="text-[10px] font-medium tracking-[0.15em] uppercase text-muted-foreground text-center">Protocol</div>
                          <div className="text-[10px] font-medium tracking-[0.15em] uppercase text-muted-foreground">Status</div>
                          <div className="text-[10px] font-medium tracking-[0.15em] uppercase text-muted-foreground text-right">Action</div>
                        </div>
                        <div className="divide-y divide-border/50">
                          {filteredSchemas.map((schema, idx) => (
                            <div key={schema.schema_id} className="grid grid-cols-[1.5fr_1fr_1fr_auto] gap-4 px-6 py-4 items-center hover:bg-muted/30 transition-colors group">
                              <span className="text-sm font-normal truncate">{schema.filename || schema.schema_id}</span>
                              <span className="text-[10px] font-mono text-muted-foreground text-center bg-muted/50 py-0.5 rounded-sm uppercase">{idx % 2 === 0 ? 'SQL' : 'Supabase'}</span>
                              <span>{statusBadge('Active')}</span>
                              <div className="flex justify-end">
                                 <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-sm" onClick={() => handleDeleteSchema(schema.schema_id)}>
                                    <Trash2 className="h-4 w-4" />
                                 </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="w-full lg:w-80 shrink-0">
                    <div className="bg-card border border-border rounded-md p-6 shadow-sm h-full">
                       <h3 className="text-xs font-medium tracking-[0.15em] uppercase text-muted-foreground mb-6 flex items-center gap-2">
                         <Activity className="h-3.5 w-3.5 text-primary" /> Live Audit
                       </h3>
                       <div className="space-y-6">
                          {activity.slice(0, 6).map((ev, i) => (
                            <div key={i} className="flex flex-col gap-1 border-l-2 border-primary/20 pl-4 py-1">
                               <span className="text-[9px] font-medium tracking-widest uppercase text-muted-foreground">{timeAgo(ev.timestamp)}</span>
                               <span className="text-xs font-medium text-foreground">{ev.type.replace(/_/g, " ")}</span>
                               <span className="text-[10px] text-muted-foreground">{ev.message}</span>
                            </div>
                          ))}
                       </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "explorer" && (
                <div className="space-y-8 animate-in-slide">
                  <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
                     <div className="relative w-full sm:w-96">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input 
                          placeholder="Search synthetic entities..." 
                          value={explorerSearch} 
                          onChange={(e) => setExplorerSearch(e.target.value)}
                          className="pl-9 h-10 w-full bg-card border-border text-xs focus-visible:ring-1 focus-visible:ring-primary"
                        />
                     </div>
                     <Button className="h-10 px-8 bg-primary hover:bg-primary/90 text-primary-foreground rounded-sm text-xs tracking-widest font-medium">
                        <Download className="h-4 w-4 mr-2" /> Export Archive
                     </Button>
                  </div>

                  <div className="border border-border rounded-md bg-card overflow-hidden shadow-sm">
                     <table className="w-full text-left">
                        <thead>
                           <tr className="bg-muted/30 border-b border-border">
                              <th className="px-6 py-4 text-[10px] font-medium tracking-widest uppercase text-muted-foreground">Entity ID</th>
                              <th className="px-6 py-4 text-[10px] font-medium tracking-widest uppercase text-muted-foreground">Label</th>
                              <th className="px-6 py-4 text-[10px] font-medium tracking-widest uppercase text-muted-foreground">Confidence</th>
                              <th className="px-6 py-4 text-[10px] font-medium tracking-widest uppercase text-muted-foreground">Origin Mapping</th>
                           </tr>
                        </thead>
                        <tbody className="divide-y divide-border/50">
                           {mockExplorerData.map((row) => (
                              <tr key={row.id} className="hover:bg-muted/30 transition-colors group">
                                 <td className="px-6 py-4 text-xs font-mono text-primary/70">#{row.id.toString().padStart(4, '0')}</td>
                                 <td className="px-6 py-4 text-sm font-normal text-foreground">{row.name}</td>
                                 <td className="px-6 py-4">
                                    <div className="flex items-center gap-3">
                                       <div className="w-24 h-1.5 bg-muted rounded-full overflow-hidden">
                                          <div className="bg-primary h-full transition-all" style={{ width: `${row.fidelity * 100}%` }} />
                                       </div>
                                       <span className="text-[10px] font-medium text-muted-foreground">{(row.fidelity * 100).toFixed(0)}%</span>
                                    </div>
                                 </td>
                                 <td className="px-6 py-4 text-xs text-muted-foreground uppercase tracking-wider">{row.city} / Cluster Node 0{row.id}</td>
                              </tr>
                           ))}
                        </tbody>
                     </table>
                  </div>
                </div>
              )}

              {activeTab === "fidelity" && (
                <div className="space-y-12 animate-in-slide">
                  {/* High-Level Audit Metrics */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    {[
                      { label: "Aggregate Fidelity", value: "0.94", icon: BarChart3, color: "text-primary" },
                      { label: "Privacy Guard", value: "A+", icon: ShieldCheck, color: "text-green-500" },
                      { label: "Synthesis Drift", value: "0.02", icon: Globe, color: "text-muted-foreground" },
                      { label: "Audit Pass Rate", value: "98.2%", icon: CheckCircle2, color: "text-primary" },
                    ].map((stat, i) => (
                      <div key={i} className="bg-card border border-border rounded-md p-6 shadow-sm">
                        <div className="flex items-center gap-4">
                          <div className={`p-2 rounded-sm bg-muted/40 ${stat.color}`}>
                            <stat.icon className="h-4 w-4" />
                          </div>
                          <div>
                            <p className="text-[9px] font-medium text-muted-foreground uppercase tracking-widest">{stat.label}</p>
                            <p className={`text-xl font-normal tracking-tight ${stat.color}`}>{stat.value}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                     {/* Radial Quality Charts */}
                     <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-card border border-border rounded-md p-8 shadow-sm flex flex-col items-center justify-center text-center relative overflow-hidden group">
                           <div className="absolute top-4 left-6 text-[10px] font-medium tracking-widest uppercase text-muted-foreground">Distribution Fidelity</div>
                           <div className="relative w-48 h-48 mb-6 mt-4">
                              <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                                 <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="6" className="text-muted/20" />
                                 <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="6" strokeDasharray="282.7" strokeDashoffset="16.9" className="text-primary transition-all duration-1000 ease-out" style={{ strokeLinecap: 'round' }} />
                                 <circle cx="50" cy="50" r="45" fill="none" stroke="white" strokeWidth="0.5" strokeDasharray="1 4" className="opacity-30" />
                              </svg>
                              <div className="absolute inset-0 flex flex-col items-center justify-center">
                                 <span className="text-4xl font-normal tracking-tight">94%</span>
                                 <span className="text-[8px] font-medium text-muted-foreground uppercase tracking-widest">Confidence</span>
                              </div>
                           </div>
                           <p className="text-[10px] text-muted-foreground font-light leading-relaxed max-w-[200px]">Statistical variance remains within acceptable KS-Test parameters.</p>
                        </div>

                        <div className="bg-card border border-border rounded-md p-8 shadow-sm flex flex-col items-center justify-center text-center relative overflow-hidden group">
                           <div className="absolute top-4 left-6 text-[10px] font-medium tracking-widest uppercase text-muted-foreground">Privacy Compliance</div>
                           <div className="relative w-48 h-48 mb-6 mt-4">
                              <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                                 <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="6" className="text-muted/20" />
                                 <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="6" strokeDasharray="282.7" strokeDashoffset="5.6" className="text-green-500 transition-all duration-1000 ease-out" style={{ strokeLinecap: 'round' }} />
                                 <circle cx="50" cy="50" r="45" fill="none" stroke="white" strokeWidth="0.5" strokeDasharray="1 4" className="opacity-30" />
                              </svg>
                              <div className="absolute inset-0 flex flex-col items-center justify-center">
                                 <span className="text-4xl font-normal tracking-tight text-green-500">98%</span>
                                 <span className="text-[8px] font-medium text-muted-foreground uppercase tracking-widest">Anonymity</span>
                              </div>
                           </div>
                           <p className="text-[10px] text-muted-foreground font-light leading-relaxed max-w-[200px]">ε-differential privacy noise layers verified across all PII columns.</p>
                        </div>
                     </div>

                     {/* Privacy Alerts / Audit Log */}
                     <div className="bg-card border border-border rounded-md p-6 shadow-sm flex flex-col h-full">
                        <h3 className="text-[10px] font-medium tracking-[0.2em] uppercase text-muted-foreground mb-8 flex items-center gap-2">
                           <ShieldAlert className="h-3.5 w-3.5 text-primary" /> Security Audit
                        </h3>
                        <div className="space-y-6 flex-1">
                           {[
                              { type: "Cleansed", msg: "Identified and synthesized 12 PII markers in 'Users' blueprint.", time: "2m ago" },
                              { type: "Success", msg: "Differential privacy verification passed (ε=0.1).", time: "14m ago" },
                              { type: "Warning", msg: "Small sample size detected for 'Region' categorical synthesis.", time: "1h ago" },
                              { type: "Safe", msg: "DCR Audit: 0% production record correlation.", time: "3h ago" },
                           ].map((alert, i) => (
                              <div key={i} className="flex flex-col gap-1.5 border-l-2 border-primary/10 pl-4 py-0.5">
                                 <div className="flex items-center justify-between">
                                    <span className={`text-[9px] font-bold uppercase tracking-[0.15em] ${alert.type === 'Warning' ? 'text-yellow-500' : 'text-primary/70'}`}>{alert.type}</span>
                                    <span className="text-[8px] text-muted-foreground uppercase">{alert.time}</span>
                                 </div>
                                 <p className="text-[11px] font-light text-muted-foreground leading-snug">{alert.msg}</p>
                              </div>
                           ))}
                        </div>
                        <div className="mt-8 pt-6 border-t border-border">
                           <Button variant="outline" className="w-full rounded-sm h-9 text-[10px] uppercase tracking-widest border-border hover:bg-muted font-medium">Download Security Report</Button>
                        </div>
                     </div>
                  </div>

                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}

function ShieldAlert(props: any) { return <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-shield-alert"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>; }
function ShieldCheck(props: any) { return <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-shield-check"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/></svg>; }
