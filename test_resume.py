"""
Test de la fonctionnalité de reprise de session (Phase 2A)
"""
import os
import tempfile
from bdnex.lib.database import BDneXDB
from bdnex.lib.advanced_batch_processor import AdvancedBatchProcessor
from bdnex.lib.cli_session_manager import CLISessionManager


def cleanup_test_db(db_path):
    """Clean up test database"""
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception as e:
        print(f"Warning: Could not remove test DB: {e}")


def test_resume_session():
    """Test complete resume workflow"""
    print("\n✓ Test: Complete Resume Workflow")
    
    # Setup test database
    db_path = os.path.join(tempfile.gettempdir(), 'test_resume.db')
    cleanup_test_db(db_path)
    
    db = BDneXDB(db_path)
    
    # Create initial session
    original_session_id = db.start_session(
        directory="/test/path",
        batch_mode=True,
        strict_mode=False,
        num_workers=4
    )
    
    # Add some files to session
    files = [
        "/test/path/file1.cbz",
        "/test/path/file2.cbz",
        "/test/path/file3.cbz",
    ]
    
    for file in files:
        result = {
            'filename': file,
            'success': False,  # Simulating unprocessed
            'bdgest_id': None,
            'score': 0.0,
        }
        db.record_processing(file, original_session_id, result)
    
    # Mark session as paused
    db.conn.execute("UPDATE processing_sessions SET status='paused' WHERE id=?", (original_session_id,))
    db.conn.commit()
    
    print(f"  ✓ Created session {original_session_id} with {len(files)} files")
    
    # Test resume_session
    new_session_id = db.resume_session(original_session_id)
    assert new_session_id != original_session_id
    print(f"  ✓ Resumed as new session {new_session_id}")
    
    # Test get_session_files
    session_files = db.get_session_files(original_session_id)
    assert len(session_files) == 3
    assert all(not f['processed'] for f in session_files)
    print(f"  ✓ Retrieved {len(session_files)} unprocessed files")
    
    # Test with processor
    processor = AdvancedBatchProcessor(
        batch_mode=True,
        use_database=True,
    )
    processor.db = db
    
    unprocessed = processor.load_session_files(original_session_id)
    assert len(unprocessed) == 3
    assert all(f in files for f in unprocessed)
    print(f"  ✓ Processor loaded {len(unprocessed)} files to resume")
    
    # Cleanup
    db.close()
    cleanup_test_db(db_path)
    print("  ✓ Resume workflow complete")


def test_resume_with_cli():
    """Test resume via CLI"""
    print("\n✓ Test: Resume via CLI arguments")
    
    db_path = os.path.join(tempfile.gettempdir(), 'test_cli_resume.db')
    cleanup_test_db(db_path)
    
    db = BDneXDB(db_path)
    
    # Create and pause a session
    session_id = db.start_session("/test/dir", num_workers=2, batch_mode=True)
    db.conn.execute("UPDATE processing_sessions SET status='paused' WHERE id=?", (session_id,))
    db.conn.commit()
    
    # Test CLI manager
    manager = CLISessionManager(db_path)
    
    # Mock args
    class Args:
        list_sessions = False
        session_info = None
        resume_session = session_id
        skip_processed = False
    
    args = Args()
    result = manager.handle_cli_session_args(args)
    
    # Should return tuple ('resume', session_id)
    assert isinstance(result, tuple)
    assert result[0] == 'resume'
    assert result[1] == session_id
    
    print(f"  ✓ CLI correctly handles --resume {session_id}")
    
    # Cleanup
    manager.db.conn.close()
    cleanup_test_db(db_path)


def test_partial_session_processing():
    """Test session with some files already processed"""
    print("\n✓ Test: Partial Session Processing")
    
    db_path = os.path.join(tempfile.gettempdir(), 'test_partial.db')
    cleanup_test_db(db_path)
    
    db = BDneXDB(db_path)
    
    # Create session
    session_id = db.start_session("/test", num_workers=2, batch_mode=True)
    
    # Add 5 files, mark 2 as processed
    all_files = [f"/test/file{i}.cbz" for i in range(5)]
    
    for i, file in enumerate(all_files):
        result = {
            'filename': file,
            'success': i < 2,  # First 2 are successful
            'bdgest_id': 123 if i < 2 else None,
            'score': 0.9 if i < 2 else 0.0,
        }
        db.record_processing(file, session_id, result)
    
    # Mark first 2 as processed
    for i in range(2):
        db.mark_as_processed(all_files[i], session_id)
    
    # Get remaining files
    session_files = db.get_session_files(session_id)
    processed_count = sum(1 for f in session_files if f['processed'])
    unprocessed_count = sum(1 for f in session_files if not f['processed'])
    
    assert processed_count == 2
    assert unprocessed_count == 3
    print(f"  ✓ Session has {processed_count} processed, {unprocessed_count} remaining")
    
    # Resume should only load unprocessed
    processor = AdvancedBatchProcessor(use_database=True)
    processor.db = db
    
    remaining = processor.load_session_files(session_id)
    assert len(remaining) == 3
    print(f"  ✓ Processor correctly loads only {len(remaining)} unprocessed files")
    
    # Cleanup
    db.close()
    cleanup_test_db(db_path)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing Resume Session Feature (Phase 2A)")
    print("="*60)
    
    try:
        test_resume_session()
        test_resume_with_cli()
        test_partial_session_processing()
        
        print("\n" + "="*60)
        print("✅ All resume tests passed! Phase 2A complete")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ Assertion failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
