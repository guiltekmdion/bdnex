#!/usr/bin/env python
"""Quick import test for batch processing modules."""

import sys
sys.path.insert(0, 'd:\\repos\\bdnex')

try:
    from bdnex.lib.batch_config import BatchConfig, SitemapCache
    print("✓ batch_config imports OK")
    
    from bdnex.lib.batch_worker import process_single_file
    print("✓ batch_worker imports OK")
    
    from bdnex.lib.advanced_batch_processor import AdvancedBatchProcessor
    print("✓ advanced_batch_processor imports OK")
    
    # Test basic functionality
    config = BatchConfig()
    print(f"✓ BatchConfig initialized: {config.num_workers} workers")
    
    cache = SitemapCache()
    print(f"✓ SitemapCache initialized")
    
    processor = AdvancedBatchProcessor()
    print(f"✓ AdvancedBatchProcessor initialized")
    
    print("\n✅ All batch processing modules working!")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
