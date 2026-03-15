"use client"

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Trash2, Plus, Zap } from "lucide-react";
import { ApiResponse, EncryptionConfig, ENCRYPTION_ALGORITHMS } from "./types";

interface ConfigureStageProps {
  databaseStructure: ApiResponse | null;
  tableEntryCounts: Record<string, number>;
  onTableEntryCountChange: (name: string, count: string) => void;
  enableEncryption: boolean;
  setEnableEncryption: (val: boolean) => void;
  encryptionConfigs: EncryptionConfig[];
  onEncryptionChange: (id: string, field: keyof EncryptionConfig, value: string) => void;
  addEncryptionRow: () => void;
  removeEncryptionRow: (id: string) => void;
  selectedTemplate: string;
  setSelectedTemplate: (val: string) => void;
  templates: Record<string, unknown>;
  onGenerate: () => void;
}

export function ConfigureStage({
  databaseStructure, tableEntryCounts, onTableEntryCountChange,
  enableEncryption, setEnableEncryption, encryptionConfigs,
  onEncryptionChange, addEncryptionRow, removeEncryptionRow,
  onGenerate
}: ConfigureStageProps) {
  if (!databaseStructure) return <div>No schema loaded</div>;

  return (
    <div className="space-y-6">
      <div className="bg-card p-6 rounded-lg border">
        <h2 className="text-xl font-semibold mb-4">Step 2: Configure Generation</h2>
        <div className="space-y-4">
          {databaseStructure.databases.map(db => db.tables.map(table => (
            <div key={table.name} className="flex items-center justify-between gap-4 p-3 bg-secondary/20 rounded-lg">
              <span className="font-medium">{table.name}</span>
              <Input type="number" value={tableEntryCounts[table.name] || 10} onChange={(e) => onTableEntryCountChange(table.name, e.target.value)} className="w-24" />
            </div>
          )))}
        </div>
      </div>

      <div className="bg-card p-6 rounded-lg border">
        <div className="flex items-center justify-between mb-4">
          <Label className="text-lg font-semibold">Encryption</Label>
          <Switch checked={enableEncryption} onCheckedChange={setEnableEncryption} />
        </div>
        {enableEncryption && (
          <div className="space-y-3">
            {encryptionConfigs.map(config => (
              <div key={config.id} className="flex gap-2 items-center">
                <Input placeholder="Table" value={config.tableName} onChange={(e) => onEncryptionChange(config.id, "tableName", e.target.value)} />
                <Input placeholder="Attribute" value={config.attribute} onChange={(e) => onEncryptionChange(config.id, "attribute", e.target.value)} />
                <Select value={config.algorithm} onValueChange={(v) => onEncryptionChange(config.id, "algorithm", v)}>
                  <SelectTrigger><SelectValue placeholder="Algorithm" /></SelectTrigger>
                  <SelectContent>{ENCRYPTION_ALGORITHMS.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}</SelectContent>
                </Select>
                <Button variant="ghost" size="icon" onClick={() => removeEncryptionRow(config.id)}><Trash2 className="h-4 w-4" /></Button>
              </div>
            ))}
            <Button variant="outline" size="sm" onClick={addEncryptionRow} className="w-full"><Plus className="h-4 w-4 mr-2" />Add Row</Button>
          </div>
        )}
      </div>

      <Button onClick={onGenerate} className="w-full h-12 text-lg font-bold"><Zap className="h-5 w-5 mr-2" />Generate Data</Button>
    </div>
  );
}
