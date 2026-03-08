"use client"

import { useState, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Upload, Database, Save, AlertCircle, FileText, Table, Plus, Trash2, ArrowRight, XCircle, Zap, BarChart3, Library, Globe, ExternalLink } from "lucide-react";
import {
  listSchemas,
  getSchema,
  getTemplates,
  generateSyntheticData,
  getJobStatus,
  cancelJob,
  getDownloadUrl,
  parseMongoDB,
  parseNeo4j,
  type SchemaListItem,
  type GenerationTemplate,
  type Database as DatabaseType,
} from "@/lib/api";

/* ─── Form Schema ─── */

const formSchema = z.object({
  databaseType: z.enum(["sql", "supabase", "nosql", "graph"]),
  sqlFile: z.instanceof(File).optional(),
  seedDataFile: z.instanceof(File).optional(),
  connectionString: z.string().optional(),
  mongoDbName: z.string().optional(),
  neo4jUri: z.string().optional(),
  neo4jUsername: z.string().optional(),
  neo4jPassword: z.string().optional(),
  neo4jDatabase: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

interface ApiResponse {
  schema_id?: string;
  databases: DatabaseType[];
  source?: string;
  connection?: { uri?: string; http_browser?: string };
}

interface EncryptionConfig {
  id: string;
  tableName: string;
  attribute: string;
  algorithm: string;
}

const ENCRYPTION_ALGORITHMS = [
  "AES-256", "AES-128", "RSA-2048", "RSA-4096",
  "ChaCha20", "Twofish", "Blowfish", "DES", "3DES"
];

export default function GeneratePage() {
  const [currentStep, setCurrentStep] = useState<"upload" | "configure">("upload");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [databaseStructure, setDatabaseStructure] = useState<ApiResponse | null>(null);
  const [tableEntryCounts, setTableEntryCounts] = useState<Record<string, number>>({});
  const [schemaId, setSchemaId] = useState<string>("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<{status: string, progress: number, message: string} | null>(null);
  const [downloadLink, setDownloadLink] = useState<string | null>(null);
  const [enableEncryption, setEnableEncryption] = useState(false);
  const [encryptionConfigs, setEncryptionConfigs] = useState<EncryptionConfig[]>([
    { id: "1", tableName: "", attribute: "", algorithm: "" }
  ]);
  const [neo4jBrowserUrl, setNeo4jBrowserUrl] = useState<string | null>(null);

  // Templates & saved schemas
  const [templates, setTemplates] = useState<Record<string, GenerationTemplate>>({});
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [savedSchemas, setSavedSchemas] = useState<SchemaListItem[]>([]);
  const [inputMode, setInputMode] = useState<"file" | "existing">("file");

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: { databaseType: "sql", neo4jUri: "bolt://localhost:7687", neo4jUsername: "neo4j" },
  });

  const selectedDbType = form.watch("databaseType");

  useEffect(() => {
    getTemplates().then((d) => setTemplates(d.templates)).catch(() => {});
    listSchemas(20).then((d) => setSavedSchemas(d.schemas || [])).catch(() => {});
  }, []);

  const handleTableEntryCountChange = (tableName: string, count: string) => {
    setTableEntryCounts((prev) => ({ ...prev, [tableName]: parseInt(count) || 0 }));
  };

  const handleEncryptionChange = (id: string, field: keyof EncryptionConfig, value: string) => {
    setEncryptionConfigs((prev) => prev.map((c) => c.id === id ? { ...c, [field]: value } : c));
  };

  const addEncryptionRow = () => {
    setEncryptionConfigs((prev) => [...prev, { id: String(prev.length + 1), tableName: "", attribute: "", algorithm: "" }]);
  };

  const removeEncryptionRow = (id: string) => {
    if (encryptionConfigs.length > 1) setEncryptionConfigs((prev) => prev.filter((c) => c.id !== id));
  };

  /* ─── Load existing schema ─── */
  const loadExistingSchema = async (sid: string) => {
    setIsUploading(true); setUploadError(null);
    try {
      const data = await getSchema(sid);
      const schema = (data as Record<string, unknown>).schema as ApiResponse | undefined;
      if (schema) {
        setSchemaId(sid);
        setDatabaseStructure(schema);
        const counts: Record<string, number> = {};
        schema.databases.forEach((db) => db.tables.forEach((t) => { counts[t.name] = 10; }));
        setTableEntryCounts(counts);
        setCurrentStep("configure");
        setUploadSuccess(true);
      }
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Failed to load schema");
    } finally { setIsUploading(false); }
  };

  /* ─── Handle schema result ─── */
  const handleSchemaResult = (responseData: Record<string, unknown>) => {
    let parsedData: ApiResponse;
    if (responseData.data && typeof responseData.data === "string") {
      parsedData = JSON.parse(responseData.data);
    } else if (responseData.databases) {
      parsedData = responseData as unknown as ApiResponse;
    } else {
      throw new Error("Unexpected response format");
    }

    if (responseData.schema_id) setSchemaId(responseData.schema_id as string);
    setDatabaseStructure(parsedData);

    // Check for Neo4j browser URL
    if (parsedData.connection?.http_browser) {
      setNeo4jBrowserUrl(parsedData.connection.http_browser);
    }
    if (responseData.statistics && typeof responseData.statistics === "object") {
      const stats = responseData.statistics as Record<string, unknown>;
      if (stats.neo4j_browser) setNeo4jBrowserUrl(stats.neo4j_browser as string);
    }

    const counts: Record<string, number> = {};
    parsedData.databases.forEach((db) => db.tables.forEach((t) => { counts[t.name] = 10; }));
    setTableEntryCounts(counts);
    setCurrentStep("configure");
    setUploadSuccess(true);
  };

  /* ─── Upload / Parse ─── */
  const onSubmit = async (data: FormData) => {
    setIsUploading(true); setUploadError(null); setUploadSuccess(false);
    setDatabaseStructure(null); setNeo4jBrowserUrl(null);

    try {
      let responseData: Record<string, unknown>;

      if (data.databaseType === "supabase") {
        if (!data.connectionString) throw new Error("Connection string required");
        const res = await fetch("http://localhost:8000/api/v1/parse/supabase", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ connection_string: data.connectionString, save_to_disk: true, overwrite_existing: true }),
        });
        if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
        responseData = await res.json();

      } else if (data.databaseType === "sql") {
        const fd = new FormData();
        if (data.sqlFile) fd.append("file", data.sqlFile);
        if (data.seedDataFile) fd.append("seed_data_file", data.seedDataFile);
        const res = await fetch("http://localhost:8000/api/v1/parse?save_to_disk=true&overwrite_existing=true", {
          method: "POST", body: fd,
        });
        if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
        responseData = await res.json();

      } else if (data.databaseType === "nosql") {
        if (!data.connectionString) throw new Error("MongoDB connection string required");
        responseData = await parseMongoDB(data.connectionString, data.mongoDbName || undefined) as Record<string, unknown>;

      } else if (data.databaseType === "graph") {
        const uri = data.neo4jUri || "bolt://localhost:7687";
        const username = data.neo4jUsername || "neo4j";
        const password = data.neo4jPassword || "";
        responseData = await parseNeo4j(uri, username, password, data.neo4jDatabase || undefined) as Record<string, unknown>;

      } else {
        throw new Error("Unsupported database type");
      }

      handleSchemaResult(responseData);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed");
    } finally { setIsUploading(false); }
  };

  /* ─── Template application ─── */
  const applyTemplate = (key: string) => setSelectedTemplate(key);

  /* ─── Generate ─── */
  const handleGenerateData = async () => {
    if (!databaseStructure || !schemaId) return;
    setIsUploading(true); setUploadError(null);
    setJobId(null); setJobStatus(null); setDownloadLink(null);
    try {
      const tmpl = selectedTemplate ? templates[selectedTemplate] : null;
      const result = await generateSyntheticData({
        schema_id: schemaId,
        scale_factor: tmpl?.scale_factor ?? 2.0,
        num_rows: tableEntryCounts,
        synthesizer_type: tmpl?.synthesizer_type ?? "HMA",
        output_format: "csv",
      });
      if (!result.success) throw new Error(result.message || "Generation failed");
      setJobId(result.generation_id);
      pollJobStatus(result.generation_id);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Generation failed");
      setIsUploading(false);
    }
  };

  /* ─── Cancel ─── */
  const handleCancelJob = async () => {
    if (!jobId) return;
    try {
      await cancelJob(jobId);
      setJobStatus({ status: "cancelled", progress: 0, message: "Job cancelled by user" });
      setIsUploading(false);
    } catch { setUploadError("Failed to cancel job"); }
  };

  /* ─── Polling ─── */
  const pollJobStatus = useCallback(async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const s = await getJobStatus(id);
        setJobStatus({ status: s.status, progress: s.progress, message: s.message || "" });
        if (s.status === "completed" || s.status === "failed" || s.status === "cancelled") {
          clearInterval(interval); setIsUploading(false);
          if (s.status === "completed") { setUploadSuccess(true); setDownloadLink(getDownloadUrl(id)); }
          else if (s.status === "failed") { setUploadError(s.error || "Job failed"); }
        }
      } catch { /* retry */ }
    }, 2000);
  }, []);

  /* ─── Reset ─── */
  const resetToUpload = () => {
    setCurrentStep("upload"); setDatabaseStructure(null);
    setTableEntryCounts({}); setEnableEncryption(false);
    setEncryptionConfigs([{ id: "1", tableName: "", attribute: "", algorithm: "" }]);
    setUploadSuccess(false); setUploadError(null);
    setJobId(null); setJobStatus(null); setDownloadLink(null);
    setSelectedTemplate(""); setInputMode("file"); setNeo4jBrowserUrl(null);
    form.reset();
  };

  const getTableNames = () => {
    if (!databaseStructure) return [];
    const names: string[] = [];
    databaseStructure.databases.forEach((db) => db.tables.forEach((t) => names.push(t.name)));
    return names;
  };

  const getTableAttributes = (tableName: string) => {
    if (!databaseStructure) return [];
    for (const db of databaseStructure.databases)
      for (const t of db.tables)
        if (t.name === tableName) return t.attributes.map((a) => a.name);
    return [];
  };

  return (
    <div className="font-sans min-h-screen flex flex-col bg-background text-foreground">
      <main className="flex flex-1 flex-col items-center justify-center text-center gap-8 px-4">
        <h1 className="text-3xl sm:text-5xl font-bold tracking-tight mb-2">Generate Data</h1>
        <p className="text-lg max-w-xl text-muted-foreground mb-6">
          Upload a schema or connect to your database to generate realistic mock data.
        </p>

        <div className="w-full max-w-4xl">
          {/* Step Indicator */}
          <div className="flex items-center justify-center mb-8">
            <div className={`flex items-center ${currentStep === "upload" ? "text-primary" : "text-muted-foreground"}`}>
              <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center ${currentStep === "upload" ? "border-primary bg-primary text-primary-foreground" : "border-muted"}`}>1</div>
              <span className="ml-2 font-medium">Connect / Upload</span>
            </div>
            <ArrowRight className="mx-4 h-5 w-5 text-muted-foreground" />
            <div className={`flex items-center ${currentStep === "configure" ? "text-primary" : "text-muted-foreground"}`}>
              <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center ${currentStep === "configure" ? "border-primary bg-primary text-primary-foreground" : "border-muted"}`}>2</div>
              <span className="ml-2 font-medium">Configure &amp; Generate</span>
            </div>
          </div>

          {/* ─── STEP 1: Upload / Connect ─── */}
          {currentStep === "upload" && (
            <>
              {savedSchemas.length > 0 && (
                <div className="flex gap-2 mb-6 justify-center">
                  <Button type="button" variant={inputMode === "file" ? "default" : "outline"} size="sm" onClick={() => setInputMode("file")}>
                    <Upload className="h-4 w-4 mr-1" /> New Connection
                  </Button>
                  <Button type="button" variant={inputMode === "existing" ? "default" : "outline"} size="sm" onClick={() => setInputMode("existing")}>
                    <Library className="h-4 w-4 mr-1" /> Existing Schema
                  </Button>
                </div>
              )}

              {inputMode === "existing" && savedSchemas.length > 0 ? (
                <div className="space-y-3 text-left">
                  <h3 className="font-semibold text-lg">Previously Parsed Schemas</h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {savedSchemas.map((s) => (
                      <button key={s.schema_id} type="button" onClick={() => loadExistingSchema(s.schema_id)} disabled={isUploading}
                        className="w-full text-left p-3 border rounded-md hover:bg-muted/50 transition-colors flex items-center justify-between">
                        <div>
                          <p className="font-medium">{s.filename || s.schema_id}</p>
                          <p className="text-xs text-muted-foreground">{s.table_count ?? "?"} tables · {s.created_at ? new Date(s.created_at).toLocaleDateString() : ""}</p>
                        </div>
                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    {/* Database Type */}
                    <FormField control={form.control} name="databaseType" render={({ field }) => (
                      <FormItem>
                        <FormLabel className="flex items-center gap-2"><Database className="h-4 w-4" /> Database Type</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl><SelectTrigger><SelectValue placeholder="Select database type" /></SelectTrigger></FormControl>
                          <SelectContent>
                            <SelectItem value="sql">SQL (File Upload)</SelectItem>
                            <SelectItem value="supabase">Supabase (PostgreSQL)</SelectItem>
                            <SelectItem value="nosql">MongoDB (NoSQL)</SelectItem>
                            <SelectItem value="graph">Neo4j (Graph DB)</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )} />

                    {/* ─── SQL inputs ─── */}
                    {selectedDbType === "sql" && (
                      <>
                        <FormField control={form.control} name="sqlFile" render={({ field: { onChange, value: _value, ...field } }) => (
                          <FormItem>
                            <FormLabel className="flex items-center gap-2"><Upload className="h-4 w-4" /> SQL File (Required)</FormLabel>
                            <FormControl>
                              <Input type="file" accept=".sql,text/plain" onChange={(e: React.ChangeEvent<HTMLInputElement>) => onChange(e.target.files?.[0])} {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )} />
                        <FormField control={form.control} name="seedDataFile" render={({ field: { onChange, value: _value, ...field } }) => (
                          <FormItem>
                            <FormLabel className="flex items-center gap-2"><FileText className="h-4 w-4" /> Seed Data (Optional)</FormLabel>
                            <FormControl>
                              <Input type="file" accept=".sql,.csv,text/plain,text/csv" onChange={(e: React.ChangeEvent<HTMLInputElement>) => onChange(e.target.files?.[0])} {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )} />
                      </>
                    )}

                    {/* ─── Supabase input ─── */}
                    {selectedDbType === "supabase" && (
                      <FormField control={form.control} name="connectionString" render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center gap-2"><Database className="h-4 w-4" /> Supabase Postgres Connection String</FormLabel>
                          <FormControl>
                            <Input type="text" placeholder="postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )} />
                    )}

                    {/* ─── MongoDB inputs ─── */}
                    {selectedDbType === "nosql" && (
                      <>
                        <FormField control={form.control} name="connectionString" render={({ field }) => (
                          <FormItem>
                            <FormLabel className="flex items-center gap-2"><Globe className="h-4 w-4" /> MongoDB Connection String</FormLabel>
                            <FormControl>
                              <Input type="text" placeholder="mongodb://localhost:27017 or mongodb+srv://user:pass@cluster.mongodb.net" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )} />
                        <FormField control={form.control} name="mongoDbName" render={({ field }) => (
                          <FormItem>
                            <FormLabel>Database Name (optional — leave blank to scan all)</FormLabel>
                            <FormControl><Input type="text" placeholder="myDatabase" {...field} /></FormControl>
                            <FormMessage />
                          </FormItem>
                        )} />
                      </>
                    )}

                    {/* ─── Neo4j inputs ─── */}
                    {selectedDbType === "graph" && (
                      <>
                        <Alert className="text-left">
                          <AlertDescription className="flex items-center gap-2">
                            <ExternalLink className="h-4 w-4 shrink-0" />
                            Neo4j Browser: <a href="http://localhost:7474" target="_blank" rel="noopener noreferrer" className="underline text-primary">http://localhost:7474</a>
                            &nbsp;| Bolt: <code className="text-xs">bolt://localhost:7687</code>
                          </AlertDescription>
                        </Alert>
                        <FormField control={form.control} name="neo4jUri" render={({ field }) => (
                          <FormItem>
                            <FormLabel className="flex items-center gap-2"><Globe className="h-4 w-4" /> Bolt URI</FormLabel>
                            <FormControl><Input type="text" placeholder="bolt://localhost:7687" {...field} /></FormControl>
                            <FormMessage />
                          </FormItem>
                        )} />
                        <div className="grid grid-cols-2 gap-4">
                          <FormField control={form.control} name="neo4jUsername" render={({ field }) => (
                            <FormItem>
                              <FormLabel>Username</FormLabel>
                              <FormControl><Input type="text" placeholder="neo4j" {...field} /></FormControl>
                            </FormItem>
                          )} />
                          <FormField control={form.control} name="neo4jPassword" render={({ field }) => (
                            <FormItem>
                              <FormLabel>Password</FormLabel>
                              <FormControl><Input type="password" placeholder="password" {...field} /></FormControl>
                            </FormItem>
                          )} />
                        </div>
                        <FormField control={form.control} name="neo4jDatabase" render={({ field }) => (
                          <FormItem>
                            <FormLabel>Database (optional)</FormLabel>
                            <FormControl><Input type="text" placeholder="neo4j (default)" {...field} /></FormControl>
                          </FormItem>
                        )} />
                      </>
                    )}

                    {/* Submit */}
                    <Button type="submit" className="w-full" disabled={isUploading}>
                      {isUploading ? (
                        <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" /> Connecting &amp; Parsing...</>
                      ) : (
                        <><Save className="h-4 w-4 mr-2" /> Parse &amp; Continue</>
                      )}
                    </Button>
                  </form>
                </Form>
              )}
            </>
          )}

          {/* ─── STEP 2: Configure & Generate ─── */}
          {currentStep === "configure" && databaseStructure && (
            <div className="space-y-6 text-left">
              <h2 className="text-2xl font-bold mb-4">Schema Structure &amp; Configuration</h2>

              {/* Neo4j browser link */}
              {neo4jBrowserUrl && (
                <Alert className="mb-4">
                  <AlertDescription className="flex items-center gap-2">
                    <ExternalLink className="h-4 w-4" />
                    <a href={neo4jBrowserUrl} target="_blank" rel="noopener noreferrer" className="underline text-primary">
                      Open Neo4j Browser ({neo4jBrowserUrl})
                    </a>
                  </AlertDescription>
                </Alert>
              )}

              {/* Template Selector */}
              {Object.keys(templates).length > 0 && (
                <div className="mb-6 p-4 border rounded-lg bg-muted/20">
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><Zap className="h-5 w-5" /> Generation Template</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {Object.entries(templates).map(([key, tmpl]) => (
                      <button key={key} type="button" onClick={() => applyTemplate(key)}
                        className={`p-3 border rounded-md text-left transition-all ${selectedTemplate === key ? "border-primary bg-primary/10 ring-2 ring-primary/30" : "hover:bg-muted/50"}`}>
                        <p className="font-medium text-sm">{tmpl.name}</p>
                        <p className="text-xs text-muted-foreground mt-1">{tmpl.description}</p>
                        <p className="text-xs text-primary mt-1">{tmpl.synthesizer_type} · {tmpl.scale_factor}x</p>
                      </button>
                    ))}
                  </div>
                  {selectedTemplate && (
                    <p className="text-xs text-muted-foreground mt-2">
                      <BarChart3 className="h-3 w-3 inline mr-1" />{templates[selectedTemplate]?.recommended_for}
                    </p>
                  )}
                </div>
              )}

              {/* Database Structure */}
              {databaseStructure.databases.map((db, i) => (
                <div key={i} className="mb-6 p-4 border rounded-lg">
                  <h3 className="text-xl font-semibold mb-3 text-primary">{db.name}</h3>
                  <div className="space-y-4">
                    {db.tables.map((table, j) => (
                      <div key={j} className="p-3 border rounded-md bg-muted/30">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="text-lg font-medium flex items-center gap-2">
                            <Table className="h-4 w-4" />
                            {table.name}
                            {table.node_type && (
                              <span className={`text-xs px-1.5 py-0.5 rounded ${table.node_type === "node" ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400" : "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"}`}>
                                {table.node_type}
                              </span>
                            )}
                          </h4>
                          <div className="flex items-center gap-2">
                            <label className="text-sm font-medium">Entries:</label>
                            <Input type="number" min="1" value={tableEntryCounts[table.name] || 10}
                              onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleTableEntryCountChange(table.name, e.target.value)} className="w-20" />
                          </div>
                        </div>

                        {/* Relationships for Neo4j nodes */}
                        {table.relationships && table.relationships.length > 0 && (
                          <div className="mb-2 text-xs text-muted-foreground">
                            <span className="font-medium">Relationships:</span>{" "}
                            {table.relationships.map((r, k) => (
                              <span key={k} className="inline-flex items-center gap-1 mr-2">
                                <ArrowRight className="h-3 w-3" /> {r.type} → {r.target}
                              </span>
                            ))}
                          </div>
                        )}

                        <div className="text-sm text-muted-foreground">
                          <p className="mb-2">Attributes:</p>
                          <ul className="space-y-1">
                            {table.attributes.map((attr, k) => (
                              <li key={k} className="flex items-center gap-2">
                                <span className="font-mono text-xs bg-background px-2 py-1 rounded">{attr.name}</span>
                                <span className="text-xs">({attr.type})</span>
                                {attr.constraints.length > 0 && <span className="text-xs text-muted-foreground">[{attr.constraints.join(", ")}]</span>}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {/* Encryption Section */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold mb-3">Encryption Configuration</h3>
                <div className="flex items-center space-x-4">
                  <label className="flex items-center space-x-2"><input type="radio" name="encryption" checked={!enableEncryption} onChange={() => setEnableEncryption(false)} /> <span>No Encryption</span></label>
                  <label className="flex items-center space-x-2"><input type="radio" name="encryption" checked={enableEncryption} onChange={() => setEnableEncryption(true)} /> <span>Enable Encryption</span></label>
                </div>
                {enableEncryption && (
                  <div className="space-y-4 mt-4">
                    <p className="text-sm text-muted-foreground">Configure which attributes to encrypt:</p>
                    {encryptionConfigs.map((config) => (
                      <div key={config.id} className="flex items-center gap-3 p-3 border rounded-md bg-muted/20">
                        <div className="flex-1"><Select value={config.tableName} onValueChange={(v: string) => handleEncryptionChange(config.id, "tableName", v)}>
                          <SelectTrigger><SelectValue placeholder="Table" /></SelectTrigger>
                          <SelectContent>{getTableNames().map((n) => <SelectItem key={n} value={n}>{n}</SelectItem>)}</SelectContent>
                        </Select></div>
                        <div className="flex-1"><Select value={config.attribute} onValueChange={(v: string) => handleEncryptionChange(config.id, "attribute", v)} disabled={!config.tableName}>
                          <SelectTrigger><SelectValue placeholder="Attribute" /></SelectTrigger>
                          <SelectContent>{config.tableName && getTableAttributes(config.tableName).map((n) => <SelectItem key={n} value={n}>{n}</SelectItem>)}</SelectContent>
                        </Select></div>
                        <div className="flex-1"><Select value={config.algorithm} onValueChange={(v: string) => handleEncryptionChange(config.id, "algorithm", v)}>
                          <SelectTrigger><SelectValue placeholder="Algorithm" /></SelectTrigger>
                          <SelectContent>{ENCRYPTION_ALGORITHMS.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}</SelectContent>
                        </Select></div>
                        <Button type="button" variant="outline" size="icon" onClick={() => removeEncryptionRow(config.id)} disabled={encryptionConfigs.length === 1}><Trash2 className="h-4 w-4" /></Button>
                      </div>
                    ))}
                    <Button type="button" variant="outline" onClick={addEncryptionRow}><Plus className="h-4 w-4 mr-1" /> Add Row</Button>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-4 mt-6">
                <Button variant="outline" onClick={resetToUpload} className="flex-1">Back</Button>
                <Button onClick={handleGenerateData} className="flex-1" disabled={isUploading}>
                  {isUploading ? (<><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" /> Generating...</>) : (<><Database className="h-4 w-4 mr-2" /> Generate Mock Data</>)}
                </Button>
              </div>
            </div>
          )}

          {/* Job Progress */}
          {jobStatus && currentStep === "configure" && !uploadSuccess && (
            <div className="w-full mt-4 p-4 border rounded-lg bg-muted text-left">
              <div className="flex justify-between mb-2">
                <span className="font-medium text-sm text-primary uppercase">{jobStatus.status}</span>
                <div className="flex items-center gap-3">
                  <span className="text-sm">{jobStatus.progress.toFixed(0)}%</span>
                  {(jobStatus.status === "pending" || jobStatus.status === "running") && (
                    <Button variant="destructive" size="sm" onClick={handleCancelJob}><XCircle className="h-3 w-3 mr-1" /> Cancel</Button>
                  )}
                </div>
              </div>
              <div className="w-full bg-secondary rounded-full h-2 mb-2">
                <div className="bg-primary h-2 rounded-full transition-all" style={{ width: `${jobStatus.progress}%` }} />
              </div>
              <p className="text-xs text-muted-foreground">{jobStatus.message}</p>
            </div>
          )}

          {/* Success */}
          {uploadSuccess && currentStep === "configure" && downloadLink && (
            <div className="w-full mt-6 p-6 border border-green-200 bg-green-50 dark:bg-green-900/20 dark:border-green-800 rounded-lg text-left">
              <h3 className="text-xl font-bold text-green-800 dark:text-green-400 mb-2">Generation Complete!</h3>
              <p className="text-sm text-green-700 dark:text-green-500 mb-6">Your synthetic data is ready for download.</p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Button asChild className="flex-1"><a href={downloadLink} download>Download (ZIP)</a></Button>
                <Button variant="outline" onClick={resetToUpload} className="flex-1">Generate New Data</Button>
              </div>
            </div>
          )}

          {/* Error */}
          {uploadError && (
            <Alert variant="destructive" className="mt-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{uploadError}</AlertDescription>
            </Alert>
          )}
        </div>
      </main>
    </div>
  );
}