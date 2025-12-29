#!/usr/bin/env python3
"""
Script de test pour le batch processing.
Vérifie que tous les composants fonctionnent ensemble.
"""
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported."""
    logger.info("Test 1: Imports")
    try:
        from bdnex.lib.batch_config import BatchConfig, SitemapCache
        logger.info("  ✓ batch_config")
        
        from bdnex.lib.batch_worker import process_single_file
        logger.info("  ✓ batch_worker")
        
        from bdnex.lib.advanced_batch_processor import AdvancedBatchProcessor
        logger.info("  ✓ advanced_batch_processor")
        
        from bdnex.lib.bdgest import BdGestParse, get_sitemap_cache
        logger.info("  ✓ bdgest with sitemap cache")
        
        return True
    except Exception as e:
        logger.error(f"  ✗ Import failed: {e}")
        return False

def test_batch_config():
    """Test BatchConfig initialization."""
    logger.info("Test 2: BatchConfig")
    try:
        from bdnex.lib.batch_config import BatchConfig
        
        config = BatchConfig(batch_mode=True, num_workers=4)
        logger.info(f"  ✓ Initialized with {config.num_workers} workers")
        logger.info(f"  ✓ Output dir: {config.output_dir}")
        logger.info(f"  ✓ Cache dir: {config.cache_dir}")
        
        # Add a test result
        test_result = {
            'filename': 'test.cbz',
            'success': True,
            'score': 0.85,
            'title': 'Test Album'
        }
        config.add_result(test_result)
        logger.info(f"  ✓ Added test result")
        
        return True
    except Exception as e:
        logger.error(f"  ✗ Config failed: {e}")
        return False

def test_sitemap_cache():
    """Test SitemapCache functionality."""
    logger.info("Test 3: SitemapCache")
    try:
        from bdnex.lib.batch_config import SitemapCache
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SitemapCache(tmpdir)
            logger.info(f"  ✓ Created cache in {tmpdir}")
            
            # Test save
            test_albums = ['Album 1', 'Album 2', 'Album 3']
            test_urls = ['http://ex1.com', 'http://ex2.com', 'http://ex3.com']
            cache.save_cache(test_albums, test_urls)
            logger.info(f"  ✓ Saved {len(test_albums)} albums")
            
            # Test retrieve
            retrieved = cache.get_cache()
            if retrieved and len(retrieved['album_list']) == 3:
                logger.info(f"  ✓ Retrieved {len(retrieved['album_list'])} albums from cache")
            else:
                logger.error(f"  ✗ Cache retrieval failed")
                return False
            
            return True
    except Exception as e:
        logger.error(f"  ✗ Cache failed: {e}")
        return False

def test_bdgest_cache():
    """Test BdGestParse with cache."""
    logger.info("Test 4: BdGestParse cache integration")
    try:
        from bdnex.lib.bdgest import BdGestParse, get_sitemap_cache
        
        # Get global cache instance
        cache = get_sitemap_cache()
        if cache:
            logger.info(f"  ✓ Global sitemap cache available")
        else:
            logger.warning(f"  ⚠ No global cache (will create on demand)")
        
        # Create parser instance (should use global cache)
        parser = BdGestParse(interactive=False)
        logger.info(f"  ✓ BdGestParse with cache: interactive={parser.interactive}")
        
        if parser.sitemap_cache:
            logger.info(f"  ✓ Parser has sitemap cache")
        else:
            logger.warning(f"  ⚠ Parser has no sitemap cache")
        
        return True
    except Exception as e:
        logger.error(f"  ✗ BdGestParse test failed: {e}")
        return False

def test_advanced_processor():
    """Test AdvancedBatchProcessor initialization."""
    logger.info("Test 5: AdvancedBatchProcessor")
    try:
        from bdnex.lib.advanced_batch_processor import AdvancedBatchProcessor
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = AdvancedBatchProcessor(
                batch_mode=True,
                strict_mode=True,
                num_workers=2,
                output_dir=tmpdir
            )
            logger.info(f"  ✓ Created processor: batch={processor.config.batch_mode}, workers={processor.config.num_workers}")
            logger.info(f"  ✓ Output: {processor.config.json_log}")
            
            return True
    except Exception as e:
        logger.error(f"  ✗ Processor failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("BDneX Batch Processing Tests")
    logger.info("=" * 60)
    
    tests = [
        test_imports,
        test_batch_config,
        test_sitemap_cache,
        test_bdgest_cache,
        test_advanced_processor,
    ]
    
    results = []
    for test_func in tests:
        result = test_func()
        results.append(result)
        logger.info("")
    
    logger.info("=" * 60)
    passed = sum(results)
    total = len(results)
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✓ All tests passed!")
        return 0
    else:
        logger.error("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
