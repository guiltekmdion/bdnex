"""
Batch processing module for handling multiple BD files with deferred challenge UI.
Collects low-confidence matches and processes them at the end in bulk.
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ProcessingResult:
    """Result of processing a single BD file."""
    filename: str
    success: bool
    score: float
    title: str = "Unknown"
    error: Optional[str] = None
    metadata: Optional[Dict] = None
    candidates: Optional[List[Tuple[Dict, float, str]]] = None  # For challenge UI later
    cover_path: Optional[str] = None


class BatchProcessor:
    """Process multiple BD files with deferred low-confidence challenge UI."""
    
    def __init__(self, interactive: bool = True, strict_mode: bool = False):
        """
        Initialize batch processor.
        
        Args:
            interactive: If True, show challenge UI for low-confidence matches
            strict_mode: If True, reject low-confidence matches instead of showing challenge
        """
        self.logger = logging.getLogger(__name__)
        self.interactive = interactive
        self.strict_mode = strict_mode
        self.results: List[ProcessingResult] = []
        self.low_confidence_results: List[ProcessingResult] = []
    
    def add_result(self, result: ProcessingResult):
        """Add processing result to batch."""
        self.results.append(result)
        
        if not result.success or (result.score >= 0 and result.score < 0.70):
            self.low_confidence_results.append(result)
    
    def get_statistics(self) -> Dict:
        """Get batch processing statistics."""
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        low_confidence = len(self.low_confidence_results)
        
        return {
            'total': total,
            'successful': successful,
            'failed': total - successful,
            'low_confidence': low_confidence,
            'success_rate': (successful / total * 100) if total > 0 else 0,
        }
    
    def get_low_confidence_results(self) -> List[Dict]:
        """
        Get low-confidence results formatted for batch challenge UI.
        
        Returns:
            List of dicts with 'filename', 'score', 'candidates', 'cover_path'
        """
        formatted = []
        for result in self.low_confidence_results:
            if result.cover_path and result.candidates:
                formatted.append({
                    'filename': result.filename,
                    'score': result.score,
                    'candidates': result.candidates,
                    'cover_path': result.cover_path,
                })
        return formatted

    
    def print_summary(self):
        """Print batch processing summary."""
        stats = self.get_statistics()
        
        separator = "=" * 70
        self.logger.info(separator)
        self.logger.info(f"RÉSUMÉ DU TRAITEMENT PAR LOT")
        self.logger.info(f"Total: {stats['total']} fichiers")
        self.logger.info(f"Réussis: {stats['successful']}")
        self.logger.info(f"Échoués: {stats['failed']}")
        self.logger.info(f"Taux de réussite: {stats['success_rate']:.1f}%")
        self.logger.info(f"Faible confiance: {stats['low_confidence']}")
        self.logger.info(separator)
        
        # List failed files
        failed = [r for r in self.results if not r.success]
        if failed:
            self.logger.warning(f"\nFichiers échoués ({len(failed)}):")
            for result in failed:
                self.logger.warning(f"  - {result.filename}: {result.error}")
        
        # List low confidence files
        if self.low_confidence_results:
            self.logger.warning(f"\nFichiers avec faible confiance ({len(self.low_confidence_results)}):")
            for result in self.low_confidence_results:
                self.logger.warning(f"  - {result.filename}: {result.score * 100:.1f}%")
