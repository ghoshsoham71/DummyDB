import { Database as DatabaseType } from "@/lib/api";

export interface ApiResponse {
  schema_id?: string;
  databases: DatabaseType[];
  source?: string;
  connection?: { uri?: string; http_browser?: string };
  statistics?: Record<string, unknown>;
}

export interface SchemaBuilderColumn {
  id: string;
  name: string;
  type: string;
  nullable: boolean;
  isPrimary: boolean;
  isUnique: boolean;
}

export interface SchemaBuilderTable {
  id: string;
  name: string;
  columns: SchemaBuilderColumn[];
}

export interface EncryptionConfig {
  id: string;
  tableName: string;
  attribute: string;
  algorithm: string;
}

export const ENCRYPTION_ALGORITHMS = [
  "AES-256", "AES-128", "RSA-2048", "RSA-4096",
  "ChaCha20", "Twofish", "Blowfish", "DES", "3DES"
];


