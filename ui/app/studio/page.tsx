"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Database, Plus, Sparkles, Send } from "lucide-react";
import { VisualSchemaBuilder } from "@/components/generate/VisualSchemaBuilder";
import { useSchemaStore } from "@/stores/schema-store";
import { useJobStore } from "@/stores/job-store";
import { useJobStream } from "@/hooks/use-job-stream";
import { ImportSchemaDialog } from "@/components/generate/ImportSchemaDialog";
import { generateSyntheticData, parseJsonSchema } from "@/lib/api";

export default function StudioPage() {
  const { currentSchema, setCurrentSchema } = useSchemaStore();
  const { activeJobs, addJob } = useJobStore();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  useJobStream(activeJobId || undefined);

  const handleSaveSchema = async (schema: any) => {
    try {
      const response = await parseJsonSchema(schema);
      if (response.success) {
        setCurrentSchema({
            id: (response as any).schema_id,
            name: "New Schema",
            canonical_schema: schema
        });
      }
    } catch (err) {
      console.error("Failed to save schema:", err);
    }
  };

  const handleGenerate = async () => {
    if (!currentSchema) return;
    
    try {
      const response = await generateSyntheticData({
        schema_id: currentSchema.id,
        num_rows: { "*": 100 }, // Default for now
        synthesizer_type: "ctgan"
      });

      if (response.success) {
        const jobId = response.generation_id;
        addJob({
            id: jobId,
            schema_id: currentSchema.id,
            job_type: "synthetic_generation",
            status: "pending",
            progress: 0,
            parameters: {},
            created_at: new Date().toISOString()
        });
        setActiveJobId(jobId);
      }
    } catch (err) {
      console.error("Generation failed:", err);
    }
  };

  return (
    <div className="container mx-auto py-8 space-y-8">
      <div className="flex justify-between items-center bg-card p-6 rounded-xl border border-primary/20 shadow-lg">
        <div>
          <h1 className="text-3xl font-black tracking-tight flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-primary animate-pulse" />
            BurstDB Studio
          </h1>
          <p className="text-muted-foreground mt-1">Design, Seed, and Scale your synthetic data models.</p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            size="lg" 
            className="border-primary/20 hover:bg-primary/5"
            onClick={() => setImportDialogOpen(true)}
          >
            Import Schema
          </Button>
          <Button size="lg" className="shadow-lg shadow-primary/20" onClick={handleGenerate} disabled={!currentSchema}>
            <Send className="w-4 h-4 mr-2" />
            Generate Data
          </Button>
        </div>
      </div>

      <ImportSchemaDialog open={importDialogOpen} onOpenChange={setImportDialogOpen} />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-3 space-y-6">
          <VisualSchemaBuilder 
            onSave={handleSaveSchema} 
            initialSchema={currentSchema?.canonical_schema}
          />
        </div>

        <div className="space-y-6">
          <Card className="border-primary/20 shadow-xl overflow-hidden">
            <CardHeader className="bg-primary/5 border-b border-primary/10">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Database className="w-4 h-4 text-primary" />
                Active Job Session
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
                {activeJobId && activeJobs[activeJobId] ? (
                    <div className="space-y-4">
                        <div className="flex justify-between text-xs font-bold uppercase tracking-wider text-muted-foreground">
                            <span>{activeJobs[activeJobId].status}</span>
                            <span>{Math.round(activeJobs[activeJobId].progress * 100)}%</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2 overflow-hidden border border-primary/10">
                            <div 
                                className="bg-primary h-full transition-all duration-500 ease-out shadow-[0_0_10px_rgba(var(--primary),0.5)]" 
                                style={{ width: `${activeJobs[activeJobId].progress * 100}%` }}
                            />
                        </div>
                        <p className="text-[10px] text-center text-muted-foreground italic">
                            {activeJobs[activeJobId].status === 'running' ? "Orchestrating generative models..." : "Awaiting worker pickup..."}
                        </p>
                    </div>
                ) : (
                    <div className="py-10 text-center space-y-3 opacity-50">
                        <div className="inline-flex items-center justify-center p-3 bg-muted rounded-full">
                            <Plus className="w-6 h-6" />
                        </div>
                        <p className="text-xs">No active generation job</p>
                    </div>
                )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
