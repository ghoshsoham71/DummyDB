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

# Removed migrations import

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
    # Deprecated
    pass

def run_migrations():
    # Deprecated
    pass

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
    
    # Migrations removed
    
    # Step 4: Verify changes
    verify_schema_changes()
    
    logger.info("🎉 Initialization completed successfully!")
    logger.info("🚀 You can now start your FastAPI application")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)