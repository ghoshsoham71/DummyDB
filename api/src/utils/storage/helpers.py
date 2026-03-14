import os
import hashlib
import zipfile
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def create_archive(files: List[str], archive_path: Path) -> str:
    """Create ZIP archive of files"""
    try:
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in files:
                if os.path.exists(f):
                    zipf.write(f, os.path.basename(f))
        return str(archive_path)
    except Exception as e:
        logger.error(f"Failed to create archive: {e}")
        raise

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get file information"""
    path = Path(file_path)
    if not path.exists(): return {"exists": False}
    stat = path.stat()
    with open(path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    return {
        "exists": True, "name": path.name, "size": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "hash": file_hash, "extension": path.suffix
    }
