"use client"

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Database, Trash2, Download, XCircle, RefreshCw,
  CheckCircle2, Clock, AlertCircle, Loader2, Activity,
  HardDrive, BarChart3, FileText, Globe, TrendingUp
} from "lucide-react";
import {
  listSchemas, listJobs, deleteSchema, bulkDeleteSchemas,
  cancelJob, getDownloadUrl, getDashboardOverview, getDashboardActivity,
  type SchemaListItem, type JobItem, type DashboardOverview, type ActivityEvent,
} from "@/lib/api";

import { ProtectedRoute } from "@/components/ProtectedRoute";

function statusBadge(status: string) {
  const icons: Record<string, React.ReactNode> = {
    completed: <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />,
    running: <Loader2 className="h-3.5 w-3.5 text-blue-500 animate-spin" />,
    pending: <Clock className="h-3.5 w-3.5 text-yellow-500" />,
    failed: <AlertCircle className="h-3.5 w-3.5 text-red-500" />,
    cancelled: <XCircle className="h-3.5 w-3.5 text-muted-foreground" />,
  };
  const colors: Record<string, string> = {
    completed: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
    running: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
    pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
    failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
    cancelled: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || colors.pending}`}>
      {icons[status] || <Clock className="h-3.5 w-3.5" />} {status}
    </span>
  );
}

function formatBytes(b: number) {
  if (!b) return "0 B";
  const k = 1024, s = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(b) / Math.log(k));
  return parseFloat((b / Math.pow(k, i)).toFixed(1)) + " " + s[i];
}

function timeAgo(d: string | number) {
  const sec = Math.floor((Date.now() - new Date(d).getTime()) / 1000);
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

export default function DashboardPage() {
  const [tab, setTab] = useState<"overview" | "schemas" | "jobs">("overview");
  const [schemas, setSchemas] = useState<SchemaListItem[]>([]);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [schemaSearch, setSchemaSearch] = useState("");
  const [selectedSchemas, setSelectedSchemas] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

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
    } catch (e) { setError(e instanceof Error ? e.message : "Failed to load"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleDeleteSchema = async (id: string) => {
    try {
      await deleteSchema(id);
      setSchemas((p) => p.filter((s) => s.schema_id !== id));
      setSelectedSchemas((p) => { const n = new Set(p); n.delete(id); return n; });
      flash("Schema deleted");
    } catch (e) { setError(e instanceof Error ? e.message : "Delete failed"); }
  };

  const handleBulkDelete = async () => {
    if (!selectedSchemas.size) return;
    try {
      await bulkDeleteSchemas(Array.from(selectedSchemas));
      setSchemas((p) => p.filter((s) => !selectedSchemas.has(s.schema_id)));
      flash(`${selectedSchemas.size} schemas deleted`); setSelectedSchemas(new Set());
    } catch (e) { setError(e instanceof Error ? e.message : "Bulk delete failed"); }
  };

  const handleCancelJob = async (jid: string) => {
    try {
      await cancelJob(jid);
      setJobs((p) => p.map((j) => j.job_id === jid ? { ...j, status: "cancelled" } : j));
      flash("Job cancelled");
    } catch (e) { setError(e instanceof Error ? e.message : "Cancel failed"); }
  };

  const flash = (msg: string) => { setSuccessMsg(msg); setTimeout(() => setSuccessMsg(null), 3000); };

  const toggleSchema = (id: string) => setSelectedSchemas((p) => { const n = new Set(p); if (n.has(id)) { n.delete(id); } else { n.add(id); } return n; });

  const filteredSchemas = schemas.filter((s) =>
    !schemaSearch || (s.filename || s.schema_id).toLowerCase().includes(schemaSearch.toLowerCase()));

  const sourceLabel = (src: string) => {
    const map: Record<string, string> = { sql_upload: "SQL", supabase_extractor: "Supabase", mongodb_extractor: "MongoDB", neo4j_extractor: "Neo4j" };
    return map[src] || src;
  };

  return (
    <ProtectedRoute>
      <div className="font-sans min-h-screen flex flex-col bg-background text-foreground">
        <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <Button variant="outline" size="sm" onClick={fetchAll}><RefreshCw className="h-4 w-4 mr-1" /> Refresh</Button>
          </div>

          {successMsg && <Alert className="mb-4 border-green-200 bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400"><CheckCircle2 className="h-4 w-4" /><AlertDescription>{successMsg}</AlertDescription></Alert>}
          {error && <Alert variant="destructive" className="mb-4"><AlertCircle className="h-4 w-4" /><AlertDescription>{error}</AlertDescription></Alert>}

          {/* Tabs */}
          <div className="flex border-b mb-6">
            {([
              { key: "overview" as const, label: "Overview", icon: <TrendingUp className="h-4 w-4" /> },
              { key: "schemas" as const, label: "Schemas", icon: <Database className="h-4 w-4" />, count: schemas.length },
              { key: "jobs" as const, label: "Jobs", icon: <Activity className="h-4 w-4" />, count: jobs.length },
            ]).map((t) => (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === t.key ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
                {t.icon} {t.label}
                {"count" in t && t.count !== undefined && <span className="ml-1 text-xs bg-muted px-1.5 py-0.5 rounded-full">{t.count}</span>}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground"><Loader2 className="h-6 w-6 animate-spin mr-2" /> Loading…</div>
          ) : (
            <>
              {/* ─── Overview Tab ─── */}
              {tab === "overview" && overview && (
                <div className="space-y-6">
                  {/* Stat Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <Card icon={<Database className="h-5 w-5 text-blue-500" />} label="Schemas" value={overview.schemas.total} />
                    <Card icon={<FileText className="h-5 w-5 text-indigo-500" />} label="Total Tables" value={overview.schemas.total_tables} />
                    <Card icon={<HardDrive className="h-5 w-5 text-violet-500" />} label="Synthetic Files" value={overview.synthetic_files.total} />
                    <Card icon={<BarChart3 className="h-5 w-5 text-green-500" />} label="Storage" value={formatBytes(overview.synthetic_files.total_size)} />
                  </div>

                  {/* Source Breakdown */}
                  {Object.keys(overview.schemas.by_source).length > 0 && (
                    <div className="border rounded-lg p-4">
                      <h3 className="font-semibold text-sm mb-3 flex items-center gap-2"><Globe className="h-4 w-4" /> Schemas by Source</h3>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        {Object.entries(overview.schemas.by_source).map(([src, count]) => (
                          <div key={src} className="flex items-center justify-between p-2 border rounded bg-muted/20">
                            <span className="text-sm font-medium">{sourceLabel(src)}</span>
                            <span className="text-lg font-bold">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Activity Timeline */}
                  {activity.length > 0 && (
                    <div className="border rounded-lg p-4">
                      <h3 className="font-semibold text-sm mb-3 flex items-center gap-2"><Activity className="h-4 w-4" /> Recent Activity</h3>
                      <div className="space-y-2">
                        {activity.map((ev, i) => (
                          <div key={i} className="flex items-center gap-3 py-1.5 border-b last:border-0 text-sm">
                            <span className={`w-2 h-2 rounded-full shrink-0 ${ev.type.includes("completed") ? "bg-green-500" :
                              ev.type.includes("failed") ? "bg-red-500" :
                                ev.type.includes("running") ? "bg-blue-500" :
                                  "bg-yellow-500"
                              }`} />
                            <span className="flex-1 truncate">
                              <span className="font-medium">{ev.type.replace(/_/g, " ")}</span>
                              {ev.filename && <span className="text-muted-foreground"> — {ev.filename}</span>}
                              {ev.message && <span className="text-muted-foreground"> — {ev.message}</span>}
                            </span>
                            <span className="text-xs text-muted-foreground shrink-0">{ev.timestamp ? timeAgo(ev.timestamp) : ""}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ─── Schemas Tab ─── */}
              {tab === "schemas" && (
                <div>
                  <div className="flex items-center gap-3 mb-4">
                    <Input placeholder="Search schemas…" value={schemaSearch} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSchemaSearch(e.target.value)} className="max-w-xs" />
                    {selectedSchemas.size > 0 && <Button variant="destructive" size="sm" onClick={handleBulkDelete}><Trash2 className="h-3 w-3 mr-1" /> Delete {selectedSchemas.size}</Button>}
                  </div>
                  {filteredSchemas.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground"><Database className="h-10 w-10 mx-auto mb-3 opacity-30" /><p>No schemas found.</p></div>
                  ) : (
                    <div className="border rounded-lg overflow-hidden">
                      <div className="grid grid-cols-[auto_1fr_80px_80px_80px_60px] gap-4 px-4 py-2 bg-muted text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        <div><input type="checkbox" checked={selectedSchemas.size === filteredSchemas.length && !!filteredSchemas.length} onChange={() => setSelectedSchemas(selectedSchemas.size === filteredSchemas.length ? new Set() : new Set(filteredSchemas.map(s => s.schema_id)))} /></div>
                        <div>Name</div><div>Tables</div><div>Size</div><div>Age</div><div></div>
                      </div>
                      {filteredSchemas.map((s) => (
                        <div key={s.schema_id} className="grid grid-cols-[auto_1fr_80px_80px_80px_60px] gap-4 px-4 py-3 border-t items-center hover:bg-muted/30">
                          <div><input type="checkbox" checked={selectedSchemas.has(s.schema_id)} onChange={() => toggleSchema(s.schema_id)} /></div>
                          <div className="truncate"><span className="font-medium">{s.filename || s.schema_id}</span><p className="text-xs text-muted-foreground truncate">{s.schema_id}</p></div>
                          <div className="text-sm">{s.table_count ?? "—"}</div>
                          <div className="text-sm">{formatBytes(s.file_size || 0)}</div>
                          <div className="text-xs text-muted-foreground">{s.created_at ? timeAgo(s.created_at) : "—"}</div>
                          <div><Button variant="ghost" size="icon" onClick={() => handleDeleteSchema(s.schema_id)}><Trash2 className="h-4 w-4 text-destructive" /></Button></div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ─── Jobs Tab ─── */}
              {tab === "jobs" && (
                <div>
                  {jobs.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground"><Activity className="h-10 w-10 mx-auto mb-3 opacity-30" /><p>No jobs yet.</p></div>
                  ) : (
                    <div className="space-y-3">
                      {jobs.map((job) => (
                        <div key={job.job_id} className="border rounded-lg p-4 hover:bg-muted/20 transition-colors">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-3">{statusBadge(job.status)} <span className="font-mono text-xs text-muted-foreground">{job.job_id.slice(0, 8)}…</span></div>
                            <div className="flex items-center gap-2">
                              {job.status === "completed" && <Button asChild variant="outline" size="sm"><a href={getDownloadUrl(job.job_id)} download><Download className="h-3 w-3 mr-1" /> Download</a></Button>}
                              {(job.status === "pending" || job.status === "running") && <Button variant="destructive" size="sm" onClick={() => handleCancelJob(job.job_id)}><XCircle className="h-3 w-3 mr-1" /> Cancel</Button>}
                            </div>
                          </div>
                          {(job.status === "running" || job.status === "pending") && (
                            <div className="w-full bg-secondary rounded-full h-1.5 mb-2"><div className="bg-primary h-1.5 rounded-full transition-all" style={{ width: `${job.progress}%` }} /></div>
                          )}
                          <div className="flex items-center gap-4 text-xs text-muted-foreground">
                            <span>{job.created_at ? timeAgo(job.created_at) : ""}</span>
                            {job.message && <span>· {job.message}</span>}
                            {job.error && <span className="text-red-500">· {job.error}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}

function Card({ icon, label, value }: { icon: React.ReactNode; label: string; value: number | string }) {
  return (
    <div className="border rounded-lg p-4 flex items-center gap-3">
      {icon}
      <div><p className="text-2xl font-bold">{value}</p><p className="text-xs text-muted-foreground">{label}</p></div>
    </div>
  );
}
