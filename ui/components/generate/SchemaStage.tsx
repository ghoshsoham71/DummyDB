"use client"

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { ApiResponse } from "./types";
import { parseSQL, parseSupabase, parseMongoDB, parseNeo4j, SchemaListItem } from "@/lib/api";
import { VisualSchemaBuilder } from "./VisualSchemaBuilder";

export const schemaFormSchema = z.object({
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

export type SchemaFormData = z.infer<typeof schemaFormSchema>;

interface SchemaStageProps {
  onSchemaParsed: (data: any) => void;
  isUploading: boolean;
  setIsUploading: (val: boolean) => void;
  setUploadError: (val: string | null) => void;
  savedSchemas: SchemaListItem[];
  loadExistingSchema: (sid: string) => void;
  schemaSource: "upload" | "existing" | "builder";
  setSchemaSource: (val: "upload" | "existing" | "builder") => void;
}

export function SchemaStage({
  onSchemaParsed, isUploading, setIsUploading, setUploadError,
  savedSchemas, loadExistingSchema, schemaSource, setSchemaSource
}: SchemaStageProps) {
  const form = useForm<SchemaFormData>({
    resolver: zodResolver(schemaFormSchema),
    defaultValues: { databaseType: "sql", neo4jUri: "bolt://localhost:7687", neo4jUsername: "neo4j" },
  });

  const selectedDbType = form.watch("databaseType");

  const onSubmit = async (data: SchemaFormData) => {
    setIsUploading(true); setUploadError(null);
    try {
      let res: any;
      if (data.databaseType === "supabase") res = await parseSupabase(data.connectionString!);
      else if (data.databaseType === "sql") res = await parseSQL(data.sqlFile as File, data.seedDataFile as File);
      else if (data.databaseType === "nosql") res = await parseMongoDB(data.connectionString!, data.mongoDbName!);
      else if (data.databaseType === "graph") res = await parseNeo4j(data.neo4jUri!, data.neo4jUsername!, data.neo4jPassword!, data.neo4jDatabase!);
      onSchemaParsed(res);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally { setIsUploading(false); }
  };

  return (
    <div className="bg-card p-6 rounded-lg border">
      <h2 className="text-xl font-semibold mb-4">Step 1: Upload Schema</h2>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField control={form.control} name="databaseType" render={({ field }) => (
            <FormItem>
              <FormLabel>Database Type</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                <SelectContent>
                  <SelectItem value="sql">SQL</SelectItem>
                  <SelectItem value="supabase">Supabase</SelectItem>
                  <SelectItem value="nosql">MongoDB</SelectItem>
                  <SelectItem value="graph">Neo4j</SelectItem>
                </SelectContent>
              </Select>
            </FormItem>
          )} />
          <div className="flex gap-2">
            <Button type="button" variant={schemaSource === "upload" ? "default" : "outline"} size="sm" onClick={() => setSchemaSource("upload")}>Upload File</Button>
            <Button type="button" variant={schemaSource === "existing" ? "default" : "outline"} size="sm" onClick={() => setSchemaSource("existing")}>Existing</Button>
            <Button type="button" variant={schemaSource === "builder" ? "default" : "outline"} size="sm" onClick={() => setSchemaSource("builder")}>Builder</Button>
          </div>
          {schemaSource === "upload" && (
            <>
              {selectedDbType === "sql" && (
                <FormField control={form.control} name="sqlFile" render={({ field: { onChange } }) => (
                  <FormItem>
                    <FormLabel>SQL File</FormLabel>
                    <FormControl>
                      <Input type="file" accept=".sql" onChange={(e) => onChange(e.target.files?.[0])} />
                    </FormControl>
                  </FormItem>
                )} />
              )}
              <Button type="submit" disabled={isUploading} className="w-full">{isUploading ? "Uploading..." : "Upload & Parse"}</Button>
            </>
          )}
          {schemaSource === "existing" && (
            <Select onValueChange={loadExistingSchema}>
              <SelectTrigger><SelectValue placeholder="Select schema" /></SelectTrigger>
              <SelectContent>{savedSchemas.map(s => <SelectItem key={s.schema_id} value={s.schema_id}>{s.filename}</SelectItem>)}</SelectContent>
            </Select>
          )}
          {schemaSource === "builder" && (
            <div className="pt-4 border-t mt-4">
               <VisualSchemaBuilder onSave={(schema) => onSchemaParsed(schema)} />
            </div>
          )}
        </form>
      </Form>
    </div>
  );
}
