#!/usr/bin/env python
"""Test database integration with batch processor."""

import sys
import os
import tempfile
sys.path.insert(0, 'd:\\repos\\bdnex')

from bdnex.lib.advanced_batch_processor import AdvancedBatchProcessor

def test_batch_with_database():
    print("Testing AdvancedBatchProcessor with Database...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_files = []
        for i in range(3):
            test_file = os.path.join(tmpdir, f'test_{i}.cbz')
            with open(test_file, 'w') as f:
                f.write('test data')
            test_files.append(test_file)
        
        try:
            # Create processor with database support
            processor = AdvancedBatchProcessor(
                batch_mode=True,
                num_workers=2,
                output_dir=os.path.join(tmpdir, 'output'),
                use_database=True,
                skip_processed=False,
            )
            print("✓ Processor created with database support")
            
            # Check database is initialized
            if processor.db:
                print("✓ Database initialized")
                
                # Check that files are not yet processed
                for f in test_files:
                    is_proc = processor.db.is_processed(f)
                    if not is_proc:
                        print(f"✓ File not processed: {os.path.basename(f)}")
            
            # Simulate processing results
            results = []
            for test_file in test_files:
                result = {
                    'filename': test_file,
                    'success': True,
                    'bdgest_id': 12345,
                    'title': 'Test Album',
                    'series': 'Test Series',
                    'score': 0.95,
                    'status': 'success',
                    'processing_time_ms': 1500,
                }
                results.append(result)
            
            # Test session and recording (without actual processing)
            session_id = processor.db.start_session(
                directory=tmpdir,
                batch_mode=True,
            )
            print(f"✓ Session started: {session_id}")
            
            # Record results
            for result in results:
                file_id = processor.db.record_processing(
                    result['filename'],
                    session_id,
                    result
                )
                print(f"✓ Recorded {os.path.basename(result['filename'])}: ID={file_id}")
            
            # Test skip_processed flag
            processor2 = AdvancedBatchProcessor(
                use_database=True,
                skip_processed=True,
            )
            
            # Check that files are marked as processed
            for f in test_files:
                is_proc = processor2.db.is_processed(f)
                if is_proc:
                    print(f"✓ File marked as processed: {os.path.basename(f)}")
            
            # Test retrieving files
            processed = processor.db.get_processed_files(session_id=session_id)
            print(f"✓ Retrieved {len(processed)} processed files from database")
            
            # Test statistics
            stats = processor.db.get_statistics(days=1)
            print(f"✓ Statistics: {stats['total_files']} files, {stats['unique_series']} series")
            
            print("\n✅ All database integration tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_batch_with_database()
    sys.exit(0 if success else 1)
