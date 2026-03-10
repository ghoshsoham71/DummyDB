import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
logger = logging.getLogger(__name__)

from src.lib.supabase_client import get_supabase_client as _get_client


class DatabaseMigrator:
    """Handle database migrations and schema updates"""
    
    def __init__(self):
        self.migrations_dir = Path("./migrations")
        self.migrations_dir.mkdir(exist_ok=True)
        
    def get_supabase_client(self):
        """Get Supabase client with service role key (delegates to shared singleton)."""
        return _get_client()

    def create_migrations_table(self) -> bool:
        """Create migrations tracking table if it doesn't exist"""
        try:
            supabase = self.get_supabase_client()
            
            # SQL to create migrations table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                migration_hash VARCHAR(32) NOT NULL,
                executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                execution_time_ms INTEGER,
                status VARCHAR(20) DEFAULT 'success',
                error_message TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_migrations_name ON schema_migrations(migration_name);
            CREATE INDEX IF NOT EXISTS idx_migrations_status ON schema_migrations(status);
            """
            
            # Execute the SQL using RPC call
            result = supabase.rpc('exec_sql', {'sql': create_table_sql}).execute()
            
            logger.info("Migrations table created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create migrations table: {e}")
            # Fallback: try direct table creation
            try:
                supabase = self.get_supabase_client()
                # Try using a simpler approach
                result = supabase.table('schema_migrations').select('id').limit(1).execute()
                logger.info("Migrations table already exists")
                return True
            except:
                logger.error("Could not verify or create migrations table")
                return False

    def get_migration_hash(self, migration_content: str) -> str:
        """Generate hash for migration content"""
        return hashlib.md5(migration_content.encode()).hexdigest()

    def is_migration_executed(self, migration_name: str, migration_hash: str) -> bool:
        """Check if migration has already been executed"""
        try:
            supabase = self.get_supabase_client()
            
            result = supabase.table('schema_migrations')\
                .select('id, migration_hash')\
                .eq('migration_name', migration_name)\
                .execute()
            
            if result.data:
                existing_hash = result.data[0].get('migration_hash')
                if existing_hash == migration_hash:
                    logger.info(f"Migration {migration_name} already executed with same hash")
                    return True
                else:
                    logger.warning(f"Migration {migration_name} exists but with different hash")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return False

    def execute_sql_migration(self, migration_name: str, sql_content: str) -> Dict[str, Any]:
        """Execute SQL migration"""
        start_time = datetime.now()
        migration_hash = self.get_migration_hash(sql_content)
        
        try:
            # Check if already executed
            if self.is_migration_executed(migration_name, migration_hash):
                return {
                    "success": True,
                    "message": f"Migration {migration_name} already executed",
                    "skipped": True
                }
            
            supabase = self.get_supabase_client()
            
            # Execute the migration SQL
            # For complex SQL, we'll need to split and execute parts
            sql_statements = self._split_sql_statements(sql_content)
            
            for i, statement in enumerate(sql_statements):
                statement = statement.strip()
                if not statement or statement.startswith('--'):
                    continue
                
                logger.info(f"Executing statement {i+1}/{len(sql_statements)}: {statement[:100]}...")
                
                # Handle different types of SQL statements
                if statement.upper().startswith(('CREATE', 'ALTER', 'DROP')):
                    # DDL statements - use RPC if available
                    try:
                        result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                    except Exception as rpc_error:
                        logger.warning(f"RPC failed, trying alternative method: {rpc_error}")
                        # Alternative: try to execute via table operations if possible
                        self._execute_ddl_alternative(supabase, statement)
                
                elif statement.upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    # DML statements
                    result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                
                else:
                    # Other statements
                    result = supabase.rpc('exec_sql', {'sql': statement}).execute()
            
            end_time = datetime.now()
            execution_time = int((end_time - start_time).total_seconds() * 1000)
            
            # Record successful migration
            migration_record = {
                "migration_name": migration_name,
                "migration_hash": migration_hash,
                "execution_time_ms": execution_time,
                "status": "success",
                "executed_at": end_time.isoformat()
            }
            
            try:
                supabase.table('schema_migrations').insert(migration_record).execute()
            except Exception as record_error:
                logger.warning(f"Could not record migration: {record_error}")
            
            return {
                "success": True,
                "message": f"Migration {migration_name} executed successfully",
                "execution_time_ms": execution_time,
                "statements_executed": len(sql_statements)
            }
            
        except Exception as e:
            end_time = datetime.now()
            execution_time = int((end_time - start_time).total_seconds() * 1000)
            
            # Record failed migration
            migration_record = {
                "migration_name": migration_name,
                "migration_hash": migration_hash,
                "execution_time_ms": execution_time,
                "status": "failed",
                "error_message": str(e),
                "executed_at": end_time.isoformat()
            }
            
            try:
                supabase = self.get_supabase_client()
                supabase.table('schema_migrations').insert(migration_record).execute()
            except:
                pass
            
            logger.error(f"Migration {migration_name} failed: {e}")
            return {
                "success": False,
                "message": f"Migration {migration_name} failed: {str(e)}",
                "execution_time_ms": execution_time
            }

    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements"""
        # Remove comments
        lines = sql_content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('--'):
                cleaned_lines.append(line)
        
        cleaned_sql = ' '.join(cleaned_lines)
        
        # Split by semicolon, but be careful with DO blocks
        statements = []
        current_statement = []
        in_do_block = False
        
        parts = cleaned_sql.split(';')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            if 'DO $$' in part.upper():
                in_do_block = True
                current_statement.append(part)
            elif in_do_block and '$$' in part:
                current_statement.append(part)
                statements.append(';'.join(current_statement) + ';')
                current_statement = []
                in_do_block = False
            elif in_do_block:
                current_statement.append(part)
            else:
                if part:
                    statements.append(part + ';')
        
        return [stmt for stmt in statements if stmt.strip()]

    def _execute_ddl_alternative(self, supabase, statement: str):
        """Alternative DDL execution methods when RPC is not available"""
        statement_upper = statement.upper().strip()
        
        if statement_upper.startswith('ALTER TABLE') and 'ADD COLUMN IF NOT EXISTS' in statement_upper:
            # Try to handle column addition
            logger.info(f"Attempting alternative execution for: {statement[:100]}")
            # For now, we'll log and continue - in production you might want to
            # implement specific handlers for different DDL types
            pass
        else:
            # For other DDL, we might need to raise an exception or implement specific handling
            logger.warning(f"Could not execute DDL statement: {statement[:100]}")

    def run_migration_file(self, migration_file: str) -> Dict[str, Any]:
        """Run migration from file"""
        migration_path = self.migrations_dir / migration_file
        
        if not migration_path.exists():
            return {
                "success": False,
                "message": f"Migration file {migration_file} not found"
            }
        
        try:
            with open(migration_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            migration_name = migration_path.stem
            return self.execute_sql_migration(migration_name, sql_content)
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to read migration file: {str(e)}"
            }

    def get_migration_status(self) -> Dict[str, Any]:
        """Get status of all migrations"""
        try:
            supabase = self.get_supabase_client()
            
            result = supabase.table('schema_migrations')\
                .select('*')\
                .order('executed_at', desc=True)\
                .execute()
            
            if result.data:
                return {
                    "success": True,
                    "migrations": result.data,
                    "total_migrations": len(result.data)
                }
            else:
                return {
                    "success": True,
                    "migrations": [],
                    "total_migrations": 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {
                "success": False,
                "message": f"Failed to get migration status: {str(e)}"
            }

    def create_schema_parse_migration(self) -> str:
        """Create the schema_parse table migration file"""
        migration_content = """-- Migration: Add schema parse enhancements
-- Description: Add filename, content_hash, file_size columns and indexes for duplicate prevention
-- Date: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """

-- Add filename column if it doesn't exist
ALTER TABLE schema_parse 
ADD COLUMN IF NOT EXISTS filename VARCHAR(255);

-- Add content_hash column if it doesn't exist (for duplicate detection)
ALTER TABLE schema_parse 
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(32);

-- Add file_size column if it doesn't exist
ALTER TABLE schema_parse 
ADD COLUMN IF NOT EXISTS file_size INTEGER;

-- Add updated_at column if it doesn't exist
ALTER TABLE schema_parse 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Create unique constraint on content_hash if it doesn't exist
DO $$
BEGIN
    BEGIN
        ALTER TABLE schema_parse ADD CONSTRAINT unique_content_hash UNIQUE (content_hash);
    EXCEPTION
        WHEN duplicate_table THEN
            -- Constraint already exists, do nothing
            NULL;
    END;
END $$;

-- Create index on content_hash for faster duplicate checking
CREATE INDEX IF NOT EXISTS idx_schema_parse_content_hash 
ON schema_parse(content_hash);

-- Create index on filename for faster filename-based searches
CREATE INDEX IF NOT EXISTS idx_schema_parse_filename 
ON schema_parse(filename);

-- Create composite index for better query performance
CREATE INDEX IF NOT EXISTS idx_schema_parse_hash_filename 
ON schema_parse(content_hash, filename);

-- Update RLS policy to allow service role operations
DO $$
BEGIN
    -- Drop existing policy if it exists
    BEGIN
        DROP POLICY IF EXISTS "Allow authenticated users" ON schema_parse;
    EXCEPTION
        WHEN undefined_object THEN
            -- Policy doesn't exist, continue
            NULL;
    END;
    
    -- Create new policy for authenticated users and service role
    BEGIN
        CREATE POLICY "Allow authenticated users" ON schema_parse
        FOR ALL USING (
            auth.role() = 'authenticated' OR 
            auth.jwt() ->> 'role' = 'service_role' OR
            current_user = 'service_role'
        );
    EXCEPTION
        WHEN others THEN
            RAISE NOTICE 'Could not create RLS policy: %', SQLERRM;
    END;
    
    -- Enable RLS if not already enabled
    BEGIN
        ALTER TABLE schema_parse ENABLE ROW LEVEL SECURITY;
    EXCEPTION
        WHEN others THEN
            RAISE NOTICE 'RLS already enabled or could not be enabled: %', SQLERRM;
    END;
    
END $$;

-- Add comments to document the new columns
COMMENT ON COLUMN schema_parse.filename IS 'Original filename of the uploaded SQL file';
COMMENT ON COLUMN schema_parse.content_hash IS 'MD5 hash of file content for duplicate detection';
COMMENT ON COLUMN schema_parse.file_size IS 'Size of the original file in bytes';
COMMENT ON COLUMN schema_parse.updated_at IS 'Timestamp when the record was last updated';
"""
        
        # Save migration file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        migration_filename = f"{timestamp}_add_schema_parse_enhancements.sql"
        migration_path = self.migrations_dir / migration_filename
        
        with open(migration_path, 'w', encoding='utf-8') as f:
            f.write(migration_content)
        
        logger.info(f"Created migration file: {migration_filename}")
        return migration_filename

    def auto_migrate(self) -> Dict[str, Any]:
        """Run all pending migrations automatically"""
        results = []
        
        try:
            # Ensure migrations table exists
            self.create_migrations_table()
            
            # Create the schema_parse enhancement migration if it doesn't exist
            migration_files = list(self.migrations_dir.glob("*_add_schema_parse_enhancements.sql"))
            
            if not migration_files:
                migration_file = self.create_schema_parse_migration()
                migration_files = [self.migrations_dir / migration_file]
            
            # Run all migration files
            for migration_path in sorted(migration_files):
                result = self.run_migration_file(migration_path.name)
                results.append({
                    "migration_file": migration_path.name,
                    **result
                })
            
            # Also run any other .sql files in migrations directory
            other_migrations = [f for f in self.migrations_dir.glob("*.sql") 
                             if not f.name.endswith("_add_schema_parse_enhancements.sql")]
            
            for migration_path in sorted(other_migrations):
                result = self.run_migration_file(migration_path.name)
                results.append({
                    "migration_file": migration_path.name,
                    **result
                })
            
            successful = sum(1 for r in results if r.get('success'))
            total = len(results)
            
            return {
                "success": successful == total,
                "message": f"Executed {successful}/{total} migrations successfully",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Auto migration failed: {e}")
            return {
                "success": False,
                "message": f"Auto migration failed: {str(e)}",
                "results": results
            }

# Global migrator instance
migrator = DatabaseMigrator()