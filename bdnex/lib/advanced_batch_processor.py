"""
Batch processor amélioré avec multiprocessing, retry logic et logging.
"""
import logging
import os
from typing import List, Dict, Any, Optional
from multiprocessing import Pool, cpu_count
from functools import partial

from bdnex.lib.batch_config import BatchConfig
from bdnex.lib.database import BDneXDB


class AdvancedBatchProcessor:
    """
    Processeur batch avec:
    - Multiprocessing pour traiter en parallèle
    - Retry logic pour erreurs réseau
    - Cache persistant des sitemaps
    - Logging détaillé en JSON/CSV
    """
    
    def __init__(
        self,
        batch_mode: bool = True,
        strict_mode: bool = False,
        num_workers: int = 4,
        output_dir: Optional[str] = None,
        use_database: bool = True,
        skip_processed: bool = False,
    ):
        """
        Initialize advanced batch processor.
        
        Args:
            batch_mode: Enable batch mode (disables interactive UI)
            strict_mode: Reject low-confidence matches
            num_workers: Number of parallel workers (1-8)
            output_dir: Directory for results and logs
            use_database: Enable database tracking (default True)
            skip_processed: Skip files already processed (requires database)
        """
        self.logger = logging.getLogger(__name__)
        self.config = BatchConfig(
            batch_mode=batch_mode,
            strict_mode=strict_mode,
            num_workers=num_workers,
            output_dir=output_dir
        )
        
        # Initialize database if enabled
        self.db = None
        self.session_id = None
        self.skip_processed = skip_processed
        
        # Enable database if either tracking or skip_processed is requested
        self.use_database = use_database
        
        if self.use_database:
            try:
                self.db = BDneXDB()
                self.logger.info("Database enabled for tracking processed files")
            except Exception as e:
                self.logger.warning(f"Could not initialize database: {e}, continuing without DB")
                self.db = None
                self.use_database = False
        
        self.logger.info(f"Batch processor initialisé: {num_workers} workers, "
                        f"mode={'batch' if batch_mode else 'interactif'}, "
                        f"mode={'strict' if strict_mode else 'normal'}")
    
    def load_session_files(self, session_id: int) -> List[str]:
        """
        Load unprocessed files from a previous session.
        
        Args:
            session_id: Session ID to resume
            
        Returns:
            List of file paths that haven't been processed yet
        """
        if not self.db:
            self.logger.error("Database not available, cannot load session files")
            return []
        
        try:
            # Get all files from the session
            all_files = self.db.get_session_files(session_id)
            
            # Filter to only unprocessed files
            unprocessed = [f for f in all_files if not f['processed']]
            
            self.logger.info(f"Session {session_id}: {len(unprocessed)} files remaining to process")
            return [f['file_path'] for f in unprocessed]
        except Exception as e:
            self.logger.error(f"Error loading session files: {e}")
            return []
    
    def process_files_parallel(
        self,
        file_list: List[str],
        directory: Optional[str] = None,
        interactive: bool = False,
        strict_mode: bool = False,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple BD files in parallel.
        
        Args:
            file_list: List of file paths to process
            directory: Directory being processed (for database tracking)
            interactive: Enable interactive challenge UI
            strict_mode: Reject low-confidence matches
            max_retries: Retry attempts on error
        
        Returns:
            List of result dicts
        """
        from bdnex.lib.batch_worker import process_single_file
        
        # Start database session if enabled
        if self.use_database and directory:
            self.session_id = self.db.start_session(
                directory=directory,
                batch_mode=self.config.batch_mode,
                strict_mode=self.config.strict_mode,
                num_workers=self.config.num_workers,
            )
            self.logger.info(f"Database session started: {self.session_id}")
        
        # Filter out already-processed files if requested
        todo_files = file_list
        if self.skip_processed and self.use_database:
            todo_files = [f for f in file_list if not self.db.is_processed(f)]
            skipped = len(file_list) - len(todo_files)
            if skipped > 0:
                self.logger.info(f"Skipping {skipped} already-processed files")
        
        self.logger.info(f"Traitement de {len(todo_files)} fichiers avec {self.config.num_workers} workers")
        
        # Create partial function with fixed arguments
        worker_func = partial(
            process_single_file,
            interactive=interactive,
            strict_mode=strict_mode,
            max_retries=max_retries,
        )
        
        results = []
        processed = 0
        
        try:
            with Pool(processes=self.config.num_workers) as pool:
                # Use imap_unordered to process results as they complete
                for result in pool.imap_unordered(worker_func, todo_files, chunksize=1):
                    results.append(result)
                    self.config.add_result(result)
                    
                    # Record in database if enabled
                    if self.use_database and self.session_id:
                        try:
                            self.db.record_processing(
                                result.get('filename', ''),
                                self.session_id,
                                result
                            )
                        except Exception as e:
                            self.logger.warning(f"Could not record file in database: {e}")
                    
                    processed += 1
                    success_str = "✓" if result.get('success') else "✗"
                    score_str = f"{result.get('score', 0) * 100:.0f}%" if result.get('score') else "N/A"
                    self.logger.info(f"[{processed}/{len(todo_files)}] {success_str} {result.get('filename')} ({score_str})")
        
        except KeyboardInterrupt:
            self.logger.warning("Interruption utilisateur - arrêt du traitement")
            # Update session as paused in database
            if self.use_database and self.session_id:
                self.db.update_session(
                    self.session_id,
                    status='paused',
                    files_processed=processed,
                )
            pool.terminate()
            pool.join()
        except Exception as e:
            self.logger.error(f"Erreur pool multiprocessing: {e}")
            raise
        
        return results
    
    def process_files_sequential(
        self,
        file_list: List[str],
        interactive: bool = False,
        strict_mode: bool = False,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Process files sequentially (for testing/debugging).
        
        Args:
            file_list: List of file paths to process
            interactive: Enable interactive challenge UI
            strict_mode: Reject low-confidence matches
            max_retries: Retry attempts on error
        
        Returns:
            List of result dicts
        """
        from bdnex.lib.batch_worker import process_single_file
        
        self.logger.info(f"Traitement séquentiel de {len(file_list)} fichiers")
        
        results = []
        for idx, filename in enumerate(file_list, 1):
            try:
                result = process_single_file(
                    filename,
                    interactive=interactive,
                    strict_mode=strict_mode,
                    max_retries=max_retries,
                )
                results.append(result)
                self.config.add_result(result)
                
                success_str = "✓" if result.get('success') else "✗"
                score_str = f"{result.get('score', 0) * 100:.0f}%" if result.get('score') else "N/A"
                self.logger.info(f"[{idx}/{len(file_list)}] {success_str} {result.get('filename')} ({score_str})")
            
            except KeyboardInterrupt:
                self.logger.warning("Interruption utilisateur - arrêt du traitement")
                break
            except Exception as e:
                self.logger.error(f"Erreur traitement {filename}: {e}")
        
        return results
    
    def get_low_confidence_files(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Get list of files with low confidence scores.
        
        Args:
            results: List of processing results
        
        Returns:
            List of filenames with low confidence
        """
        low_confidence = []
        for result in results:
            if not result.get('success') or (result.get('score', 1) < 0.70):
                low_confidence.append(result.get('filename'))
        
        return low_confidence
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """
        Print and save batch processing summary.
        
        Args:
            results: List of processing results
        """
        total = len(results)
        successful = sum(1 for r in results if r.get('success'))
        failed = total - successful
        low_confidence = len(self.get_low_confidence_files(results))
        
        success_rate = (successful / total * 100) if total > 0 else 0
        
        # Update database session if enabled
        if self.use_database and self.session_id:
            self.db.update_session(
                self.session_id,
                total_files=total,
                files_processed=total,
                files_successful=successful,
                files_failed=failed,
                status='completed',
            )
            self.logger.debug(f"Database session {self.session_id} updated and marked completed")
        
        separator = "=" * 70
        self.logger.info(separator)
        self.logger.info(f"RÉSUMÉ DU TRAITEMENT PAR LOT")
        self.logger.info(f"Fichiers traités: {total}")
        self.logger.info(f"Réussis: {successful}")
        self.logger.info(f"Échoués: {failed}")
        self.logger.info(f"Taux de réussite: {success_rate:.1f}%")
        self.logger.info(f"Faible confiance: {low_confidence}")
        if self.use_database and self.session_id:
            self.logger.info(f"Session database: {self.session_id}")
        self.logger.info(separator)
        
        # List failed files
        failed_files = [r for r in results if not r.get('success')]
        if failed_files:
            self.logger.warning(f"\nFichiers échoués ({len(failed_files)}):")
            for result in failed_files[:10]:  # Show first 10
                self.logger.warning(f"  - {result.get('filename')}: {result.get('error')}")
            if len(failed_files) > 10:
                self.logger.warning(f"  ... et {len(failed_files) - 10} autres")
        
        # List low confidence files
        if low_confidence:
            self.logger.warning(f"\nFichiers avec faible confiance ({low_confidence}):")
            for fname in low_confidence[:10]:  # Show first 10
                self.logger.warning(f"  - {fname}")
            if len(low_confidence) > 10:
                self.logger.warning(f"  ... et {len(low_confidence) - 10} autres")
        
        # Save logs
        self.config.save_json_log()
        self.config.save_csv_log()
        
        self.logger.info(f"Résultats: {self.config.json_log}")
