#!/usr/bin/env python3
"""
Test CLI Session Manager
Validates Phase 2A CLI integration
"""

import logging
import os
import sys
import tempfile
from pathlib import Path
from argparse import Namespace

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

from bdnex.lib.cli_session_manager import CLISessionManager
from bdnex.lib.database import BDneXDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_cli_manager_initialization():
    """Test CLISessionManager can be initialized"""
    print("\n✓ Test 1: CLISessionManager initialization")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = CLISessionManager(db_path)
        
        assert manager.db is not None, "Database should be initialized"
        
        # Explicitly close database connection to release file lock
        if manager.db and hasattr(manager.db, 'conn'):
            manager.db.conn.close()
        
        print("  ✓ Manager initialized with database")


def test_list_sessions_empty_db():
    """Test listing sessions on empty database"""
    print("\n✓ Test 2: List sessions (empty database)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = CLISessionManager(db_path)
        
        result = manager.list_all_sessions()
        assert result is True, "Should return True even on empty DB"
        print("  ✓ Empty database handled correctly")


def test_list_sessions_with_data():
    """Test listing sessions with actual data"""
    print("\n✓ Test 3: List sessions (with data)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Create database with test session
        db = BDneXDB(db_path)
        session_id = db.start_session("Test Session", num_workers=4, batch_mode=True)
        
        # List sessions
        manager = CLISessionManager(db_path)
        result = manager.list_all_sessions()
        
        assert result is True, "Should list sessions successfully"
        print(f"  ✓ Listed session {session_id}")


def test_session_info():
    """Test retrieving detailed session info"""
    print("\n✓ Test 4: Session info retrieval")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Create database with test session and file
        db = BDneXDB(db_path)
        session_id = db.start_session("Info Test", num_workers=2, batch_mode=True)
        file_id = db.record_processing("test_file.cbz", "success", session_id, bdgest_id=12345)
        
        # Get session info
        manager = CLISessionManager(db_path)
        result = manager.show_session_info(session_id)
        
        assert result is True, "Should retrieve session info successfully"
        print(f"  ✓ Retrieved info for session {session_id} with {file_id} file")


def test_can_resume_session():
    """Test checking if session can be resumed"""
    print("\n✓ Test 5: Resume capability check")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Create database with test session
        db = BDneXDB(db_path)
        session_id = db.start_session("Resume Test", num_workers=2, batch_mode=True)
        
        # Check resume capability
        manager = CLISessionManager(db_path)
        
        # Should be resumable (status is not "completed")
        can_resume = manager.can_resume_session(session_id)
        print(f"  ✓ Session {session_id} resumable: {can_resume}")


def test_cli_args_list_sessions():
    """Test handling --list-sessions argument"""
    print("\n✓ Test 6: Handle --list-sessions argument")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Create test data
        db = BDneXDB(db_path)
        db.start_session("Arg Test", num_workers=4, batch_mode=True)
        
        # Create mock args
        args = Namespace(
            list_sessions=True,
            session_info=None,
            resume_session=None,
            skip_processed=False,
            force_reprocess=False
        )
        
        manager = CLISessionManager(db_path)
        result = manager.handle_cli_session_args(args)
        
        assert result is True, "Should handle --list-sessions successfully"
        print("  ✓ --list-sessions argument handled")


def test_cli_args_session_info():
    """Test handling --session-info argument"""
    print("\n✓ Test 7: Handle --session-info argument")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Create test data
        db = BDneXDB(db_path)
        session_id = db.start_session("Info Arg Test", num_workers=4, batch_mode=True)
        
        # Create mock args
        args = Namespace(
            list_sessions=False,
            session_info=session_id,
            resume_session=None,
            skip_processed=False,
            force_reprocess=False
        )
        
        manager = CLISessionManager(db_path)
        result = manager.handle_cli_session_args(args)
        
        assert result is True, "Should handle --session-info successfully"
        print(f"  ✓ --session-info argument handled for session {session_id}")


def test_cli_args_resume():
    """Test handling --resume argument"""
    print("\n✓ Test 8: Handle --resume argument")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Create test data
        db = BDneXDB(db_path)
        session_id = db.start_session("Resume Arg Test", num_workers=4, batch_mode=True)
        
        # Create mock args
        args = Namespace(
            list_sessions=False,
            session_info=None,
            resume_session=session_id,
            skip_processed=False,
            force_reprocess=False
        )
        
        manager = CLISessionManager(db_path)
        result = manager.handle_cli_session_args(args)
        
        assert result is True, "Should handle --resume successfully"
        print(f"  ✓ --resume argument handled for session {session_id}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing CLI Session Manager (Phase 2A)")
    print("="*60)
    
    try:
        test_cli_manager_initialization()
        test_list_sessions_empty_db()
        test_list_sessions_with_data()
        test_session_info()
        test_can_resume_session()
        test_cli_args_list_sessions()
        test_cli_args_session_info()
        test_cli_args_resume()
        
        print("\n" + "="*60)
        print("✓ All CLI Session Manager tests passed!")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
