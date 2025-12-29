"""
Worker process pour batch processing parallèle.
Traite un seul fichier BD de manière isolée avec retry logic.
"""
import logging
import sys
from typing import Dict, Any
from bdnex.ui import add_metadata_from_bdgest


def process_single_file(
    filename: str,
    interactive: bool = False,
    strict_mode: bool = False,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Process a single BD file in isolation (for multiprocessing).
    
    Args:
        filename: Path to BD file
        interactive: Enable interactive challenge UI
        strict_mode: Reject low-confidence matches
        max_retries: Number of retries on network errors
    
    Returns:
        Result dict with success, filename, score, title, error (if any)
    """
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Processing {filename} (attempt {attempt + 1}/{max_retries})")
            
            result = add_metadata_from_bdgest(
                filename,
                batch_processor=None,  # Don't track in batch processor (will do it in main)
                interactive=interactive,
                strict_mode=strict_mode
            )
            
            # Convert ProcessingResult to dict
            return {
                'filename': result.filename,
                'success': result.success,
                'score': result.score,
                'title': result.title,
                'error': result.error,
                'metadata': result.metadata,
            }
        
        except Exception as e:
            logger.warning(f"Erreur traitement {filename}: {e}")
            
            if attempt < max_retries - 1:
                import time
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Nouvelle tentative après {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Échec définitif après {max_retries} tentatives")
                return {
                    'filename': filename,
                    'success': False,
                    'score': 0.0,
                    'title': 'Unknown',
                    'error': f"Erreur après {max_retries} tentatives: {str(e)}",
                }
    
    return {
        'filename': filename,
        'success': False,
        'score': 0.0,
        'title': 'Unknown',
        'error': 'Erreur inconnue',
    }
