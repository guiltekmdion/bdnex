# BDneX Architecture - Phase 1 Implementation Guide

## Database Schema Design

### Core Tables

```sql
-- Fichiers traités
CREATE TABLE processed_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL,           -- SHA256
    file_size INTEGER,                  -- bytes
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP,
    
    -- Résultats de recherche
    bdgest_id INTEGER,
    bdgest_url TEXT,
    confidence_score REAL,              -- 0.0 to 1.0
    
    -- Métadonnées trouvées
    title TEXT,
    series TEXT,
    volume INTEGER,
    editor TEXT,
    year INTEGER,
    isbn TEXT,
    pages INTEGER,
    
    -- État du traitement
    status TEXT CHECK(status IN ('success', 'manual', 'skipped', 'failed')),
    error_msg TEXT,
    
    -- ComicInfo.xml
    has_metadata BOOLEAN DEFAULT FALSE,
    metadata_hash TEXT,                -- Track metadata changes
    
    -- Session
    session_id INTEGER,
    processing_time_ms INTEGER,
    
    FOREIGN KEY (session_id) REFERENCES processing_sessions(id)
);

-- Cache des albums Bédéthèque
CREATE TABLE bdgest_albums (
    id INTEGER PRIMARY KEY,           -- bdgest album ID
    title TEXT NOT NULL,
    series TEXT,
    volume INTEGER,
    editor TEXT,
    year INTEGER,
    isbn TEXT,
    pages INTEGER,
    cover_url TEXT,
    url TEXT UNIQUE,
    
    -- Cache control
    cached_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cache_valid_until TIMESTAMP,      -- TTL 7 jours
    
    -- Metadata JSON for complex fields
    metadata JSON
);

-- Sessions de traitement batch
CREATE TABLE processing_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    
    -- Configuration
    directory TEXT NOT NULL,
    pattern TEXT DEFAULT '*.cbz|*.cbr',
    batch_mode BOOLEAN DEFAULT TRUE,
    strict_mode BOOLEAN DEFAULT FALSE,
    num_workers INTEGER DEFAULT 4,
    
    -- Résultats
    total_files INTEGER DEFAULT 0,
    files_processed INTEGER DEFAULT 0,
    files_successful INTEGER DEFAULT 0,
    files_failed INTEGER DEFAULT 0,
    files_skipped INTEGER DEFAULT 0,
    
    -- État
    status TEXT CHECK(status IN ('running', 'paused', 'completed', 'failed')),
    
    -- Logs
    log_file_path TEXT,
    json_log_path TEXT,
    csv_log_path TEXT
);

-- Historique des modifications
CREATE TABLE metadata_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    field TEXT,                        -- 'title', 'volume', etc.
    old_value TEXT,
    new_value TEXT,
    source TEXT,                       -- 'auto', 'manual', 'api'
    
    FOREIGN KEY (file_id) REFERENCES processed_files(id)
);

-- Statistiques d'utilisation
CREATE TABLE statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE DEFAULT CURRENT_DATE,
    total_files INTEGER,
    total_series INTEGER,
    total_editors INTEGER,
    avg_pages INTEGER,
    avg_processing_time_ms INTEGER
);

-- Index pour les performances
CREATE INDEX idx_file_path ON processed_files(file_path);
CREATE INDEX idx_status ON processed_files(status);
CREATE INDEX idx_session_id ON processed_files(session_id);
CREATE INDEX idx_bdgest_id ON processed_files(bdgest_id);
CREATE INDEX idx_series ON processed_files(series);
CREATE INDEX idx_editor ON processed_files(editor);
```

---

## Module Structure

### `bdnex/lib/database.py`

```python
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import json
import hashlib
from typing import Optional, List, Dict, Any

class BDneXDB:
    """Main database interface."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database (default: ~/.local/share/bdnex/bdnex.db)
        """
        if db_path is None:
            from bdnex.lib.utils import bdnex_config
            config = bdnex_config()
            db_dir = Path(config['database']['path']).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / 'bdnex.db')
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        """Create tables if they don't exist."""
        with open(Path(__file__).parent.parent / 'conf' / 'schema.sql') as f:
            self.conn.executescript(f.read())
    
    def is_processed(self, file_path: str, force_check: bool = False) -> bool:
        """Check if file has been processed before."""
        cursor = self.conn.cursor()
        row = cursor.execute(
            "SELECT id FROM processed_files WHERE file_path = ?",
            (file_path,)
        ).fetchone()
        return row is not None
    
    def get_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def record_processing(
        self,
        file_path: str,
        session_id: int,
        result: Dict[str, Any],
    ) -> int:
        """Record a processed file."""
        file_hash = self.get_file_hash(file_path)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO processed_files (
                file_path, file_hash, file_size,
                bdgest_id, bdgest_url, title, series, volume,
                editor, year, isbn, pages,
                confidence_score, status, error_msg,
                session_id, processing_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_path,
            file_hash,
            Path(file_path).stat().st_size,
            result.get('bdgest_id'),
            result.get('bdgest_url'),
            result.get('title'),
            result.get('series'),
            result.get('volume'),
            result.get('editor'),
            result.get('year'),
            result.get('isbn'),
            result.get('pages'),
            result.get('score'),
            result.get('status', 'unknown'),
            result.get('error'),
            session_id,
            result.get('processing_time_ms', 0),
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def start_session(
        self,
        directory: str,
        batch_mode: bool = True,
        strict_mode: bool = False,
        num_workers: int = 4,
    ) -> int:
        """Start a new processing session."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO processing_sessions (
                directory, batch_mode, strict_mode, num_workers, status
            ) VALUES (?, ?, ?, ?, 'running')
        """, (directory, batch_mode, strict_mode, num_workers))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def update_session(
        self,
        session_id: int,
        **kwargs
    ):
        """Update session statistics."""
        allowed_fields = {
            'total_files', 'files_processed', 'files_successful',
            'files_failed', 'files_skipped', 'status'
        }
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return
        
        set_clause = ', '.join(f"{k}=?" for k in updates.keys())
        cursor = self.conn.cursor()
        cursor.execute(
            f"UPDATE processing_sessions SET {set_clause} WHERE id=?",
            list(updates.values()) + [session_id]
        )
        
        if 'status' in updates and updates['status'] == 'completed':
            cursor.execute(
                "UPDATE processing_sessions SET session_end=CURRENT_TIMESTAMP WHERE id=?",
                (session_id,)
            )
        
        self.conn.commit()
    
    def get_session_stats(self, session_id: int) -> Dict[str, Any]:
        """Get session statistics."""
        cursor = self.conn.cursor()
        row = cursor.execute(
            "SELECT * FROM processing_sessions WHERE id=?",
            (session_id,)
        ).fetchone()
        return dict(row) if row else {}
    
    def get_processed_files(
        self,
        status: Optional[str] = None,
        series: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get processed files with optional filters."""
        query = "SELECT * FROM processed_files WHERE 1=1"
        params = []
        
        if status:
            query += " AND status=?"
            params.append(status)
        
        if series:
            query += " AND series=?"
            params.append(series)
        
        query += " LIMIT ?"
        params.append(limit)
        
        cursor = self.conn.cursor()
        rows = cursor.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    
    def cache_album(self, album_data: Dict[str, Any]):
        """Cache album metadata from Bédéthèque."""
        cursor = self.conn.cursor()
        cache_valid_until = datetime.now() + timedelta(days=7)
        
        cursor.execute("""
            INSERT OR REPLACE INTO bdgest_albums (
                id, title, series, volume, editor, year, isbn, pages,
                cover_url, url, cached_date, cache_valid_until, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
        """, (
            album_data.get('id'),
            album_data.get('title'),
            album_data.get('series'),
            album_data.get('volume'),
            album_data.get('editor'),
            album_data.get('year'),
            album_data.get('isbn'),
            album_data.get('pages'),
            album_data.get('cover_url'),
            album_data.get('url'),
            cache_valid_until.isoformat(),
            json.dumps(album_data),
        ))
        
        self.conn.commit()
    
    def get_cached_album(self, bdgest_id: int) -> Optional[Dict[str, Any]]:
        """Get cached album if still valid."""
        cursor = self.conn.cursor()
        row = cursor.execute("""
            SELECT metadata FROM bdgest_albums
            WHERE id=? AND cache_valid_until > CURRENT_TIMESTAMP
        """, (bdgest_id,)).fetchone()
        
        if row:
            return json.loads(row[0])
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get library statistics."""
        cursor = self.conn.cursor()
        
        total = cursor.execute(
            "SELECT COUNT(*) FROM processed_files WHERE status='success'"
        ).fetchone()[0]
        
        series_count = cursor.execute(
            "SELECT COUNT(DISTINCT series) FROM processed_files WHERE status='success'"
        ).fetchone()[0]
        
        editors = cursor.execute(
            "SELECT COUNT(DISTINCT editor) FROM processed_files WHERE status='success'"
        ).fetchone()[0]
        
        return {
            'total_files': total,
            'total_series': series_count,
            'total_editors': editors,
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()


class SessionManager:
    """Manage processing sessions."""
    
    def __init__(self, db: BDneXDB):
        self.db = db
    
    def resume_session(self, session_id: int) -> bool:
        """Resume an interrupted session."""
        stats = self.db.get_session_stats(session_id)
        if not stats:
            return False
        
        # Get already processed files
        processed = self.db.get_processed_files(limit=10000)
        processed_paths = {f['file_path'] for f in processed}
        
        # Get remaining files
        # ... implementation
        
        return True
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        # ... implementation
        pass
```

---

## Integration Points

### 1. Modify `AdvancedBatchProcessor.process_files_parallel()`

```python
def process_files_parallel(self, file_list, ...):
    # Initialize database
    db = BDneXDB()
    session_id = db.start_session(
        directory=self.config.output_dir,
        batch_mode=True,
        num_workers=self.config.num_workers
    )
    
    for result in pool.imap_unordered(worker_func, file_list):
        # Skip if already processed (unless --force)
        if db.is_processed(result['filename']) and not self.force:
            logger.info(f"Already processed, skipping {result['filename']}")
            continue
        
        # Record in database
        file_id = db.record_processing(
            result['filename'],
            session_id,
            result
        )
        
        # Update session stats
        db.update_session(
            session_id,
            files_processed=db.get_session_stats(session_id)['files_processed'] + 1,
            files_successful=... if result['success'] else ...,
        )
```

### 2. Add CLI Arguments

```python
# bdnex/lib/utils.py args()

parser.add_argument('--resume', dest='resume', type=int, default=None,
                    help="Resume interrupted processing session")

parser.add_argument('--list-sessions', dest='list_sessions', action='store_true',
                    help="List all processing sessions")

parser.add_argument('--session-info', dest='session_info', type=int, default=None,
                    help="Show details of a processing session")

parser.add_argument('--force', dest='force', action='store_true',
                    help="Reprocess files even if already processed")

parser.add_argument('--skip-processed', dest='skip_processed', action='store_true',
                    help="Skip files that have been processed before")
```

### 3. Update Main Function

```python
def main():
    vargs = args()
    db = BDneXDB()
    
    if vargs.list_sessions:
        # Show available sessions
        sessions = db.get_session_stats()
        for session in sessions:
            logger.info(f"Session {session['id']}: {session['files_processed']}/{session['total_files']}")
        return
    
    if vargs.resume:
        # Resume specific session
        session_mgr = SessionManager(db)
        if not session_mgr.resume_session(vargs.resume):
            logger.error(f"Session {vargs.resume} not found")
            return
        return
    
    # Normal processing
    # ... rest of main()
```

---

## Testing Database Operations

```python
# test/test_database.py

import pytest
import tempfile
from bdnex.lib.database import BDneXDB

def test_database_creation():
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        db = BDneXDB(f.name)
        stats = db.get_statistics()
        assert stats['total_files'] == 0
        db.close()

def test_record_processing():
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        db = BDneXDB(f.name)
        
        session_id = db.start_session('/test/dir')
        file_id = db.record_processing(
            '/test/bd.cbz',
            session_id,
            {'title': 'Test', 'score': 0.85, 'status': 'success'}
        )
        
        files = db.get_processed_files()
        assert len(files) == 1
        assert files[0]['title'] == 'Test'
        
        db.close()

def test_cache_album():
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        db = BDneXDB(f.name)
        
        album = {
            'id': 12345,
            'title': 'Tintin',
            'series': 'Tintin',
            'volume': 1,
            'cover_url': 'http://example.com/cover.jpg'
        }
        
        db.cache_album(album)
        cached = db.get_cached_album(12345)
        assert cached['title'] == 'Tintin'
        
        db.close()
```

---

## Configuration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "BDneX Configuration",
  "type": "object",
  "properties": {
    "database": {
      "type": "object",
      "properties": {
        "backend": {
          "type": "string",
          "enum": ["sqlite", "postgresql"],
          "default": "sqlite"
        },
        "path": {
          "type": "string",
          "default": "~/.local/share/bdnex/bdnex.db"
        }
      },
      "required": ["backend"]
    }
  }
}
```

---

## Implementation Checklist

- [ ] Create `bdnex/conf/schema.sql` with table definitions
- [ ] Implement `BDneXDB` class in `bdnex/lib/database.py`
- [ ] Implement `SessionManager` in same file
- [ ] Add database CLI arguments to `args()`
- [ ] Integrate with `AdvancedBatchProcessor`
- [ ] Add tests in `test/test_database.py`
- [ ] Update configuration YAML schema
- [ ] Document resume workflow
- [ ] Add --skip-processed and --force support

---

## Migration Path for Existing Data

For users who have already run batch processing without a database:

```python
def migrate_existing_batch_logs():
    """Import existing batch logs into database."""
    db = BDneXDB()
    
    for log_file in Path('~/.config/bdnex/batch_results').glob('batch_*.json'):
        with open(log_file) as f:
            batch = json.load(f)
        
        session_id = db.start_session(
            directory='<imported>',
            ...
        )
        
        for result in batch['results']:
            db.record_processing(
                result['filename'],
                session_id,
                result
            )
```

This can be run once on first startup if database is empty and existing logs are found.
