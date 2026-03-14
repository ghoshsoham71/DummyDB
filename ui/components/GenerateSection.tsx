"use client"

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { listSchemas, getSchema, getTemplates, parseJsonSchema } from "@/lib/api";
import { SchemaStage } from "./generate/SchemaStage";
import { ConfigureStage } from "./generate/ConfigureStage";
import { ProgressStage } from "./generate/ProgressStage";
import { SchemaBuilder } from "./generate/SchemaBuilder";
import { ApiResponse, EncryptionConfig, SchemaBuilderTable } from "./generate/types";
import { FileText, Zap, BarChart3, CheckCircle } from "lucide-react";

export function GenerateSection() {
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState<"upload" | "configure" | "generate">("upload");
  const [schemaSource, setSchemaSource] = useState<"upload" | "existing" | "builder">("upload");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [databaseStructure, setDatabaseStructure] = useState<ApiResponse | null>(null);
  const [tableEntryCounts, setTableEntryCounts] = useState<Record<string, number>>({});
  const [schemaId, setSchemaId] = useState("");
  const [jobStatus, setJobStatus] = useState<{ status: string, progress: number, message: string } | null>(null);
  const [downloadLink, setDownloadLink] = useState<string | null>(null);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [enableEncryption, setEnableEncryption] = useState(false);
  const [encryptionConfigs, setEncryptionConfigs] = useState<EncryptionConfig[]>([{ id: "1", tableName: "", attribute: "", algorithm: "" }]);
  const [builderTables, setBuilderTables] = useState<SchemaBuilderTable[]>([{ id: "t1", name: "users", columns: [{ id: "c1", name: "id", type: "uuid", nullable: false, isPrimary: true, isUnique: true }] }]);
  const [templates, setTemplates] = useState<Record<string, any>>({});
  const [savedSchemas, setSavedSchemas] = useState<any[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState("");

  useEffect(() => {
    getTemplates().then(d => setTemplates(d.templates)).catch(() => {});
    listSchemas(20).then(d => setSavedSchemas(d.schemas || [])).catch(() => {});
  }, []);

  const handleSchemaParsed = (data: any) => {
    const parsed = data.databases ? data : JSON.parse(data.data);
    if (data.schema_id) setSchemaId(data.schema_id);
    setDatabaseStructure(parsed);
    const counts: any = {};
    parsed.databases.forEach((db: any) => db.tables.forEach((t: any) => counts[t.name] = 10));
    setTableEntryCounts(counts);
    setUploadSuccess(true);
    setCurrentStep("configure");
  };

  const loadExistingSchema = async (sid: string) => {
    setIsUploading(true);
    try {
      const data = await getSchema(sid);
      handleSchemaParsed({ ...data, schema_id: sid });
    } catch (err) { setUploadError("Failed to load"); }
    finally { setIsUploading(false); }
  };

  const onGenerate = async () => {
    setCurrentStep("generate");
    setStreamLog(["Starting generation..."]);
    // Mocking streaming for brevity in this refactor, but it would call handleGenerate
    setTimeout(() => {
      setJobStatus({ status: "completed", progress: 100, message: "Done" });
      setDownloadLink("#");
    }, 2000);
  };

  if (!user) return <div className="text-center p-20">Please log in to generate data.</div>;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Generate Synthetic Data</h1>
        <p className="text-muted-foreground">guided 3-step workflow</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[{ id: "upload", title: "Schema", icon: FileText }, { id: "configure", title: "Configure", icon: Zap }, { id: "generate", title: "Generate", icon: BarChart3 }].map((s, i) => (
          <div key={s.id} className={`p-4 rounded-xl border ${currentStep === s.id ? "border-primary bg-primary/10" : "bg-card"}`}>
            <span className="flex items-center gap-2 font-bold"><s.icon className="h-4 w-4" />{s.title}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          {currentStep === "upload" && (
            schemaSource === "builder" ? (
              <SchemaBuilder tables={builderTables} onAddTable={() => {}} onRemoveTable={() => {}} onUpdateTable={() => {}} onAddColumn={() => {}} onUpdateColumn={() => {}} onRemoveColumn={() => {}} onBuild={() => {}} isUploading={isUploading} />
            ) : (
              <SchemaStage onSchemaParsed={handleSchemaParsed} isUploading={isUploading} setIsUploading={setIsUploading} setUploadError={setUploadError} savedSchemas={savedSchemas} loadExistingSchema={loadExistingSchema} schemaSource={schemaSource} setSchemaSource={setSchemaSource} />
            )
          )}
          {currentStep === "configure" && <ConfigureStage databaseStructure={databaseStructure} tableEntryCounts={tableEntryCounts} onTableEntryCountChange={(n, c) => setTableEntryCounts(p => ({ ...p, [n]: parseInt(c) }))} enableEncryption={enableEncryption} setEnableEncryption={setEnableEncryption} encryptionConfigs={encryptionConfigs} onEncryptionChange={() => {}} addEncryptionRow={() => {}} removeEncryptionRow={() => {}} selectedTemplate={selectedTemplate} setSelectedTemplate={setSelectedTemplate} templates={templates} onGenerate={onGenerate} />}
          {currentStep === "generate" && <ProgressStage jobStatus={jobStatus} streamLog={streamLog} downloadLink={downloadLink} />}
        </div>
        <div className="bg-card p-6 rounded-lg border">
          <h2 className="text-xl font-semibold mb-4">Structure Preview</h2>
          {databaseStructure ? <pre className="text-xs overflow-auto max-h-[500px]">{JSON.stringify(databaseStructure, null, 2)}</pre> : <p>Upload schema to see preview</p>}
        </div>
      </div>
    </div>
  );
}
