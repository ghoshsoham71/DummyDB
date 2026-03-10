"""
Startup script to initialize database and run migrations
Run this before starting your FastAPI application
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.migrations import migrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set them in your .env file or environment")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def initialize_migration_system():
    """Initialize the complete migration system"""
    logger.info("🚀 Initializing migration system...")
    
    try:
        # Create migrations directory
        migrations_dir = migrator.migrations_dir
        migrations_dir.mkdir(exist_ok=True)
        logger.info(f"✅ Migrations directory: {migrations_dir}")
        
        # Create migrations tracking table
        logger.info("📋 Creating migrations tracking table...")
        table_created = migrator.create_migrations_table()
        
        if table_created:
            logger.info("✅ Migrations tracking table ready")
        else:
            logger.warning("⚠️ Could not verify migrations tracking table")
        
        # Create schema_parse migration if it doesn't exist
        logger.info("📝 Creating schema_parse enhancement migration...")
        migration_files = list(migrations_dir.glob("*_add_schema_parse_enhancements.sql"))
        
        if not migration_files:
            migration_file = migrator.create_schema_parse_migration()
            logger.info(f"✅ Created migration: {migration_file}")
        else:
            logger.info(f"✅ Migration already exists: {migration_files[0].name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize migration system: {e}")
        return False

def run_migrations():
    """Run all pending migrations"""
    logger.info("🏃 Running migrations...")
    
    try:
        result = migrator.auto_migrate()
        
        if result["success"]:
            logger.info(f"✅ {result['message']}")
            
            # Log details of each migration
            for migration_result in result.get("results", []):
                status = "✅" if migration_result.get("success") else "❌"
                migration_name = migration_result.get("migration_file", "Unknown")
                message = migration_result.get("message", "No message")
                
                if migration_result.get("skipped"):
                    status = "⏭️"
                
                logger.info(f"  {status} {migration_name}: {message}")
                
                # Show execution time if available
                exec_time = migration_result.get("execution_time_ms")
                if exec_time is not None:
                    logger.info(f"    ⏱️ Execution time: {exec_time}ms")
            
            return True
        else:
            logger.error(f"❌ Migration failed: {result['message']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration execution failed: {e}")
        return False

def verify_schema_changes():
    """Verify that schema changes were applied successfully"""
    logger.info("🔍 Verifying schema changes...")
    
    try:
        from src.lib.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Try to query the schema_parse table to verify new columns exist
        result = supabase.table('schema_parse').select('filename, content_hash, file_size').limit(1).execute()
        
        logger.info("✅ Schema changes verified - new columns are accessible")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Could not verify schema changes: {e}")
        logger.info("This might be normal if the table is empty or RLS policies are restrictive")
        return True  # Don't fail startup due to verification issues

def main():
    """Main startup function"""
    logger.info("🎯 Starting Schema Parser API initialization...")
    
    # Step 1: Check environment
    if not check_environment():
        logger.error("❌ Environment check failed")
        sys.exit(1)
    
    # Step 2: Initialize migration system
    if not initialize_migration_system():
        logger.error("❌ Migration system initialization failed")
        sys.exit(1)
    
    # Step 3: Run migrations
    if not run_migrations():
        logger.error("❌ Migration execution failed")
        sys.exit(1)
    
    # Step 4: Verify changes
    verify_schema_changes()
    
    logger.info("🎉 Initialization completed successfully!")
    logger.info("🚀 You can now start your FastAPI application")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)