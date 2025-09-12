import os
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import tempfile
import zipfile
import json

logger = logging.getLogger(__name__)

class FileManager:
    """Centralized file management for synthetic data generation system"""
    
    def __init__(self):
        self.base_dir = Path("./data")
        self.schemas_dir = self.base_dir / "schemas"
        self.seed_data_dir = self.base_dir / "seed_data"
        self.synthetic_data_dir = self.base_dir / "synthetic_data"
        self.reports_dir = self.base_dir / "reports"
        self.temp_dir = self.base_dir / "temp"
        
        # Create directories
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.base_dir,
            self.schemas_dir,
            self.seed_data_dir,
            self.synthetic_data_dir,
            self.reports_dir,
            self.temp_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def save_schema(self, schema_data: Dict[str, Any], 
                   schema_id: str, 
                   filename: str) -> str:
        """Save schema data to JSON file"""
        try:
            schema_file = self.schemas_dir / f"{schema_id}.json"
            
            with open(schema_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "schema_id": schema_id,
                    "original_filename": filename,
                    "created_at": datetime.now().isoformat(),
                    "schema": schema_data
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Schema saved: {schema_file}")
            return str(schema_file)
            
        except Exception as e:
            logger.error(f"Failed to save schema {schema_id}: {e}")
            raise
    
    def load_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        """Load schema data from JSON file"""
        try:
            schema_file = self.schemas_dir / f"{schema_id}.json"
            
            if not schema_file.exists():
                logger.warning(f"Schema file not found: {schema_file}")
                return None
            
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            
            logger.debug(f"Schema loaded: {schema_id}")
            return schema_data
            
        except Exception as e:
            logger.error(f"Failed to load schema {schema_id}: {e}")
            return None
    
    def save_csv_data(self, data: Dict[str, Any], 
                     directory: str, 
                     prefix: str = "") -> List[str]:
        """Save dataframes as CSV files"""
        import pandas as pd
        
        saved_files = []
        target_dir = self.base_dir / directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            for table_name, df in data.items():
                if isinstance(df, pd.DataFrame):
                    filename = f"{prefix}{table_name}.csv"
                    file_path = target_dir / filename
                    
                    df.to_csv(file_path, index=False)
                    saved_files.append(str(file_path))
                    logger.debug(f"CSV saved: {file_path} ({len(df)} rows)")
            
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save CSV data: {e}")
            raise
    
    def load_csv_data(self, directory: str) -> Dict[str, Any]:
        """Load all CSV files from directory"""
        import pandas as pd
        
        data = {}
        target_dir = self.base_dir / directory
        
        if not target_dir.exists():
            logger.warning(f"Directory not found: {target_dir}")
            return data
        
        try:
            for csv_file in target_dir.glob("*.csv"):
                table_name = csv_file.stem
                df = pd.read_csv(csv_file)
                data[table_name] = df
                logger.debug(f"CSV loaded: {csv_file} ({len(df)} rows)")
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to load CSV data from {directory}: {e}")
            raise
    
    def create_temp_file(self, content: str, suffix: str = ".tmp") -> str:
        """Create temporary file with content"""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix=suffix, 
                dir=self.temp_dir, 
                delete=False
            ) as f:
                f.write(content)
                temp_path = f.name
            
            logger.debug(f"Temporary file created: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to create temporary file: {e}")
            raise
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up old temporary files"""
        try:
            current_time = datetime.now()
            cleaned_count = 0
            
            for temp_file in self.temp_dir.glob("*"):
                if temp_file.is_file():
                    file_age = current_time - datetime.fromtimestamp(temp_file.stat().st_mtime)
                    
                    if file_age.total_seconds() > (max_age_hours * 3600):
                        temp_file.unlink()
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} temporary files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup temporary files: {e}")
            return 0
    
    def create_archive(self, files: List[str], archive_name: str) -> str:
        """Create ZIP archive of files"""
        try:
            archive_path = self.reports_dir / f"{archive_name}.zip"
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    if os.path.exists(file_path):
                        # Add file with relative path
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
                        logger.debug(f"Added to archive: {file_path}")
            
            logger.info(f"Archive created: {archive_path}")
            return str(archive_path)
            
        except Exception as e:
            logger.error(f"Failed to create archive: {e}")
            raise
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {"exists": False}
            
            stat = path.stat()
            
            # Calculate file hash
            with open(path, 'rb') as f:
                content = f.read()
                file_hash = hashlib.md5(content).hexdigest()
            
            return {
                "exists": True,
                "name": path.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "hash": file_hash,
                "extension": path.suffix
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return {"exists": False, "error": str(e)}
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file safely"""
        try:
            path = Path(file_path)
            
            if path.exists() and path.is_file():
                path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found or not a file: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    def get_directory_size(self, directory: str) -> int:
        """Get total size of directory"""
        try:
            total_size = 0
            target_dir = self.base_dir / directory
            
            if target_dir.exists():
                for file_path in target_dir.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
            
            return total_size
            
        except Exception as e:
            logger.error(f"Failed to calculate directory size for {directory}: {e}")
            return 0
    
    def list_files(self, directory: str, 
                  pattern: str = "*",
                  recursive: bool = False) -> List[Dict[str, Any]]:
        """List files in directory with metadata"""
        try:
            files = []
            target_dir = self.base_dir / directory
            
            if not target_dir.exists():
                return files
            
            glob_pattern = target_dir.rglob(pattern) if recursive else target_dir.glob(pattern)
            
            for file_path in glob_pattern:
                if file_path.is_file():
                    file_info = self.get_file_info(str(file_path))
                    file_info["path"] = str(file_path.relative_to(self.base_dir))
                    files.append(file_info)
            
            return sorted(files, key=lambda x: x.get("modified", ""), reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list files in {directory}: {e}")
            return []
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats = {
                "total_size": 0,
                "directories": {}
            }
            
            directories = [
                ("schemas", self.schemas_dir),
                ("seed_data", self.seed_data_dir),
                ("synthetic_data", self.synthetic_data_dir),
                ("reports", self.reports_dir),
                ("temp", self.temp_dir)
            ]
            
            for dir_name, dir_path in directories:
                if dir_path.exists():
                    dir_size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
                    file_count = sum(1 for f in dir_path.rglob("*") if f.is_file())
                    
                    stats["directories"][dir_name] = {
                        "size": dir_size,
                        "files": file_count,
                        "path": str(dir_path)
                    }
                    stats["total_size"] += dir_size
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"error": str(e)}

# Global file manager instance
file_manager = FileManager()