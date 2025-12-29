#!/usr/bin/env python3
"""
CLI Session Manager for Phase 2A
Handles database-aware command-line operations: resume, list sessions, show stats
"""

import logging
import sys
from typing import Optional, List, Dict
from datetime import datetime

from bdnex.lib.database import BDneXDB


class CLISessionManager:
    """Manage CLI session operations through database"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize session manager
        
        Args:
            db_path: Optional path to database. If None, uses default location
        """
        self.logger = logging.getLogger(__name__)
        try:
            self.db = BDneXDB(db_path)
            self.logger.debug(f"Database initialized at {self.db.db_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            self.db = None
    
    def list_all_sessions(self) -> bool:
        """
        List all batch processing sessions in database
        
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            self.logger.error("Database not available. Cannot list sessions.")
            return False
        
        try:
            sessions = self.db.conn.execute(
                "SELECT id, directory, status, total_files, files_processed, "
                "       files_failed, session_start, session_end, num_workers, batch_mode "
                "FROM processing_sessions "
                "ORDER BY id DESC"
            ).fetchall()
            
            if not sessions:
                print("\nNo sessions found in database.")
                return True
            
            print("\n" + "="*100)
            print("BATCH PROCESSING SESSIONS")
            print("="*100)
            print(f"{'ID':>5} {'Status':<10} {'Files':<12} {'Processed':<12} {'Failed':<8} {'Workers':<8} {'Created':<20}")
            print("-"*100)
            
            for row in sessions:
                session_id, directory, status, total, processed, failed, start_time, end_time, workers, batch_mode = row
                processed_count = processed or 0
                failed_count = failed or 0
                status_str = status or "unknown"
                workers_count = workers or "?"
                
                print(f"{session_id:>5} {status_str:<10} {total:<12} {processed_count:<12} {failed_count:<8} {workers_count:<8} {start_time:<20}")
            
            print("="*100)
            print(f"\nTotal sessions: {len(sessions)}")
            print("Use --session-info <id> to see detailed statistics for a session\n")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {e}")
            return False
    
    def show_session_info(self, session_id: int) -> bool:
        """
        Show detailed information about a specific session
        
        Args:
            session_id: Database session ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            self.logger.error("Database not available. Cannot retrieve session info.")
            return False
        
        try:
            # Get session info
            session = self.db.conn.execute(
                "SELECT id, directory, status, total_files, files_processed, "
                "       files_failed, session_start, session_end, num_workers, batch_mode, "
                "       json_log_path "
                "FROM processing_sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            
            if not session:
                print(f"\nSession {session_id} not found.\n")
                return False
            
            sid, directory, status, total, processed, failed, start_time, end_time, workers, batch_mode, log_path = session
            
            print("\n" + "="*80)
            print(f"SESSION #{sid} - {directory or 'Unnamed'}")
            print("="*80)
            print(f"Status:           {status or 'unknown'}")
            print(f"Started:          {start_time or 'N/A'}")
            print(f"Ended:            {end_time or 'In progress'}")
            print(f"Workers:          {workers or 'N/A'}")
            print(f"Batch Mode:       {'Yes' if batch_mode else 'No'}")
            print(f"\nFiles Total:      {total or 0}")
            print(f"Files Processed:  {processed or 0}")
            print(f"Files Failed:     {failed or 0}")
            
            if total:
                success_rate = ((total - (failed or 0)) / total * 100) if total > 0 else 0
                print(f"Success Rate:     {success_rate:.1f}%")
            
            # Get processed files in this session
            files = self.db.conn.execute(
                "SELECT id, file_path, status, bdgest_id, processed_date "
                "FROM processed_files WHERE session_id = ? "
                "ORDER BY processed_date DESC LIMIT 10",
                (session_id,)
            ).fetchall()
            
            if files:
                print(f"\nRecent Files (last 10):")
                print("-"*80)
                for file_id, path, file_status, bdgest_id, proc_time in files:
                    status_icon = "OK" if file_status == "success" else "X"
                    print(f"  [{status_icon}] {path}")
                    if bdgest_id:
                        print(f"      → BdGest ID: {bdgest_id}")
            
            print("="*80 + "\n")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve session info: {e}")
            return False
    
    def can_resume_session(self, session_id: int) -> bool:
        """
        Check if a session can be resumed
        
        Args:
            session_id: Database session ID to check
            
        Returns:
            True if session exists and can be resumed, False otherwise
        """
        if not self.db:
            self.logger.error("Database not available.")
            return False
        
        try:
            with self.db as db:
                session = db.conn.execute(
                    "SELECT id, status FROM processing_sessions WHERE id = ?",
                    (session_id,)
                ).fetchone()
            
            if not session:
                self.logger.error(f"Session {session_id} not found.")
                return False
            
            sid, status = session
            if status == "paused":
                self.logger.info(f"Session {sid} can be resumed (currently paused).")
                return True
            elif status == "completed":
                self.logger.warning(f"Session {sid} is already completed.")
                return False
            else:
                self.logger.warning(f"Session {sid} has status '{status}' and cannot be resumed.")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to check session: {e}")
            return False
    
    def get_unprocessed_files(self, session_id: int) -> Optional[List[str]]:
        """
        Get list of unprocessed files from a session
        
        Args:
            session_id: Database session ID
            
        Returns:
            List of file paths not yet processed in this session, or None on error
        """
        if not self.db:
            self.logger.error("Database not available.")
            return None
        
        try:
            with self.db as db:
                files = db.conn.execute(
                    "SELECT DISTINCT file_path FROM processed_files "
                    "WHERE session_id = ? AND status = 'pending' "
                    "ORDER BY file_path",
                    (session_id,)
                ).fetchall()
            
            return [row[0] for row in files] if files else []
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve unprocessed files: {e}")
            return None
    
    def handle_cli_session_args(self, args) -> bool:
        """
        Handle database-aware CLI arguments
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            True if handled successfully, False otherwise
        """
        # Handle --list-sessions
        if args.list_sessions:
            return self.list_all_sessions()
        
        # Handle --session-info
        if args.session_info is not None:
            return self.show_session_info(args.session_info)
        
        # Handle --resume
        if args.resume_session is not None:
            if self.can_resume_session(args.resume_session):
                self.logger.info(f"Ready to resume session {args.resume_session}")
                # Return session ID to indicate resume mode
                return ('resume', args.resume_session)
            else:
                self.logger.error(f"Cannot resume session {args.resume_session}")
                return False
        
        # No session-related args handled
        return None
