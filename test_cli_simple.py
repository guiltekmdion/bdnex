#!/usr/bin/env python3
"""
Test CLI Session Manager - Simple version
Validates Phase 2A CLI integration
"""

import logging
import os
import sys
from pathlib import Path
from argparse import Namespace
import shutil

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

from bdnex.lib.cli_session_manager import CLISessionManager
from bdnex.lib.database import BDneXDB

# Use fixed test directory instead of tempdir
TEST_DIR = "test_cli_manager_work"
os.makedirs(TEST_DIR, exist_ok=True)

logging.basicConfig(level=logging.WARNING)  # Suppress noise


def cleanup_test_db(db_path):
    """Force close and cleanup database files"""
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        wal_file = f"{db_path}-wal"
        if os.path.exists(wal_file):
            os.remove(wal_file)
        shm_file = f"{db_path}-shm"
        if os.path.exists(shm_file):
            os.remove(shm_file)
    except:
        pass


def test_1_cli_manager_init():
    """Test CLISessionManager initialization"""
    print("\n✓ Test 1: CLISessionManager initialization")
    
    db_path = os.path.join(TEST_DIR, "test1.db")
    cleanup_test_db(db_path)
    
    manager = CLISessionManager(db_path)
    assert manager.db is not None, "Database should be initialized"
    
    # Close explicitly
    manager.db.conn.close()
    cleanup_test_db(db_path)
    print("  ✓ Manager initialized")


def test_2_list_sessions_empty():
    """Test listing sessions on empty database"""
    print("\n✓ Test 2: List sessions (empty)")
    
    db_path = os.path.join(TEST_DIR, "test2.db")
    cleanup_test_db(db_path)
    
    manager = CLISessionManager(db_path)
    result = manager.list_all_sessions()
    
    assert result is True, "Should return True"
    manager.db.conn.close()
    cleanup_test_db(db_path)
    print("  ✓ Empty DB handled")


def test_3_list_sessions_with_data():
    """Test listing sessions with data"""
    print("\n✓ Test 3: List sessions (with data)")
    
    db_path = os.path.join(TEST_DIR, "test3.db")
    cleanup_test_db(db_path)
    
    db = BDneXDB(db_path)
    session_id = db.start_session("Test", num_workers=4, batch_mode=True)
    db.conn.close()
    
    manager = CLISessionManager(db_path)
    result = manager.list_all_sessions()
    
    assert result is True
    manager.db.conn.close()
    cleanup_test_db(db_path)
    print(f"  ✓ Listed session {session_id}")


def test_4_session_info():
    """Test session info retrieval"""
    print("\n✓ Test 4: Session info")
    
    db_path = os.path.join(TEST_DIR, "test4.db")
    cleanup_test_db(db_path)
    
    db = BDneXDB(db_path)
    session_id = db.start_session("Info", num_workers=2, batch_mode=True)
    
    # Create test result dict
    result = {
        'bdgest_id': 999,
        'title': 'Test',
        'series': 'Test Series',
        'volume': 1,
        'status': 'success',
        'score': 95,
        'processing_time_ms': 100
    }
    file_id = db.record_processing("test.cbz", session_id, result)
    
    # Update session stats
    db.update_session(session_id, files_processed=1, files_successful=1, total_files=1)
    
    db.conn.close()
    
    manager = CLISessionManager(db_path)
    result_check = manager.show_session_info(session_id)
    
    assert result_check is True
    manager.db.conn.close()
    cleanup_test_db(db_path)
    print(f"  ✓ Session info retrieved")


def test_5_resume_check():
    """Test resume capability"""
    print("\n✓ Test 5: Resume capability check")
    
    db_path = os.path.join(TEST_DIR, "test5.db")
    cleanup_test_db(db_path)
    
    db = BDneXDB(db_path)
    session_id = db.start_session("Resume", num_workers=2, batch_mode=True)
    
    # Update session status to 'paused' so it can be resumed
    db.conn.execute("UPDATE processing_sessions SET status='paused' WHERE id=?", (session_id,))
    db.conn.commit()
    db.conn.close()
    
    manager = CLISessionManager(db_path)
    can_resume = manager.can_resume_session(session_id)
    
    assert can_resume is True, f"Should be resumable, got {can_resume}"
    manager.db.conn.close()
    cleanup_test_db(db_path)
    print(f"  ✓ Session resumable")


def test_6_cli_args():
    """Test CLI argument handling"""
    print("\n✓ Test 6: CLI argument handling")
    
    db_path = os.path.join(TEST_DIR, "test6.db")
    cleanup_test_db(db_path)
    
    # Create test session
    db = BDneXDB(db_path)
    session_id = db.start_session("CLI", num_workers=4, batch_mode=True)
    db.conn.close()
    
    # Test --list-sessions
    manager = CLISessionManager(db_path)
    args = Namespace(
        list_sessions=True,
        session_info=None,
        resume_session=None,
        skip_processed=False,
        force_reprocess=False
    )
    result = manager.handle_cli_session_args(args)
    assert result is True
    manager.db.conn.close()
    
    # Test --session-info
    manager = CLISessionManager(db_path)
    args.list_sessions = False
    args.session_info = session_id
    result = manager.handle_cli_session_args(args)
    assert result is True
    manager.db.conn.close()
    
    # Test --resume
    manager = CLISessionManager(db_path)
    # Mark session as paused so it can be resumed
    manager.db.conn.execute("UPDATE processing_sessions SET status='paused' WHERE id=?", (session_id,))
    manager.db.conn.commit()

    args.session_info = None
    args.resume_session = session_id
    result = manager.handle_cli_session_args(args)
    assert result is True
    manager.db.conn.close()
    
    cleanup_test_db(db_path)
    print(f"  ✓ CLI arguments handled correctly")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing CLI Session Manager (Phase 2A)")
    print("="*60)
    
    try:
        test_1_cli_manager_init()
        test_2_list_sessions_empty()
        test_3_list_sessions_with_data()
        test_4_session_info()
        test_5_resume_check()
        test_6_cli_args()
        
        # Cleanup
        shutil.rmtree(TEST_DIR, ignore_errors=True)
        
        print("\n" + "="*60)
        print("✓ All 6 tests passed! Phase 2A CLI Manager ready")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ Assertion failed: {e}\n")
        shutil.rmtree(TEST_DIR, ignore_errors=True)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        import traceback
        traceback.print_exc()
        shutil.rmtree(TEST_DIR, ignore_errors=True)
        sys.exit(1)
