"""
BDneX Database Module - Phase 1 Implementation

Provides database access for tracking processed files, sessions, and metadata.
"""

import os
import sqlite3
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


class BDneXDB:
    """Main database interface for BDneX."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
                    Default: ~/.local/share/bdnex/bdnex.db
        """
        self.logger = logging.getLogger(__name__)
        
        if db_path is None:
            try:
                from bdnex.lib.utils import bdnex_config
                config = bdnex_config()
                share_path = config.get('bdnex', {}).get('share_path', '~/.local/share/bdnex')
                share_path = os.path.expanduser(share_path)
                db_path = os.path.join(share_path, 'bdnex.db')
            except Exception as e:
                self.logger.warning(f"Could not read config: {e}, using default path")
                db_path = os.path.expanduser('~/.local/share/bdnex/bdnex.db')
        
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)
        
        self.db_path = db_path
        self.logger.info(f"Database: {db_path}")
        
        # Connect to database
        # Increase timeout to reduce transient "database is locked" errors,
        # especially during fast batch inserts.
        self.conn = sqlite3.connect(db_path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

        # Improve concurrent read/write behavior.
        try:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA busy_timeout=30000")
        except Exception:
            pass
        
        # Initialize schema
        self._init_schema()
    
    def _init_schema(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Check if tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='processed_files'"
        )
        if cursor.fetchone():
            self.logger.debug("Database schema already initialized")
            return
        
        self.logger.info("Initializing database schema...")
        
        # Create tables
        schema_sql = """
        -- Fichiers traités
        CREATE TABLE IF NOT EXISTS processed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            file_hash TEXT NOT NULL,
            file_size INTEGER,
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified TIMESTAMP,
            
            -- Résultats de recherche
            bdgest_id INTEGER,
            bdgest_url TEXT,
            confidence_score REAL,
            
            -- Métadonnées trouvées
            title TEXT,
            series TEXT,
            volume INTEGER,
            editor TEXT,
            year INTEGER,
            isbn TEXT,
            pages INTEGER,
            
            -- État du traitement
            status TEXT CHECK(status IN ('success', 'manual', 'skipped', 'failed', 'unknown')),
            error_msg TEXT,
            
            -- ComicInfo.xml
            has_metadata BOOLEAN DEFAULT 0,
            metadata_hash TEXT,
            
            -- Session
            session_id INTEGER,
            processing_time_ms INTEGER,
            
            FOREIGN KEY (session_id) REFERENCES processing_sessions(id)
        );
        
        -- Sessions de traitement batch
        CREATE TABLE IF NOT EXISTS processing_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_end TIMESTAMP,
            
            -- Configuration
            directory TEXT NOT NULL,
            pattern TEXT DEFAULT '*.cbz|*.cbr',
            batch_mode INTEGER DEFAULT 1,
            strict_mode INTEGER DEFAULT 0,
            num_workers INTEGER DEFAULT 4,
            
            -- Résultats
            total_files INTEGER DEFAULT 0,
            files_processed INTEGER DEFAULT 0,
            files_successful INTEGER DEFAULT 0,
            files_failed INTEGER DEFAULT 0,
            files_skipped INTEGER DEFAULT 0,
            
            -- État
            status TEXT CHECK(status IN ('running', 'paused', 'completed', 'failed', 'resumed')),
            
            -- Logs
            log_file_path TEXT,
            json_log_path TEXT,
            csv_log_path TEXT
        );
        
        -- Cache des albums Bédéthèque
        CREATE TABLE IF NOT EXISTS bdgest_albums (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            series TEXT,
            volume INTEGER,
            editor TEXT,
            year INTEGER,
            isbn TEXT,
            pages INTEGER,
            cover_url TEXT,
            url TEXT UNIQUE,
            
            cached_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cache_valid_until TIMESTAMP,
            
            metadata JSON
        );
        
        -- Historique des modifications
        CREATE TABLE IF NOT EXISTS metadata_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            field TEXT,
            old_value TEXT,
            new_value TEXT,
            source TEXT,
            
            FOREIGN KEY (file_id) REFERENCES processed_files(id)
        );
        
        -- Statistiques d'utilisation
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE DEFAULT CURRENT_DATE,
            total_files INTEGER,
            total_series INTEGER,
            total_editors INTEGER,
            avg_pages INTEGER,
            avg_processing_time_ms INTEGER
        );
        
        -- Index pour les performances
        CREATE INDEX IF NOT EXISTS idx_file_path ON processed_files(file_path);
        CREATE INDEX IF NOT EXISTS idx_status ON processed_files(status);
        CREATE INDEX IF NOT EXISTS idx_session_id ON processed_files(session_id);
        CREATE INDEX IF NOT EXISTS idx_bdgest_id ON processed_files(bdgest_id);
        CREATE INDEX IF NOT EXISTS idx_series ON processed_files(series);
        CREATE INDEX IF NOT EXISTS idx_editor ON processed_files(editor);
        """
        
        cursor.executescript(schema_sql)
        self.conn.commit()
        self.logger.info("Database schema initialized successfully")
    
    def is_processed(self, file_path: str) -> bool:
        """
        Check if a file has been processed before.
        
        Args:
            file_path: Path to the file to check
        
        Returns:
            True if file has been processed, False otherwise
        """
        file_path = self._normalize_file_path(file_path)
        cursor = self.conn.cursor()
        row = cursor.execute(
            "SELECT id FROM processed_files WHERE file_path = ?",
            (file_path,)
        ).fetchone()
        return row is not None

    @staticmethod
    def _normalize_file_path(file_path: str) -> str:
        """Normalize file paths for consistent DB identity.

        - Absolute path
        - Normalized separators
        - Case-normalized on Windows
        """
        if not file_path:
            return ""
        try:
            normalized = os.path.normpath(os.path.abspath(os.path.expanduser(file_path)))
            if os.name == "nt":
                normalized = os.path.normcase(normalized)
            return normalized
        except Exception:
            return file_path
    
    def get_file_hash(self, file_path: str) -> str:
        """
        Compute SHA256 hash of a file.
        
        Args:
            file_path: Path to the file
        
        Returns:
            Hex string of SHA256 hash
        """
        file_path = self._normalize_file_path(file_path)
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            self.logger.error(f"Error computing hash for {file_path}: {e}")
            return ""
    
    def record_processing(
        self,
        file_path: str,
        session_id: int,
        result: Dict[str, Any],
    ) -> int:
        """
        Record a processed file in the database.
        
        Args:
            file_path: Path to the processed file
            session_id: Session ID this file was processed in
            result: Result dictionary with keys like:
                   - bdgest_id: Album ID from Bédéthèque
                   - title, series, volume, editor, year, isbn, pages
                   - score: Confidence score (0-100)
                   - status: 'success', 'manual', 'skipped', 'failed'
                   - error: Error message if failed
                   - processing_time_ms: Time taken to process
        
        Returns:
            File ID in database
        """
        file_path = self._normalize_file_path(file_path)

        file_hash = self.get_file_hash(file_path)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
        
        # Normalize score to 0-1 range if it's 0-100
        score = result.get('score', 0)
        if score > 1:
            score = score / 100.0
        
        cursor = self.conn.cursor()
        try:
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
                file_size,
                result.get('bdgest_id'),
                result.get('bdgest_url'),
                result.get('title'),
                result.get('series'),
                result.get('volume'),
                result.get('editor'),
                result.get('year'),
                result.get('isbn'),
                result.get('pages'),
                score,
                result.get('status', 'unknown'),
                result.get('error'),
                session_id,
                result.get('processing_time_ms', 0),
            ))
            
            self.conn.commit()
            file_id = cursor.lastrowid
            self.logger.debug(f"Recorded file {file_path} (ID: {file_id})")
            return file_id
        
        except sqlite3.IntegrityError as e:
            # Already recorded: return existing row id (do not crash the batch).
            self.logger.info(f"File already recorded: {file_path}")
            existing = cursor.execute(
                "SELECT id FROM processed_files WHERE file_path = ?",
                (file_path,),
            ).fetchone()
            if existing:
                return int(existing[0])
            raise
        except Exception as e:
            self.logger.error(f"Error recording file: {e}")
            raise
    
    def start_session(
        self,
        directory: str,
        batch_mode: bool = True,
        strict_mode: bool = False,
        num_workers: int = 4,
        pattern: str = '*.cbz|*.cbr',
    ) -> int:
        """
        Start a new processing session.
        
        Args:
            directory: Directory being processed
            batch_mode: Whether batch mode is enabled
            strict_mode: Whether strict mode is enabled
            num_workers: Number of worker processes
            pattern: File pattern to match
        
        Returns:
            Session ID
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO processing_sessions (
                    directory, batch_mode, strict_mode, num_workers,
                    pattern, status
                ) VALUES (?, ?, ?, ?, ?, 'running')
            """, (directory, batch_mode, strict_mode, num_workers, pattern))
            
            self.conn.commit()
            session_id = cursor.lastrowid
            self.logger.info(f"Started session {session_id} for {directory}")
            return session_id
        
        except Exception as e:
            self.logger.error(f"Error starting session: {e}")
            raise
    
    def update_session(self, session_id: int, **kwargs) -> None:
        """
        Update session statistics.
        
        Args:
            session_id: Session ID to update
            **kwargs: Fields to update
                     Valid fields: total_files, files_processed, files_successful,
                                  files_failed, files_skipped, status
        """
        allowed_fields = {
            'total_files', 'files_processed', 'files_successful',
            'files_failed', 'files_skipped', 'status'
        }
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return
        
        set_clause = ', '.join(f"{k}=?" for k in updates.keys())
        cursor = self.conn.cursor()
        
        try:
            cursor.execute(
                f"UPDATE processing_sessions SET {set_clause} WHERE id=?",
                list(updates.values()) + [session_id]
            )
            
            # Set session_end timestamp if status is 'completed'
            if updates.get('status') == 'completed':
                cursor.execute(
                    "UPDATE processing_sessions SET session_end=CURRENT_TIMESTAMP WHERE id=?",
                    (session_id,)
                )
            
            self.conn.commit()
            self.logger.debug(f"Updated session {session_id}: {updates}")
        
        except Exception as e:
            self.logger.error(f"Error updating session: {e}")
            raise
    
    def get_session_stats(self, session_id: int) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Args:
            session_id: Session ID to query
        
        Returns:
            Dictionary with session information
        """
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
        session_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get processed files with optional filters.
        
        Args:
            status: Filter by status ('success', 'manual', 'failed', etc.)
            series: Filter by series name
            session_id: Filter by session ID
            limit: Maximum number of results
        
        Returns:
            List of file records
        """
        query = "SELECT * FROM processed_files WHERE 1=1"
        params = []
        
        if status:
            query += " AND status=?"
            params.append(status)
        
        if series:
            query += " AND series=?"
            params.append(series)
        
        if session_id:
            query += " AND session_id=?"
            params.append(session_id)
        
        query += f" ORDER BY processed_date DESC LIMIT {limit}"
        
        cursor = self.conn.cursor()
        rows = cursor.execute(query, params).fetchall()
        
        return [dict(row) for row in rows]
    
    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get usage statistics for the past N days.
        
        Args:
            days: Number of days to include
        
        Returns:
            Dictionary with statistics
        """
        cursor = self.conn.cursor()
        
        # Get date range
        start_date = datetime.now() - timedelta(days=days)
        
        stats = {}
        
        # Total files processed
        row = cursor.execute(
            "SELECT COUNT(*) as count FROM processed_files WHERE processed_date > ?",
            (start_date,)
        ).fetchone()
        stats['total_files'] = dict(row)['count'] if row else 0
        
        # Files by status
        for status in ['success', 'manual', 'failed', 'skipped']:
            row = cursor.execute(
                "SELECT COUNT(*) as count FROM processed_files WHERE status=? AND processed_date > ?",
                (status, start_date)
            ).fetchone()
            stats[f'files_{status}'] = dict(row)['count'] if row else 0
        
        # Unique series
        row = cursor.execute(
            "SELECT COUNT(DISTINCT series) as count FROM processed_files WHERE series IS NOT NULL AND processed_date > ?",
            (start_date,)
        ).fetchone()
        stats['unique_series'] = dict(row)['count'] if row else 0
        
        # Unique editors
        row = cursor.execute(
            "SELECT COUNT(DISTINCT editor) as count FROM processed_files WHERE editor IS NOT NULL AND processed_date > ?",
            (start_date,)
        ).fetchone()
        stats['unique_editors'] = dict(row)['count'] if row else 0
        
        # Average processing time
        row = cursor.execute(
            "SELECT AVG(processing_time_ms) as avg_time FROM processed_files WHERE processing_time_ms > 0 AND processed_date > ?",
            (start_date,)
        ).fetchone()
        stats['avg_processing_time_ms'] = int(dict(row)['avg_time']) if row and dict(row)['avg_time'] else 0
        
        return stats
    
    def resume_session(self, session_id: int) -> int:
        """
        Resume a paused or failed session.
        
        Args:
            session_id: Session ID to resume
        
        Returns:
            New session ID (fork of original)
        """
        cursor = self.conn.cursor()
        
        # Get original session info
        original = cursor.execute(
            "SELECT * FROM processing_sessions WHERE id=?",
            (session_id,)
        ).fetchone()
        
        if not original:
            raise ValueError(f"Session {session_id} not found")
        
        original_dict = dict(original)
        
        # Create new session with same parameters
        cursor.execute("""
            INSERT INTO processing_sessions (
                directory, batch_mode, strict_mode, num_workers, pattern, status
            ) VALUES (?, ?, ?, ?, ?, 'running')
        """, (
            original_dict['directory'],
            original_dict['batch_mode'],
            original_dict['strict_mode'],
            original_dict['num_workers'],
            original_dict['pattern'],
        ))
        
        self.conn.commit()
        new_session_id = cursor.lastrowid
        
        self.logger.info(f"Resumed session {session_id} as new session {new_session_id}")
        return new_session_id
    
    def get_session_files(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Get all files associated with a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of dicts with file information (with 'processed' flag computed from status)
        """
        cursor = self.conn.cursor()
        rows = cursor.execute("""
            SELECT 
                file_path,
                CASE WHEN status IN ('success', 'manual') THEN 1 ELSE 0 END as processed,
                status,
                bdgest_id,
                processed_date
            FROM processed_files
            WHERE session_id = ?
            ORDER BY processed_date ASC
        """, (session_id,)).fetchall()
        
        return [dict(row) for row in rows]
    
    def mark_as_processed(self, file_path: str, session_id: int):
        """Mark a file as successfully processed."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE processed_files
            SET status = 'success'
            WHERE file_path = ? AND session_id = ?
        """, (file_path, session_id))
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.logger.debug("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
