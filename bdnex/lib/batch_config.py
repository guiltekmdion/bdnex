"""
Configuration et paramètres pour le batch processing.
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class BatchConfig:
    """Configuration du batch processing avec support cache et logging."""
    
    def __init__(self, batch_mode: bool = False, strict_mode: bool = False, 
                 num_workers: int = 4, output_dir: Optional[str] = None):
        """
        Initialize batch configuration.
        
        Args:
            batch_mode: Enable batch mode (disables interactive UI)
            strict_mode: Reject low-confidence matches instead of asking
            num_workers: Number of parallel workers (default 4, max 8)
            output_dir: Directory for batch results and logs
        """
        self.logger = logging.getLogger(__name__)
        self.batch_mode = batch_mode
        self.strict_mode = strict_mode
        self.num_workers = min(max(num_workers, 1), 8)  # Clamp to 1-8
        
        # Setup output directory
        if output_dir is None:
            # Use default batch results directory
            from bdnex.lib.utils import bdnex_config
            bdnex_conf = bdnex_config()
            share_path = os.path.expanduser(bdnex_conf['bdnex']['share_path'])
            output_dir = os.path.join(share_path, 'batch_results')
        
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Cache directory for sitemaps
        self.cache_dir = os.path.join(output_dir, 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # Log files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.json_log = os.path.join(output_dir, f'batch_{timestamp}.json')
        self.csv_log = os.path.join(output_dir, f'batch_{timestamp}.csv')
        
        self.batch_start_time = datetime.now()
        self.results = []
    
    def add_result(self, result: Dict[str, Any]):
        """Add a processing result to the batch log."""
        result_with_timestamp = {
            **result,
            'timestamp': datetime.now().isoformat(),
        }
        self.results.append(result_with_timestamp)
    
    def save_json_log(self):
        """Save results to JSON log."""
        try:
            summary = {
                'batch_start': self.batch_start_time.isoformat(),
                'batch_end': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - self.batch_start_time).total_seconds(),
                'total_files': len(self.results),
                'successful': sum(1 for r in self.results if r.get('success')),
                'failed': sum(1 for r in self.results if not r.get('success')),
                'low_confidence': sum(1 for r in self.results if r.get('score', 1) < 0.70),
                'results': self.results,
            }
            
            with open(self.json_log, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Résultats sauvegardés en JSON: {self.json_log}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde JSON: {e}")
    
    def save_csv_log(self):
        """Save results to CSV log."""
        try:
            import csv
            
            if not self.results:
                return
            
            # Get all keys from results
            fieldnames = set()
            for result in self.results:
                fieldnames.update(result.keys())
            fieldnames = sorted(fieldnames)
            
            with open(self.csv_log, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
            
            self.logger.info(f"Résultats sauvegardés en CSV: {self.csv_log}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde CSV: {e}")


class SitemapCache:
    """Cache persistant pour les sitemaps nettoyées."""
    
    CACHE_VALIDITY_HOURS = 24  # Re-fetch sitemaps après 24h
    
    def __init__(self, cache_dir: str):
        """
        Initialize sitemap cache.
        
        Args:
            cache_dir: Directory to store cached sitemaps
        """
        self.cache_dir = cache_dir
        self.logger = logging.getLogger(__name__)
        self.cache_file = os.path.join(cache_dir, 'sitemaps_cache.json')
    
    def get_cache(self) -> Optional[Dict[str, list]]:
        """
        Get cached sitemaps if still valid.
        
        Returns:
            Cached album_list and urls or None if cache is invalid/missing
        """
        if not os.path.exists(self.cache_file):
            return None
        
        try:
            file_mtime = os.path.getmtime(self.cache_file)
            age_hours = (datetime.now() - datetime.fromtimestamp(file_mtime)).total_seconds() / 3600
            
            if age_hours > self.CACHE_VALIDITY_HOURS:
                self.logger.debug(f"Cache expiré ({age_hours:.1f}h)")
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            self.logger.debug(f"Cache valide ({age_hours:.1f}h), {len(cache.get('album_list', []))} albums")
            return cache
        except Exception as e:
            self.logger.warning(f"Erreur lecture cache: {e}")
            return None
    
    def save_cache(self, album_list: list, urls: list):
        """
        Save sitemaps to cache.
        
        Args:
            album_list: List of album names
            urls: List of corresponding URLs
        """
        try:
            cache = {
                'album_list': album_list,
                'urls': urls,
                'timestamp': datetime.now().isoformat(),
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False)
            
            self.logger.debug(f"Cache sauvegardé: {len(album_list)} albums")
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde cache: {e}")
