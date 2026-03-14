"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Upload, FileText, Loader2, AlertCircle } from "lucide-react";
import { parseSQL } from "@/lib/api";
import { useSchemaStore } from "@/stores/schema-store";
import { useAuth } from "@/lib/auth-context";

interface ImportSchemaDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ImportSchemaDialog({ open, onOpenChange }: ImportSchemaDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setCurrentSchema } = useSchemaStore();
  const { user } = useAuth();

  const handleImport = async () => {
    if (!file) return;
    if (!user) {
      setError("Please sign in to import schemas");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const response = await parseSQL(file);
      // Backend returns ParseResponse which has 'data' as stringified JSON of the schema
      const schemaData = JSON.parse((response as any).data);
      
      setCurrentSchema({
        id: (response as any).schema_id || Math.random().toString(36).substring(7),
        name: file.name,
        canonical_schema: schemaData
      });
      
      onOpenChange(false);
      setFile(null);
    } catch (err: any) {
      setError(err.message || "Failed to parse schema");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Import SQL Schema</DialogTitle>
          <DialogDescription>
            Upload a .sql file containing your table definitions.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div 
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              file ? 'border-primary bg-primary/5' : 'border-muted-foreground/20 hover:border-primary/50'
            }`}
          >
            <input
              type="file"
              accept=".sql"
              className="hidden"
              id="sql-upload"
              onChange={(e) => {
                const selected = e.target.files?.[0];
                if (selected) {
                  setFile(selected);
                  setError(null);
                }
              }}
            />
            <label htmlFor="sql-upload" className="cursor-pointer space-y-2 block">
              <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                {file ? <FileText className="w-6 h-6 text-primary" /> : <Upload className="w-6 h-6" />}
              </div>
              <div className="text-sm font-medium">
                {file ? file.name : "Click to upload or drag & drop"}
              </div>
              <p className="text-xs text-muted-foreground">
                SQL files up to 10MB
              </p>
            </label>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-xs text-destructive p-3 bg-destructive/10 rounded border border-destructive/20">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isUploading}>
            Cancel
          </Button>
          <Button onClick={handleImport} disabled={!file || isUploading}>
            {isUploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Parsing...
              </>
            ) : "Import Schema"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
