"use client"

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2, Database } from "lucide-react";
import { SchemaBuilderTable } from "./types";

interface SchemaBuilderProps {
  tables: SchemaBuilderTable[];
  onAddTable: () => void;
  onRemoveTable: (id: string) => void;
  onUpdateTable: (id: string, name: string) => void;
  onAddColumn: (tid: string) => void;
  onUpdateColumn: (tid: string, cid: string, field: string, val: string) => void;
  onRemoveColumn: (tid: string, cid: string) => void;
  onBuild: () => void;
  isUploading: boolean;
}

export function SchemaBuilder({
  tables, onAddTable, onRemoveTable, onUpdateTable,
  onAddColumn, onUpdateColumn, onRemoveColumn, onBuild, isUploading
}: SchemaBuilderProps) {
  return (
    <div className="bg-card p-6 rounded-lg border space-y-6">
      <div className="flex items-center justify-between"><h2 className="text-xl font-semibold flex items-center gap-2"><Database className="h-5 w-5" />Schema Builder</h2><Button onClick={onAddTable} variant="outline" size="sm"><Plus className="h-4 w-4 mr-2" />Add Table</Button></div>
      <div className="space-y-4">
        {tables.map(table => (
          <div key={table.id} className="p-4 border rounded-lg bg-secondary/10 space-y-4">
            <div className="flex gap-2"><Input value={table.name} onChange={(e) => onUpdateTable(table.id, e.target.value)} className="font-bold" /><Button variant="ghost" size="icon" onClick={() => onRemoveTable(table.id)}><Trash2 className="h-4 w-4" /></Button></div>
            <div className="pl-4 space-y-2">
              {table.columns.map(col => (
                <div key={col.id} className="flex gap-2 items-center text-sm">
                  <Input value={col.name} onChange={(e) => onUpdateColumn(table.id, col.id, "name", e.target.value)} className="h-8" />
                  <Select value={col.type} onValueChange={(v) => onUpdateColumn(table.id, col.id, "type", v)}>
                    <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                    <SelectContent><SelectItem value="uuid">UUID</SelectItem><SelectItem value="string">String</SelectItem><SelectItem value="integer">Integer</SelectItem></SelectContent>
                  </Select>
                  <Button variant="ghost" size="icon" onClick={() => onRemoveColumn(table.id, col.id)} className="h-8 w-8"><Trash2 className="h-3 w-3" /></Button>
                </div>
              ))}
              <Button onClick={() => onAddColumn(table.id)} variant="ghost" size="sm" className="w-full text-xs h-8"><Plus className="h-3 w-3 mr-1" />Add Column</Button>
            </div>
          </div>
        ))}
      </div>
      <Button onClick={onBuild} disabled={isUploading} className="w-full">{isUploading ? "Building..." : "Build Schema"}</Button>
    </div>
  );
}
