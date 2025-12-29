"""
Metadata Merger for BDneX - Phase 4

Intelligently merges metadata from multiple scraper sources.
Resolves conflicts using configurable priority and confidence rules.
"""

import logging
from typing import List, Dict, Optional, Any
from collections import defaultdict
from datetime import datetime

from .base_scraper import ScraperResult


class MetadataMerger:
    """Merge and resolve metadata from multiple sources."""
    
    def __init__(self, priority_map: Optional[Dict[str, int]] = None):
        """
        Initialize metadata merger.
        
        Args:
            priority_map: Optional mapping of source names to priorities
                         (lower = higher priority)
        """
        self.logger = logging.getLogger(__name__)
        self.priority_map = priority_map or {}
    
    def merge_results(
        self,
        results: List[ScraperResult],
        strategy: str = "best_confidence",
        min_agreement: int = 2
    ) -> Optional[ScraperResult]:
        """
        Merge multiple scraper results into a single unified result.
        
        Args:
            results: List of ScraperResult objects to merge
            strategy: Merging strategy:
                     - "best_confidence": Use highest confidence result
                     - "priority": Use configured source priority
                     - "consensus": Require agreement from multiple sources
            min_agreement: Minimum sources that must agree (for consensus)
            
        Returns:
            Merged ScraperResult or None
        """
        if not results:
            return None
        
        if len(results) == 1:
            return results[0]
        
        if strategy == "best_confidence":
            return self._merge_by_confidence(results)
        elif strategy == "priority":
            return self._merge_by_priority(results)
        elif strategy == "consensus":
            return self._merge_by_consensus(results, min_agreement)
        else:
            self.logger.warning(f"Unknown strategy '{strategy}', using best_confidence")
            return self._merge_by_confidence(results)
    
    def _merge_by_confidence(self, results: List[ScraperResult]) -> ScraperResult:
        """Merge by selecting highest confidence result and supplementing."""
        # Sort by confidence (highest first)
        sorted_results = sorted(results, key=lambda r: r.confidence, reverse=True)
        base = sorted_results[0]
        
        # Supplement missing fields from other sources
        merged = self._create_merged_result(base)
        
        for result in sorted_results[1:]:
            self._fill_missing_fields(merged, result)
        
        return merged
    
    def _merge_by_priority(self, results: List[ScraperResult]) -> ScraperResult:
        """Merge by source priority configuration."""
        # Sort by priority (lower = higher priority)
        def get_priority(result: ScraperResult) -> int:
            return self.priority_map.get(result.source, 999)
        
        sorted_results = sorted(results, key=get_priority)
        base = sorted_results[0]
        
        merged = self._create_merged_result(base)
        
        for result in sorted_results[1:]:
            self._fill_missing_fields(merged, result)
        
        return merged
    
    def _merge_by_consensus(
        self, 
        results: List[ScraperResult],
        min_agreement: int = 2
    ) -> Optional[ScraperResult]:
        """Merge by requiring agreement across sources."""
        if len(results) < min_agreement:
            self.logger.warning(f"Not enough results ({len(results)}) for consensus (need {min_agreement})")
            return self._merge_by_confidence(results)
        
        # Analyze agreement for key fields
        field_values = defaultdict(lambda: defaultdict(int))
        
        for result in results:
            for field in ['title', 'series', 'volume', 'year', 'editor']:
                value = getattr(result, field, None)
                if value:
                    field_values[field][str(value)] += 1
        
        # Find consensus values (most common with min_agreement)
        consensus = {}
        for field, values in field_values.items():
            most_common = max(values.items(), key=lambda x: x[1])
            if most_common[1] >= min_agreement:
                consensus[field] = most_common[0]
        
        if not consensus:
            self.logger.warning("No consensus reached, falling back to confidence")
            return self._merge_by_confidence(results)
        
        # Build merged result from consensus
        base = sorted(results, key=lambda r: r.confidence, reverse=True)[0]
        merged = self._create_merged_result(base)
        
        # Apply consensus values
        for field, value in consensus.items():
            if hasattr(merged, field):
                setattr(merged, field, value)
        
        # Fill remaining fields
        for result in results:
            self._fill_missing_fields(merged, result)
        
        return merged
    
    def _create_merged_result(self, base: ScraperResult) -> ScraperResult:
        """Create a copy of base result for merging."""
        return ScraperResult(
            source=f"merged_{base.source}",
            url=base.url,
            confidence=base.confidence,
            title=base.title,
            series=base.series,
            volume=base.volume,
            writer=base.writer,
            penciller=base.penciller,
            colorist=base.colorist,
            inker=base.inker,
            editor=base.editor,
            year=base.year,
            isbn=base.isbn,
            pages=base.pages,
            format=base.format,
            summary=base.summary,
            cover_url=base.cover_url,
            cover_data=base.cover_data,
            extra=base.extra.copy() if base.extra else {},
            retrieved_at=datetime.now()
        )
    
    def _fill_missing_fields(self, target: ScraperResult, source: ScraperResult) -> None:
        """Fill missing fields in target from source."""
        fields = [
            'title', 'series', 'volume', 'writer', 'penciller', 'colorist',
            'inker', 'editor', 'year', 'isbn', 'pages', 'format', 'summary',
            'cover_url', 'cover_data'
        ]
        
        for field in fields:
            target_value = getattr(target, field, None)
            source_value = getattr(source, field, None)
            
            # Fill if target is missing and source has value
            if not target_value and source_value:
                setattr(target, field, source_value)
        
        # Merge extra fields
        if source.extra:
            if not target.extra:
                target.extra = {}
            target.extra.update(source.extra)
    
    def group_by_album(
        self,
        results: List[ScraperResult],
        similarity_threshold: float = 0.8
    ) -> List[List[ScraperResult]]:
        """
        Group results that likely refer to the same album.
        
        Args:
            results: List of ScraperResult objects
            similarity_threshold: Minimum similarity to group together
            
        Returns:
            List of groups, where each group is a list of similar results
        """
        if not results:
            return []
        
        groups = []
        
        for result in results:
            # Find best matching group
            best_group = None
            best_similarity = 0.0
            
            for group in groups:
                # Compare with first item in group
                similarity = self._calculate_similarity(result, group[0])
                if similarity > best_similarity and similarity >= similarity_threshold:
                    best_similarity = similarity
                    best_group = group
            
            if best_group is not None:
                best_group.append(result)
            else:
                groups.append([result])
        
        return groups
    
    def _calculate_similarity(self, r1: ScraperResult, r2: ScraperResult) -> float:
        """Calculate similarity score between two results (0-1)."""
        score = 0.0
        total_weight = 0.0
        
        # Series match (weight: 30%)
        if r1.series and r2.series:
            total_weight += 0.3
            if self._normalize_text(r1.series) == self._normalize_text(r2.series):
                score += 0.3
        
        # Volume match (weight: 25%)
        if r1.volume is not None and r2.volume is not None:
            total_weight += 0.25
            if r1.volume == r2.volume:
                score += 0.25
        
        # Title match (weight: 25%)
        if r1.title and r2.title:
            total_weight += 0.25
            if self._normalize_text(r1.title) == self._normalize_text(r2.title):
                score += 0.25
            elif self._normalize_text(r1.title) in self._normalize_text(r2.title) or \
                 self._normalize_text(r2.title) in self._normalize_text(r1.title):
                score += 0.15
        
        # Year match (weight: 10%)
        if r1.year and r2.year:
            total_weight += 0.1
            if abs(r1.year - r2.year) <= 1:
                score += 0.1
            elif abs(r1.year - r2.year) <= 2:
                score += 0.05
        
        # Publisher match (weight: 10%)
        if r1.editor and r2.editor:
            total_weight += 0.1
            if self._normalize_text(r1.editor) == self._normalize_text(r2.editor):
                score += 0.1
        
        # Normalize by total weight considered
        return score / total_weight if total_weight > 0 else 0.0
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        import unicodedata
        # Remove accents
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        # Lowercase and remove extra spaces
        return ' '.join(text.lower().split())
