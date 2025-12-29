"""
Plugin Manager for BDneX Scrapers - Phase 4

Manages dynamic loading and coordination of metadata scraper plugins.
Handles priority ordering, parallel searching, and result aggregation.
"""

import logging
import importlib
import pkgutil
from typing import List, Dict, Optional, Type, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_scraper import BaseScraper, ScraperResult


class PluginManager:
    """Manages scraper plugins and coordinates metadata retrieval."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin manager.
        
        Args:
            config: Configuration dictionary with scraper settings
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.scrapers: List[BaseScraper] = []
        self._loaded = False
    
    def load_scrapers(self, scrapers_package: str = "bdnex.lib.scrapers") -> None:
        """
        Discover and load all available scrapers.
        
        Args:
            scrapers_package: Package path to search for scrapers
        """
        if self._loaded:
            self.logger.debug("Scrapers already loaded")
            return
        
        try:
            # Import the scrapers package
            package = importlib.import_module(scrapers_package)
            package_path = Path(package.__file__).parent
            
            # Find all modules in the scrapers package
            for _, module_name, is_pkg in pkgutil.iter_modules([str(package_path)]):
                if module_name.startswith('_') or module_name == 'base_scraper':
                    continue
                
                try:
                    # Import the module
                    module = importlib.import_module(f"{scrapers_package}.{module_name}")
                    
                    # Look for scraper classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        
                        # Check if it's a scraper class (not the base class)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseScraper) and 
                            attr is not BaseScraper):
                            
                            # Get scraper-specific config
                            scraper_config = self.config.get(attr_name, {})
                            
                            # Instantiate scraper
                            scraper = attr(config=scraper_config)
                            
                            if scraper.is_enabled:
                                self.scrapers.append(scraper)
                                self.logger.info(f"Loaded scraper: {scraper.name} (priority: {scraper.priority})")
                            else:
                                self.logger.info(f"Scraper disabled: {scraper.name}")
                
                except Exception as e:
                    self.logger.error(f"Error loading scraper module {module_name}: {e}")
            
            # Sort scrapers by priority (lower = higher priority)
            self.scrapers.sort(key=lambda s: s.priority)
            
            self._loaded = True
            self.logger.info(f"Loaded {len(self.scrapers)} scrapers")
            
        except Exception as e:
            self.logger.error(f"Error loading scrapers: {e}")
    
    def get_scraper(self, name: str) -> Optional[BaseScraper]:
        """
        Get a specific scraper by name.
        
        Args:
            name: Name of the scraper
            
        Returns:
            BaseScraper instance or None
        """
        for scraper in self.scrapers:
            if scraper.name == name:
                return scraper
        return None
    
    def search_all(
        self,
        query: str,
        series: Optional[str] = None,
        volume: Optional[int] = None,
        year: Optional[int] = None,
        limit: int = 10,
        parallel: bool = True,
        max_workers: int = 5
    ) -> Dict[str, List[ScraperResult]]:
        """
        Search for albums across all enabled scrapers.
        
        Args:
            query: Search query string
            series: Optional series name filter
            volume: Optional volume number filter
            year: Optional publication year filter
            limit: Maximum results per scraper
            parallel: Whether to search scrapers in parallel
            max_workers: Maximum parallel workers
            
        Returns:
            Dictionary mapping scraper names to their results
        """
        if not self._loaded:
            self.load_scrapers()
        
        results = {}
        
        if parallel and len(self.scrapers) > 1:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_scraper = {
                    executor.submit(
                        scraper.search, query, series, volume, year, limit
                    ): scraper
                    for scraper in self.scrapers
                }
                
                for future in as_completed(future_to_scraper):
                    scraper = future_to_scraper[future]
                    try:
                        scraper_results = future.result()
                        results[scraper.name] = scraper_results
                        self.logger.debug(f"{scraper.name}: {len(scraper_results)} results")
                    except Exception as e:
                        self.logger.error(f"Error searching {scraper.name}: {e}")
                        results[scraper.name] = []
        else:
            # Sequential execution
            for scraper in self.scrapers:
                try:
                    scraper_results = scraper.search(query, series, volume, year, limit)
                    results[scraper.name] = scraper_results
                    self.logger.debug(f"{scraper.name}: {len(scraper_results)} results")
                except Exception as e:
                    self.logger.error(f"Error searching {scraper.name}: {e}")
                    results[scraper.name] = []
        
        return results
    
    def search_best(
        self,
        query: str,
        series: Optional[str] = None,
        volume: Optional[int] = None,
        year: Optional[int] = None,
        min_confidence: float = 50.0,
        limit: int = 10
    ) -> List[ScraperResult]:
        """
        Search across all scrapers and return best results merged.
        
        Args:
            query: Search query string
            series: Optional series name filter
            volume: Optional volume number filter
            year: Optional publication year filter
            min_confidence: Minimum confidence threshold
            limit: Maximum results to return
            
        Returns:
            List of best ScraperResult objects, sorted by confidence
        """
        all_results = self.search_all(query, series, volume, year, limit)
        
        # Flatten all results
        merged = []
        for scraper_name, scraper_results in all_results.items():
            for result in scraper_results:
                if result.confidence >= min_confidence:
                    merged.append(result)
        
        # Sort by confidence (highest first)
        merged.sort(key=lambda r: r.confidence, reverse=True)
        
        return merged[:limit]
    
    def get_details(self, url: str, scraper_name: Optional[str] = None) -> Optional[ScraperResult]:
        """
        Get detailed metadata for an album.
        
        Args:
            url: URL of the album page
            scraper_name: Optional specific scraper to use
            
        Returns:
            ScraperResult with details, or None
        """
        if not self._loaded:
            self.load_scrapers()
        
        if scraper_name:
            # Use specific scraper
            scraper = self.get_scraper(scraper_name)
            if scraper:
                try:
                    return scraper.get_details(url)
                except Exception as e:
                    self.logger.error(f"Error getting details from {scraper_name}: {e}")
            return None
        else:
            # Try to determine scraper from URL
            for scraper in self.scrapers:
                # Check if URL matches scraper's domain
                if any(domain in url for domain in [scraper.name, scraper.name.replace('_', '')]):
                    try:
                        return scraper.get_details(url)
                    except Exception as e:
                        self.logger.error(f"Error getting details from {scraper.name}: {e}")
            
            self.logger.warning(f"No scraper found for URL: {url}")
            return None
    
    def list_scrapers(self) -> List[Dict[str, Any]]:
        """
        Get information about all loaded scrapers.
        
        Returns:
            List of scraper info dictionaries
        """
        if not self._loaded:
            self.load_scrapers()
        
        return [
            {
                'name': scraper.name,
                'priority': scraper.priority,
                'enabled': scraper.is_enabled,
                'class': scraper.__class__.__name__
            }
            for scraper in self.scrapers
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get plugin manager statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self._loaded:
            self.load_scrapers()
        
        return {
            'total_scrapers': len(self.scrapers),
            'enabled_scrapers': len([s for s in self.scrapers if s.is_enabled]),
            'disabled_scrapers': len([s for s in self.scrapers if not s.is_enabled]),
            'scrapers': [s.name for s in self.scrapers]
        }
