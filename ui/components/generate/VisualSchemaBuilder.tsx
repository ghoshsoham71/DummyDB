"use client"

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, Trash2, Database, Table as TableIcon, Layers } from "lucide-react";
import { Table, TableAttribute } from "@/lib/api";

export function VisualSchemaBuilder({ 
  onSave, 
  initialSchema 
}: { 
  onSave: (schema: any) => void,
  initialSchema?: any
}) {
  const [tables, setTables] = useState<Table[]>([]);

  useEffect(() => {
    if (initialSchema) {
      if (initialSchema.databases && initialSchema.databases.length > 0) {
        setTables(initialSchema.databases[0].tables || []);
      } else if (Array.isArray(initialSchema.tables)) {
        setTables(initialSchema.tables);
      }
    }
  }, [initialSchema]);

  const addTable = () => {
    setTables([...tables, { name: `Table_${tables.length + 1}`, attributes: [] }]);
  };

  const addAttribute = (tableIndex: number) => {
    const newTables = [...tables];
    newTables[tableIndex].attributes.push({ name: "id", type: "INTEGER", constraints: ["PRIMARY KEY"] });
    setTables(newTables);
  };

  const removeTable = (index: number) => {
    setTables(tables.filter((_, i) => i !== index));
  };

  const updateTableName = (index: number, name: string) => {
    const newTables = [...tables];
    newTables[index].name = name;
    setTables(newTables);
  };

  const handleSave = () => {
    onSave({ databases: [{ name: "burst_db", tables }] });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <Database className="w-5 h-5" />
          BurstDB Studio: Visual Builder
        </h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={addTable}>
            <Plus className="w-4 h-4 mr-2" /> Add Table
          </Button>
          <Button size="sm" onClick={handleSave} disabled={tables.length === 0}>
            Save Schema
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tables.map((table, tIdx) => (
          <Card key={tIdx} className="border-2 border-primary/10 hover:border-primary/30 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <TableIcon className="w-4 h-4 text-primary" />
                <Input 
                  value={table.name} 
                  onChange={(e) => updateTableName(tIdx, e.target.value)}
                  className="h-7 w-32 text-xs font-bold bg-transparent border-none focus-visible:ring-0 p-0"
                />
              </CardTitle>
              <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={() => removeTable(tIdx)}>
                <Trash2 className="w-3 h-3" />
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {table.attributes.map((attr, aIdx) => (
                  <div key={aIdx} className="flex gap-2 items-center bg-muted/50 p-1 rounded text-[10px]">
                    <span className="font-mono flex-1">{attr.name}</span>
                    <Badge variant="outline" className="text-[8px] px-1 h-4">{attr.type}</Badge>
                  </div>
                ))}
                <Button variant="ghost" size="sm" className="w-full h-7 text-[10px] mt-2 border-dashed border" onClick={() => addAttribute(tIdx)}>
                  <Plus className="w-3 h-3 mr-1" /> Add Attribute
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
        {tables.length === 0 && (
          <div className="col-span-full py-20 flex flex-col items-center justify-center border-2 border-dashed rounded-xl opacity-50">
            <Layers className="w-10 h-10 mb-4" />
            <p className="text-sm">Start by adding your first database table</p>
          </div>
        )}
      </div>
    </div>
  );
}


