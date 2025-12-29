"""
Base Scraper Interface for BDneX - Phase 4 Plugin System

Defines the abstract base class that all metadata scrapers must implement.
Provides a common interface for searching albums and retrieving metadata.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScraperResult:
    """Result from a metadata scraper."""
    
    # Required fields
    source: str  # Name of the scraper (e.g., "bedetheque", "bdgest")
    url: str  # URL to the album page
    confidence: float  # Confidence score 0-100
    
    # Core metadata
    title: str
    series: Optional[str] = None
    volume: Optional[int] = None
    
    # Extended metadata
    writer: Optional[str] = None
    penciller: Optional[str] = None
    colorist: Optional[str] = None
    inker: Optional[str] = None
    editor: Optional[str] = None  # Publisher
    year: Optional[int] = None
    isbn: Optional[str] = None
    pages: Optional[int] = None
    format: Optional[str] = None
    summary: Optional[str] = None
    
    # Cover and images
    cover_url: Optional[str] = None
    cover_data: Optional[bytes] = None
    
    # Additional data
    extra: Dict[str, Any] = None
    retrieved_at: datetime = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}
        if self.retrieved_at is None:
            self.retrieved_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'source': self.source,
            'url': self.url,
            'confidence': self.confidence,
            'title': self.title,
            'series': self.series,
            'volume': self.volume,
            'writer': self.writer,
            'penciller': self.penciller,
            'colorist': self.colorist,
            'inker': self.inker,
            'editor': self.editor,
            'year': self.year,
            'isbn': self.isbn,
            'pages': self.pages,
            'format': self.format,
            'summary': self.summary,
            'cover_url': self.cover_url,
            'extra': self.extra,
            'retrieved_at': self.retrieved_at.isoformat() if self.retrieved_at else None
        }


class BaseScraper(ABC):
    """Abstract base class for metadata scrapers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize scraper.
        
        Args:
            config: Configuration dictionary (timeout, cache, etc.)
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.config = config or {}
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        self.enabled = self.config.get('enabled', True)
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the scraper (e.g., "bedetheque", "bdgest")."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """
        Return the priority of this scraper (lower = higher priority).
        Used when merging results from multiple sources.
        """
        pass
    
    @property
    def is_enabled(self) -> bool:
        """Check if scraper is enabled."""
        return self.enabled
    
    @abstractmethod
    def search(
        self,
        query: str,
        series: Optional[str] = None,
        volume: Optional[int] = None,
        year: Optional[int] = None,
        limit: int = 10
    ) -> List[ScraperResult]:
        """
        Search for albums matching the query.
        
        Args:
            query: Search query string
            series: Optional series name to filter by
            volume: Optional volume number to filter by
            year: Optional publication year to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of ScraperResult objects
        """
        pass
    
    @abstractmethod
    def get_details(self, url: str) -> Optional[ScraperResult]:
        """
        Get detailed metadata for a specific album.
        
        Args:
            url: URL of the album page
            
        Returns:
            ScraperResult with detailed metadata, or None if not found
        """
        pass
    
    def download_cover(self, cover_url: str) -> Optional[bytes]:
        """
        Download cover image from URL.
        
        Args:
            cover_url: URL of the cover image
            
        Returns:
            Image data as bytes, or None if download failed
        """
        try:
            import requests
            response = requests.get(cover_url, timeout=self.timeout)
            response.raise_for_status()
            return response.content
        except Exception as e:
            self.logger.error(f"Error downloading cover from {cover_url}: {e}")
            return None
    
    def normalize_isbn(self, isbn: str) -> Optional[str]:
        """
        Normalize ISBN format (remove hyphens, spaces).
        
        Args:
            isbn: ISBN string
            
        Returns:
            Normalized ISBN or None
        """
        if not isbn:
            return None
        # Remove common separators
        normalized = isbn.replace('-', '').replace(' ', '').strip()
        # Validate length (ISBN-10 or ISBN-13)
        if len(normalized) in (10, 13) and normalized.isdigit():
            return normalized
        return None
    
    def validate_result(self, result: ScraperResult) -> bool:
        """
        Validate that a result has minimum required fields.
        
        Args:
            result: ScraperResult to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Must have at least title and source
        if not result.title or not result.source:
            return False
        
        # Confidence must be between 0 and 100
        if result.confidence < 0 or result.confidence > 100:
            return False
        
        # URL should be valid
        if not result.url or not result.url.startswith('http'):
            return False
        
        return True
    
    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"<{self.__class__.__name__}(name={self.name}, priority={self.priority}, {status})>"
