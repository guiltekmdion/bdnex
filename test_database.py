#!/usr/bin/env python
"""Test database module."""

import sys
import os
import tempfile
sys.path.insert(0, 'd:\\repos\\bdnex')

from bdnex.lib.database import BDneXDB

def test_database():
    print("Testing BDneXDB...")
    
    # Use temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        
        try:
            # Test initialization
            db = BDneXDB(db_path)
            print("✓ Database initialized")
            
            # Test session creation
            session_id = db.start_session(
                directory='/test/path',
                batch_mode=True,
                num_workers=4
            )
            print(f"✓ Session created: ID={session_id}")
            
            # Test file recording
            result = {
                'bdgest_id': 12345,
                'title': 'Asterix',
                'series': 'Asterix',
                'volume': 1,
                'editor': 'Dargaud',
                'year': 1961,
                'pages': 48,
                'score': 95,
                'status': 'success',
                'processing_time_ms': 1500,
            }
            
            # Create a test file
            test_file = os.path.join(tmpdir, 'test.cbz')
            with open(test_file, 'w') as f:
                f.write('test')
            
            file_id = db.record_processing(test_file, session_id, result)
            print(f"✓ File recorded: ID={file_id}")
            
            # Test is_processed
            is_proc = db.is_processed(test_file)
            print(f"✓ File check: processed={is_proc}")
            
            # Test session update
            db.update_session(
                session_id,
                total_files=1,
                files_processed=1,
                files_successful=1,
                status='completed'
            )
            print("✓ Session updated")
            
            # Test session stats
            stats = db.get_session_stats(session_id)
            print(f"✓ Session stats: files_processed={stats.get('files_processed')}")
            
            # Test file retrieval
            files = db.get_processed_files(session_id=session_id)
            print(f"✓ Retrieved {len(files)} processed file(s)")
            
            # Test statistics
            stats = db.get_statistics(days=30)
            print(f"✓ Statistics: total_files={stats.get('total_files')}")
            
            db.close()
            print("\n✅ All database tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_database()
    sys.exit(0 if success else 1)
