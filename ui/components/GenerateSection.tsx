"use client"

import { useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Upload, Database, Save, AlertCircle, FileText, Table, Plus, Trash2, Zap, BarChart3, Globe, CheckCircle } from "lucide-react";
import {
  listSchemas,
  getSchema,
  getTemplates,
  parseSQL,
  parseSupabase,
  parseMongoDB,
  parseNeo4j,
  parseJsonSchema,
  type SchemaListItem,
  type GenerationTemplate,
  type Database as DatabaseType,
  type StreamEvent,
} from "@/lib/api";

import { useAuth } from "@/lib/auth-context";

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

interface SchemaBuilderColumn {
  id: string;
  name: string;
  type: string;
  nullable: boolean;
  isPrimary: boolean;
  isUnique: boolean;
}

interface SchemaBuilderTable {
  id: string;
  name: string;
  columns: SchemaBuilderColumn[];
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

export function GenerateSection() {
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState<"upload" | "configure" | "generate">("upload");
  const [schemaSource, setSchemaSource] = useState<"upload" | "existing" | "builder">("upload");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [databaseStructure, setDatabaseStructure] = useState<ApiResponse | null>(null);
  const [tableEntryCounts, setTableEntryCounts] = useState<Record<string, number>>({});
  const [schemaId, setSchemaId] = useState<string>("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<{ status: string, progress: number, message: string } | null>(null);
  const [downloadLink, setDownloadLink] = useState<string | null>(null);
  const [enableEncryption, setEnableEncryption] = useState(false);
  const [encryptionConfigs, setEncryptionConfigs] = useState<EncryptionConfig[]>([
    { id: "1", tableName: "", attribute: "", algorithm: "" }
  ]);
  const [neo4jBrowserUrl, setNeo4jBrowserUrl] = useState<string | null>(null);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Schema builder state (premium flow: build or edit schema inline)
  const [builderDatabaseName, setBuilderDatabaseName] = useState<string>("main");
  const [builderTables, setBuilderTables] = useState<SchemaBuilderTable[]>([
    {
      id: "table-1",
      name: "users",
      columns: [
        { id: "col-1", name: "id", type: "uuid", nullable: false, isPrimary: true, isUnique: true },
        { id: "col-2", name: "email", type: "string", nullable: false, isPrimary: false, isUnique: true },
        { id: "col-3", name: "created_at", type: "timestamp", nullable: false, isPrimary: false, isUnique: false },
      ],
    },
  ]);

  // Templates & saved schemas
  const [templates, setTemplates] = useState<Record<string, GenerationTemplate>>({});
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [savedSchemas, setSavedSchemas] = useState<SchemaListItem[]>([]);

  const steps = [
    {
      id: "upload",
      title: "Schema",
      subtitle: "Upload or build your schema",
      icon: FileText,
    },
    {
      id: "configure",
      title: "Configure",
      subtitle: "Set table sizes & options",
      icon: Zap,
    },
    {
      id: "generate",
      title: "Generate",
      subtitle: "Run and download data",
      icon: BarChart3,
    },
  ];

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: { databaseType: "sql", neo4jUri: "bolt://localhost:7687", neo4jUsername: "neo4j" },
  });

  const selectedDbType = form.watch("databaseType");

  useEffect(() => {
    getTemplates().then((d) => setTemplates(d.templates)).catch(() => { });
    listSchemas(20).then((d) => setSavedSchemas(d.schemas || [])).catch(() => { });
  }, []);

  const genId = () => window.crypto?.randomUUID?.() ?? Math.random().toString(16).slice(2);

  const addTable = () => {
    const newTable: SchemaBuilderTable = {
      id: genId(),
      name: `table_${builderTables.length + 1}`,
      columns: [
        { id: genId(), name: "id", type: "uuid", nullable: false, isPrimary: true, isUnique: true },
      ],
    };
    setBuilderTables((prev) => [...prev, newTable]);
  };

  const removeTable = (tableId: string) => {
    setBuilderTables((prev) => prev.filter((t) => t.id !== tableId));
  };

  const updateTableName = (tableId: string, name: string) => {
    setBuilderTables((prev) => prev.map((t) => (t.id === tableId ? { ...t, name } : t)));
  };

  const addColumn = (tableId: string) => {
    setBuilderTables((prev) =>
      prev.map((t) =>
        t.id === tableId
          ? {
              ...t,
              columns: [
                ...t.columns,
                {
                  id: genId(),
                  name: "new_column",
                  type: "string",
                  nullable: true,
                  isPrimary: false,
                  isUnique: false,
                },
              ],
            }
          : t
      )
    );
  };

  const updateColumn = (
    tableId: string,
    columnId: string,
    field: keyof SchemaBuilderColumn,
    value: string | boolean
  ) => {
    setBuilderTables((prev) =>
      prev.map((t) =>
        t.id === tableId
          ? {
              ...t,
              columns: t.columns.map((c) =>
                c.id === columnId ? { ...c, [field]: value } : c
              ),
            }
          : t
      )
    );
  };

  const removeColumn = (tableId: string, columnId: string) => {
    setBuilderTables((prev) =>
      prev.map((t) =>
        t.id === tableId
          ? { ...t, columns: t.columns.filter((c) => c.id !== columnId) }
          : t
      )
    );
  };

  const buildSchemaFromBuilder = async () => {
    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(false);
    setDatabaseStructure(null);
    setNeo4jBrowserUrl(null);

    try {
      const schemaPayload = {
        databases: [
          {
            name: builderDatabaseName || "main",
            tables: builderTables.map((t) => ({
              name: t.name,
              columns: t.columns.map((c) => ({
                name: c.name,
                type: c.type,
                nullable: c.nullable,
                constraints: [
                  ...(c.isPrimary ? ["PRIMARY_KEY"] : []),
                  ...(c.isUnique ? ["UNIQUE"] : []),
                ],
              })),
            })),
          },
        ],
      };

      const responseData = await parseJsonSchema(schemaPayload);
      handleSchemaResult(responseData);
      setSchemaSource("existing");
      setCurrentStep("configure");
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Failed to save schema");
    } finally {
      setIsUploading(false);
    }
  };

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
        setSchemaSource("existing");
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
    setSchemaSource("existing");
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
        responseData = await parseSupabase(data.connectionString);

      } else if (data.databaseType === "sql") {
        responseData = await parseSQL(data.sqlFile as File, data.seedDataFile as File | undefined);

      } else if (data.databaseType === "nosql") {
        if (!data.connectionString) throw new Error("MongoDB connection string required");
        if (!data.mongoDbName) throw new Error("MongoDB database name required");
        responseData = await parseMongoDB(data.connectionString, data.mongoDbName);

      } else if (data.databaseType === "graph") {
        if (!data.neo4jUri || !data.neo4jUsername || !data.neo4jPassword || !data.neo4jDatabase) {
          throw new Error("All Neo4j fields are required");
        }
        responseData = await parseNeo4j(data.neo4jUri, data.neo4jUsername, data.neo4jPassword, data.neo4jDatabase);

      } else {
        throw new Error("Invalid database type");
      }

      handleSchemaResult(responseData);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  /* ─── Generate ─── */
  const handleGenerate = async () => {
    if (!databaseStructure || !schemaId) return;

    setCurrentStep("generate");
    setJobId(null);
    setJobStatus(null);
    setDownloadLink(null);
    setStreamLog([]);

    try {
      const payload = {
        schema_id: schemaId,
        table_entry_counts: tableEntryCounts,
        template: selectedTemplate || undefined,
        encryption: enableEncryption ? encryptionConfigs.filter(c => c.tableName && c.attribute && c.algorithm) : undefined,
      };

      const response = await fetch("http://localhost:8000/api/v1/generate/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error(`Generation failed: ${response.statusText}`);

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event: StreamEvent = JSON.parse(line.slice(6));
              setStreamLog((prev) => [...prev, event.message]);

              if (event.type === "job_started") {
                setJobId(event.job_id || null);
              } else if (event.type === "progress") {
                setJobStatus({ status: "running", progress: event.progress || 0, message: event.message });
              } else if (event.type === "completed") {
                setJobStatus({ status: "completed", progress: 100, message: event.message });
                if (event.download_url) setDownloadLink(event.download_url);
              } else if (event.type === "error") {
                setJobStatus({ status: "error", progress: 0, message: event.message });
              }
            } catch (e) {
              console.error("Failed to parse SSE event:", e);
            }
          }
        }
      }
    } catch (err) {
      setJobStatus({ status: "error", progress: 0, message: err instanceof Error ? err.message : "Generation failed" });
    }
  };

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [streamLog]);

  if (!user) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold mb-2">Generate Synthetic Data</h1>
          <p className="text-muted-foreground">
            Upload your database schema or connect to an existing database to generate realistic synthetic data.
          </p>
          <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-yellow-800 dark:text-yellow-200">
              Please log in to access data generation features.
            </p>
          </div>
        </div>

        {/* Show disabled preview */}
        <div className="opacity-50 pointer-events-none">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Upload Section */}
            <div className="space-y-6">
              <div className="bg-card p-6 rounded-lg border">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                  <Upload className="h-5 w-5" />
                  Step 1: Upload Schema
                </h2>

                <Form {...form}>
                  <form className="space-y-4">
                    {/* Database Type */}
                    <FormField
                      control={form.control}
                      name="databaseType"
                      render={() => (
                        <FormItem>
                          <FormLabel>Database Type</FormLabel>
                          <Select disabled>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Select database type" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="sql">SQL (PostgreSQL, MySQL, etc.)</SelectItem>
                              <SelectItem value="supabase">Supabase</SelectItem>
                              <SelectItem value="nosql">MongoDB</SelectItem>
                              <SelectItem value="graph">Neo4j</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Input Mode Toggle */}
                    <div className="flex gap-2">
                      <Button type="button" variant="outline" size="sm" disabled>
                        Upload File
                      </Button>
                      <Button type="button" variant="outline" size="sm" disabled>
                        Use Existing Schema
                      </Button>
                    </div>

                    <Button type="submit" disabled className="w-full">
                      Upload & Parse
                    </Button>
                  </form>
                </Form>
              </div>
            </div>

            {/* Database Structure Preview */}
            <div className="space-y-6">
              <div className="bg-card p-6 rounded-lg border">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Database Structure
                </h2>
                <p className="text-muted-foreground">Upload a schema to see the structure here.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold mb-2">Generate Synthetic Data</h1>
        <p className="text-muted-foreground">
          Upload or craft a schema, then generate realistic synthetic data with a guided 3-step workflow.
        </p>
      </div>

      {/* Stepper */}
      <div className="mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {steps.map((step, index) => {
            const currentIndex = steps.findIndex((s) => s.id === currentStep);
            const isActive = currentStep === step.id;
            const isCompleted = currentIndex > index;
            const isDisabled = step.id !== "upload" && !uploadSuccess && !isActive;

            return (
              <button
                key={step.id}
                type="button"
                onClick={() => !isDisabled && setCurrentStep(step.id)}
                className={`flex flex-col items-start gap-2 p-4 rounded-2xl border transition-all ${
                  isActive
                    ? "border-primary bg-white/10 shadow-lg"
                    : isCompleted
                    ? "border-emerald-500 bg-emerald-500/10"
                    : "border-white/10 bg-white/5"
                } ${isDisabled ? "opacity-50 cursor-not-allowed" : "hover:shadow-lg"}`}
              >
                <div className="flex items-center gap-2">
                  {isCompleted ? (
                    <CheckCircle className="h-5 w-5 text-emerald-400" />
                  ) : (
                    <step.icon className="h-5 w-5" />
                  )}
                  <div>
                    <div className="text-sm font-semibold">{step.title}</div>
                    <div className="text-xs text-muted-foreground">{step.subtitle}</div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Upload Section */}
          <div className="space-y-6">
            <div className="bg-card p-6 rounded-lg border">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Step 1: Upload Schema
              </h2>

              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  {/* Database Type */}
                  <FormField
                    control={form.control}
                    name="databaseType"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Database Type</FormLabel>
                        <Select onValueChange={field.onChange} value={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select database type" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="sql">SQL (PostgreSQL, MySQL, etc.)</SelectItem>
                            <SelectItem value="supabase">Supabase</SelectItem>
                            <SelectItem value="nosql">MongoDB</SelectItem>
                            <SelectItem value="graph">Neo4j</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Input Mode Toggle */}
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant={schemaSource === "upload" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSchemaSource("upload")}
                    >
                      Upload File
                    </Button>
                    <Button
                      type="button"
                      variant={schemaSource === "existing" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSchemaSource("existing")}
                    >
                      Use Existing Schema
                    </Button>
                  </div>

                  {schemaSource === "upload" ? (
                    <>
                      {/* SQL File Upload */}
                      {selectedDbType === "sql" && (
                        <FormField
                          control={form.control}
                          name="sqlFile"
                          render={({ field: { onChange } }) => (
                            <FormItem>
                              <FormLabel>SQL Schema File</FormLabel>
                              <FormControl>
                                <Input
                                  type="file"
                                  accept=".sql"
                                  onChange={(e) => onChange(e.target.files?.[0])}
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      )}

                      {/* Supabase Connection */}
                      {selectedDbType === "supabase" && (
                        <FormField
                          control={form.control}
                          name="connectionString"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Supabase Connection String</FormLabel>
                              <FormControl>
                                <Input placeholder="postgresql://..." {...field} />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      )}

                      {/* MongoDB */}
                      {selectedDbType === "nosql" && (
                        <>
                          <FormField
                            control={form.control}
                            name="connectionString"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>MongoDB Connection String</FormLabel>
                                <FormControl>
                                  <Input placeholder="mongodb://..." {...field} />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="mongoDbName"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Database Name</FormLabel>
                                <FormControl>
                                  <Input placeholder="my_database" {...field} />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </>
                      )}

                      {/* Neo4j */}
                      {selectedDbType === "graph" && (
                        <>
                          <FormField
                            control={form.control}
                            name="neo4jUri"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Neo4j URI</FormLabel>
                                <FormControl>
                                  <Input placeholder="bolt://localhost:7687" {...field} />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="neo4jUsername"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Username</FormLabel>
                                <FormControl>
                                  <Input placeholder="neo4j" {...field} />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="neo4jPassword"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Password</FormLabel>
                                <FormControl>
                                  <Input type="password" {...field} />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="neo4jDatabase"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Database Name</FormLabel>
                                <FormControl>
                                  <Input placeholder="neo4j" {...field} />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </>
                      )}

                      {/* Seed Data File */}
                      {selectedDbType === "sql" && (
                        <FormField
                          control={form.control}
                          name="seedDataFile"
                          render={({ field: { onChange } }) => (
                            <FormItem>
                              <FormLabel>Seed Data File (Optional)</FormLabel>
                              <FormControl>
                                <Input
                                  type="file"
                                  accept=".csv,.json"
                                  onChange={(e) => onChange(e.target.files?.[0])}
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      )}

                      <Button type="submit" disabled={isUploading} className="w-full">
                        {isUploading ? "Uploading..." : "Upload & Parse"}
                      </Button>
                    </>
                  ) : schemaSource === "existing" ? (
                    <div className="space-y-2">
                      <FormLabel>Select Existing Schema</FormLabel>
                      <Select onValueChange={loadExistingSchema}>
                        <SelectTrigger>
                          <SelectValue placeholder="Choose a saved schema" />
                        </SelectTrigger>
                        <SelectContent>
                          {savedSchemas.map((schema) => (
                            <SelectItem key={schema.schema_id} value={schema.schema_id}>
                              {schema.filename} ({schema.schema_id.slice(0, 8)})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                          <FormLabel>Database Name</FormLabel>
                          <Input value={builderDatabaseName} onChange={(e) => setBuilderDatabaseName(e.target.value)} />
                        </div>
                        <div className="flex items-end gap-2">
                          <Button type="button" variant="outline" size="sm" onClick={() => setBuilderTables([{
                            id: genId(),
                            name: "users",
                            columns: [
                              { id: genId(), name: "id", type: "uuid", nullable: false, isPrimary: true, isUnique: true },
                            ],
                          }])}>
                            Reset
                          </Button>
                          <Button type="button" variant="outline" size="sm" onClick={addTable}>
                            <Plus className="h-4 w-4 mr-2" />
                            Add Table
                          </Button>
                        </div>
                      </div>

                      {builderTables.map((table) => (
                        <div key={table.id} className="border border-white/10 rounded-xl p-4 bg-white/5">
                          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                            <div className="flex-1">
                              <FormLabel>Table Name</FormLabel>
                              <Input
                                value={table.name}
                                onChange={(e) => updateTableName(table.id, e.target.value)}
                                placeholder="e.g. users"
                              />
                            </div>
                            <Button type="button" variant="ghost" size="icon" onClick={() => removeTable(table.id)}>
                              <Trash2 className="h-5 w-5" />
                            </Button>
                          </div>

                          <div className="mt-4 space-y-3">
                            {table.columns.map((column) => (
                              <div key={column.id} className="grid grid-cols-1 md:grid-cols-6 gap-2 items-center">
                                <Input
                                  value={column.name}
                                  onChange={(e) => updateColumn(table.id, column.id, "name", e.target.value)}
                                  placeholder="column name"
                                  className="md:col-span-2"
                                />
                                <Select
                                  value={column.type}
                                  onValueChange={(value) => updateColumn(table.id, column.id, "type", value)}
                                  className="md:col-span-2"
                                >
                                  <SelectTrigger>
                                    <SelectValue placeholder="Type" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {["string", "integer", "float", "boolean", "date", "timestamp", "uuid"].map((type) => (
                                      <SelectItem key={type} value={type}>
                                        {type}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>

                                <div className="flex items-center gap-2 md:col-span-2">
                                  <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                                    <input
                                      type="checkbox"
                                      checked={column.nullable}
                                      onChange={(e) => updateColumn(table.id, column.id, "nullable", e.target.checked)}
                                    />
                                    Nullable
                                  </label>
                                  <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                                    <input
                                      type="checkbox"
                                      checked={column.isPrimary}
                                      onChange={(e) => updateColumn(table.id, column.id, "isPrimary", e.target.checked)}
                                    />
                                    PK
                                  </label>
                                  <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                                    <input
                                      type="checkbox"
                                      checked={column.isUnique}
                                      onChange={(e) => updateColumn(table.id, column.id, "isUnique", e.target.checked)}
                                    />
                                    Unique
                                  </label>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => removeColumn(table.id, column.id)}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </div>
                              </div>
                            ))}

                            <Button type="button" variant="outline" size="sm" onClick={() => addColumn(table.id)}>
                              <Plus className="h-4 w-4 mr-2" />
                              Add Column
                            </Button>
                          </div>
                        </div>
                      ))}

                      <div className="mt-4">
                        <Button type="button" onClick={buildSchemaFromBuilder} disabled={isUploading}>
                          {isUploading ? "Saving schema..." : "Save schema & continue"}
                        </Button>
                      </div>
                    </div>
                  )}

                  <Button type="submit" disabled={isUploading} className="w-full">
                    {isUploading ? "Uploading..." : "Upload & Parse"}
                  </Button>
                </form>
              </Form>

              {uploadError && (
                <Alert variant="destructive" className="mt-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{uploadError}</AlertDescription>
                </Alert>
              )}

              {uploadSuccess && (
                <Alert className="mt-4">
                  <Database className="h-4 w-4" />
                  <AlertDescription>Schema uploaded successfully! Proceed to configure generation.</AlertDescription>
                </Alert>
              )}
            </div>
          </div>

          {/* Database Structure Preview */}
          <div className="space-y-6">
            {databaseStructure && (
              <div className="bg-card p-6 rounded-lg border">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Database Structure
                </h2>
                <div className="space-y-4">
                  {databaseStructure.databases?.map((db, dbIndex) => (
                    <div key={dbIndex} className="border rounded p-4">
                      <h3 className="font-medium mb-2">{db.name}</h3>
                      <div className="space-y-2">
                        {db.tables?.map((table, tableIndex) => (
                          <div key={tableIndex} className="flex items-center gap-2 text-sm">
                            <Table className="h-4 w-4" />
                            <span>{table.name}</span>
                            <span className="text-muted-foreground">({table.columns?.length ?? 0} columns)</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Configuration Section */}
        {uploadSuccess && currentStep === "configure" && (
          <div className="mt-8 bg-card p-6 rounded-lg border">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Step 2: Configure Generation
            </h2>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Table Entry Counts */}
              <div className="space-y-4">
                <h3 className="font-medium">Entry Counts per Table</h3>
                {databaseStructure?.databases?.flatMap((db) =>
                  (db.tables ?? []).map((table) => (
                    <div key={table.name} className="flex items-center gap-2">
                      <label className="text-sm font-medium min-w-[120px]">{table.name}:</label>
                      <Input
                        type="number"
                        min="1"
                        max="10000"
                        value={tableEntryCounts[table.name] || 10}
                        onChange={(e) => handleTableEntryCountChange(table.name, e.target.value)}
                        className="w-24"
                      />
                    </div>
                  ))
                )}
              </div>

              {/* Templates */}
              <div className="space-y-4">
                <h3 className="font-medium">Generation Template</h3>
                <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a template (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Default</SelectItem>
                    {Object.entries(templates).map(([key, template]) => (
                      <SelectItem key={key} value={key}>
                        {template.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Encryption */}
            <div className="mt-6">
              <div className="flex items-center gap-2 mb-4">
                <input
                  type="checkbox"
                  id="enableEncryption"
                  checked={enableEncryption}
                  onChange={(e) => setEnableEncryption(e.target.checked)}
                />
                <label htmlFor="enableEncryption" className="font-medium">Enable Data Encryption</label>
              </div>

              {enableEncryption && (
                <div className="space-y-2">
                  <h4 className="font-medium">Encryption Configuration</h4>
                  {encryptionConfigs.map((config) => (
                    <div key={config.id} className="flex gap-2 items-center">
                      <Select
                        value={config.tableName}
                        onValueChange={(value) => handleEncryptionChange(config.id, "tableName", value)}
                      >
                        <SelectTrigger className="w-32">
                          <SelectValue placeholder="Table" />
                        </SelectTrigger>
                        <SelectContent>
                          {databaseStructure?.databases.flatMap((db) => db.tables.map((t) => (
                            <SelectItem key={t.name} value={t.name}>{t.name}</SelectItem>
                          )))}
                        </SelectContent>
                      </Select>
                      <Select
                        value={config.attribute}
                        onValueChange={(value) => handleEncryptionChange(config.id, "attribute", value)}
                      >
                        <SelectTrigger className="w-32">
                          <SelectValue placeholder="Attribute" />
                        </SelectTrigger>
                        <SelectContent>
                          {databaseStructure?.databases.flatMap((db) =>
                            db.tables.find((t) => t.name === config.tableName)?.columns.map((c) => (
                              <SelectItem key={c.name} value={c.name}>{c.name}</SelectItem>
                            )) || []
                          )}
                        </SelectContent>
                      </Select>
                      <Select
                        value={config.algorithm}
                        onValueChange={(value) => handleEncryptionChange(config.id, "algorithm", value)}
                      >
                        <SelectTrigger className="w-32">
                          <SelectValue placeholder="Algorithm" />
                        </SelectTrigger>
                        <SelectContent>
                          {ENCRYPTION_ALGORITHMS.map((alg) => (
                            <SelectItem key={alg} value={alg}>{alg}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => removeEncryptionRow(config.id)}
                        disabled={encryptionConfigs.length <= 1}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  <Button type="button" variant="outline" size="sm" onClick={addEncryptionRow}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Encryption Rule
                  </Button>
                </div>
              )}
            </div>

            <div className="mt-6 flex gap-4">
              <Button onClick={handleGenerate} disabled={!databaseStructure}>
                <Zap className="h-4 w-4 mr-2" />
                Generate Synthetic Data
              </Button>
            </div>
          </div>
        )}

        {/* Generation Progress */}
        {currentStep === "generate" && (
          <div className="mt-8 bg-white/10 border border-white/10 backdrop-blur-xl shadow-sm p-6 rounded-2xl">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Step 3: Generate & Download
            </h2>

            {!jobStatus && (
              <p className="text-muted-foreground">Click &apos;Generate Synthetic Data&apos; to start and watch progress here.</p>
            )}

            {jobStatus && (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="flex-1 bg-secondary rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all"
                      style={{ width: `${jobStatus.progress}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">{jobStatus.progress}%</span>
                </div>

                <p className="text-sm text-muted-foreground">{jobStatus.message}</p>

                {jobId && (
                  <p className="text-xs text-muted-foreground">Job ID: {jobId}</p>
                )}

                {downloadLink && (
                  <div className="flex gap-2 flex-wrap">
                    <Button asChild>
                      <a href={downloadLink} download>
                        <Save className="h-4 w-4 mr-2" />
                        Download Generated Data
                      </a>
                    </Button>
                    {neo4jBrowserUrl && (
                      <Button variant="outline" asChild>
                        <a href={neo4jBrowserUrl} target="_blank" rel="noopener noreferrer">
                          <Globe className="h-4 w-4 mr-2" />
                          Open Neo4j Browser
                        </a>
                      </Button>
                    )}
                  </div>
                )}

                <div className="mt-4">
                  <h3 className="font-medium mb-2">Generation Log</h3>
                  <div className="bg-secondary p-4 rounded max-h-64 overflow-y-auto text-xs font-mono">
                    {streamLog.map((log, index) => (
                      <div key={index} className="mb-1">{log}</div>
                    ))}
                    <div ref={logEndRef} />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
    </div>
  );
}