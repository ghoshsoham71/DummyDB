import logging
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.utils.storage.helpers import create_archive, get_file_info

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
        self._ensure_directories()
    
    def _ensure_directories(self):
        for d in [self.base_dir, self.schemas_dir, self.seed_data_dir, self.synthetic_data_dir, self.reports_dir, self.temp_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def save_schema(self, data: Dict[str, Any], schema_id: str, filename: str) -> str:
        path = self.schemas_dir / f"{schema_id}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({"schema_id": schema_id, "original_filename": filename, "created_at": datetime.now().isoformat(), "schema": data}, f, indent=2)
        return str(path)
    
    def load_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        path = self.schemas_dir / f"{schema_id}.json"
        if not path.exists(): return None
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    
    def save_csv_data(self, data: Dict[str, Any], directory: str, prefix: str = "") -> List[str]:
        import pandas as pd
        saved, target = [], self.base_dir / directory
        target.mkdir(parents=True, exist_ok=True)
        for name, df in data.items():
            if isinstance(df, pd.DataFrame):
                path = target / f"{prefix}{name}.csv"
                df.to_csv(path, index=False)
                saved.append(str(path))
        return saved
    
    def load_csv_data(self, directory: str) -> Dict[str, Any]:
        import pandas as pd
        data, target = {}, self.base_dir / directory
        if not target.exists(): return data
        for f in target.glob("*.csv"): data[f.stem] = pd.read_csv(f)
        return data
    
    def create_temp_file(self, content: str, suffix: str = ".tmp") -> str:
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, dir=self.temp_dir, delete=False) as f:
            f.write(content)
            return f.name
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        now, count = datetime.now(), 0
        for f in self.temp_dir.glob("*"):
            if f.is_file() and (now - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() > (max_age_hours * 3600):
                f.unlink(); count += 1
        return count
    
    def create_archive(self, files: List[str], name: str) -> str:
        return create_archive(files, self.reports_dir / f"{name}.zip")
    
    def get_file_info(self, path: str) -> Dict[str, Any]: return get_file_info(path)
    
    def delete_file(self, path: str) -> bool:
        p = Path(path)
        if p.exists() and p.is_file(): p.unlink(); return True
        return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        stats = {"total_size": 0, "directories": {}}
        dirs = [("schemas", self.schemas_dir), ("seed_data", self.seed_data_dir), ("synthetic_data", self.synthetic_data_dir), ("reports", self.reports_dir), ("temp", self.temp_dir)]
        for name, path in dirs:
            if path.exists():
                size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                stats["directories"][name] = {"size": size, "files": sum(1 for f in path.rglob("*") if f.is_file())}
                stats["total_size"] += size
        return stats
    
    def list_files(self, directory: str, pattern: str = "*", recursive: bool = False) -> List[Dict[str, Any]]:
        target = self.base_dir / directory
        if not target.exists(): return []
        glob = target.rglob(pattern) if recursive else target.glob(pattern)
        return sorted([{"path": str(f.relative_to(self.base_dir)), **self.get_file_info(str(f))} for f in glob if f.is_file()], key=lambda x: x.get("modified", ""), reverse=True)

file_manager = FileManager()