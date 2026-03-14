// ui/stores/schema-store.ts

import { create } from 'zustand';

export interface SchemaSpec {
  id: string;
  name: string;
  description?: string;
  raw_content?: string;
  canonical_schema: any;
  created_at?: string;
}

interface SchemaState {
  currentSchema: SchemaSpec | null;
  schemas: SchemaSpec[];
  setSchemas: (schemas: SchemaSpec[]) => void;
  setCurrentSchema: (schema: SchemaSpec | null) => void;
  updateSchema: (id: string, updates: Partial<SchemaSpec>) => void;
}

export const useSchemaStore = create<SchemaState>((set) => ({
  currentSchema: null,
  schemas: [],
  setSchemas: (schemas) => set({ schemas }),
  setCurrentSchema: (schema) => set({ currentSchema: schema }),
  updateSchema: (id, updates) => 
    set((state) => ({
      schemas: state.schemas.map((s) => (s.id === id ? { ...s, ...updates } : s)),
      currentSchema: state.currentSchema?.id === id ? { ...state.currentSchema, ...updates } : state.currentSchema
    })),
}));
