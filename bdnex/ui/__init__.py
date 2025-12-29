#!/usr/bin/env python3
import os
import logging
import shutil
import http.server
import socketserver
import json
from threading import Thread
from urllib.parse import urlparse, parse_qs

from bdnex.lib.archive_tools import archive_get_front_cover
from bdnex.lib.bdgest import BdGestParse
from bdnex.lib.comicrack import comicInfo
from bdnex.lib.cover import front_cover_similarity, get_bdgest_cover
from bdnex.lib.utils import yesno, args, bdnex_config
from bdnex.lib.disambiguation import FilenameMetadataExtractor, CandidateScorer
from bdnex.lib.batch_processor import ProcessingResult
from bdnex.ui.challenge import ChallengeUI
from bdnex.ui.batch_challenge import BatchChallengeUI
from pathlib import Path
from termcolor import colored


def add_metadata_from_bdgest(filename, batch_processor=None, interactive=True, strict_mode=False):
    """
    Add metadata from Bédéthèque to a BD file.
    
    Args:
        filename: Path to the BD file (CBZ/CBR)
        batch_processor: Optional BatchProcessor for collecting results
        interactive: Whether to show challenge UI on low confidence
        strict_mode: If True, skip low-confidence matches instead of asking
    
    Returns:
        ProcessingResult with success/failure info
    """
    bdnex_conf = bdnex_config()
    logger = logging.getLogger(__name__)
    start_separator = colored(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~',
                              'red', attrs=['bold'])

    logger.info(start_separator)
    logger.info(f"Traitement de {filename}")

    album_name = os.path.splitext(os.path.basename(filename))[0]
    filename_basename = os.path.basename(filename)

    try:
        # Extract archive cover first for disambiguation
        cover_archive_fp = archive_get_front_cover(filename)

        # Extract filename metadata
        extractor = FilenameMetadataExtractor()
        filename_volume = extractor.extract_volume_number(album_name)

        # Try disambiguation using multi-criteria scoring across top fuzzy candidates
        parser = BdGestParse()
        candidates = parser.search_album_candidates_fast(album_name, top_k=5)
        
        # Score all candidates
        scored_candidates = []
        cover_similarities = []
        candidate_covers = []
        
        for _, _, url in candidates:
            try:
                bd_meta_candidate, comicrack_meta_candidate = parser.parse_album_metadata_mobile(album_name, album_url=url)
                cover_web_fp_candidate = get_bdgest_cover(bd_meta_candidate["cover_url"])
                sim = front_cover_similarity(cover_archive_fp, cover_web_fp_candidate)
                
                cover_similarities.append(sim)
                candidate_covers.append(cover_web_fp_candidate)
                
                # Extract year from Dépot_légal if present
                candidate_year = -1
                try:
                    if 'Dépot_légal' in bd_meta_candidate:
                        published_date = parser.parse_date_from_depot_legal(bd_meta_candidate['Dépot_légal'])
                        if published_date:
                            candidate_year = published_date.year
                except:
                    pass
                
                # Build candidate metadata dict
                candidate_meta = {
                    'title': bd_meta_candidate.get('Titre', 'Unknown'),
                    'volume': bd_meta_candidate.get('Tome', -1),
                    'editor': bd_meta_candidate.get('Éditeur', 'Unknown'),
                    'year': candidate_year,
                    'pages': bd_meta_candidate.get('Planches', '?'),
                    'url': url,
                    'comicrack_meta': comicrack_meta_candidate,
                    'cover_path': cover_web_fp_candidate,
                }
                scored_candidates.append(candidate_meta)
            except Exception as e:
                logger.debug(f"Error processing candidate: {e}")
                continue

        if not scored_candidates:
            error_msg = "No valid candidates found"
            logger.error(error_msg)
            result = ProcessingResult(
                filename=filename_basename,
                success=False,
                score=0.0,
                title="Unknown",
                error=error_msg
            )
            if batch_processor:
                batch_processor.add_result(result)
            return result

        # Filename metadata
        filename_metadata = {
            'volume': filename_volume,
            'title': album_name,
            'editor': 'unknown',
            'year': -1,
        }

        # Score candidates
        scorer = CandidateScorer()
        scored = scorer.score_candidates(filename_metadata, scored_candidates, cover_similarities)
        
        best_candidate, best_score = scored[0]
        
        logger.info(f"Score de meilleure correspondance: {best_score * 100:.1f}%")
        
        # Determine if we need challenge UI
        challenge_threshold = bdnex_conf['cover'].get('challenge_threshold', 0.70)  # Default 70%
        selected_score = best_score  # Default to best_score
        
        if best_score >= challenge_threshold:
            # High confidence, use automatically
            logger.info(f"Correspondance de haute confiance ({best_score * 100:.1f}%). Utilisation automatique.")
            bdgest_meta = {k: v for k, v in best_candidate.items() if k not in ['comicrack_meta', 'cover_path']}
            comicrack_meta = best_candidate['comicrack_meta']
            cover_web_fp = best_candidate['cover_path']
            selected_score = best_score
        else:
            # Low confidence
            logger.warning(f"Correspondance de faible confiance ({best_score * 100:.1f}%). Score: {best_score * 100:.1f}%")
            
            if strict_mode:
                # In strict mode, skip low-confidence matches
                logger.info(f"Mode strict: fichier ignoré (confiance insuffisante)")
                result = ProcessingResult(
                    filename=filename_basename,
                    success=False,
                    score=best_score,
                    title=best_candidate.get('title', 'Unknown'),
                    error="Confiance insuffisante (mode strict)",
                    candidates=[(c.get('title', 'Unknown'), s, c.get('cover_path', '')) for c, s in scored[:3]],
                    cover_path=cover_archive_fp
                )
                if batch_processor:
                    batch_processor.add_result(result)
                cover_path = Path(cover_archive_fp).parent.as_posix()
                shutil.rmtree(cover_path)
                return result
            
            if not interactive:
                # In batch mode (non-interactive), collect for later review
                result = ProcessingResult(
                    filename=filename_basename,
                    success=False,
                    score=best_score,
                    title=best_candidate.get('title', 'Unknown'),
                    error="Confiance insuffisante (révision requise)",
                    candidates=[(c.get('title', 'Unknown'), s, c.get('cover_path', '')) for c, s in scored[:3]],
                    cover_path=cover_archive_fp,
                    metadata=filename_metadata
                )
                if batch_processor:
                    batch_processor.add_result(result)
                return result
            
            # Interactive mode: show challenge
            logger.warning(f"Affichage de l'interface de désambiguation.")
            
            # Prepare candidates for challenge (top 3)
            challenge_candidates = []
            for candidate, score in scored[:3]:
                challenge_candidates.append((candidate, score, candidate['cover_path']))
            
            # Show challenge
            challenge_ui = ChallengeUI()
            selected_idx = challenge_ui.show_challenge_interactive(
                cover_archive_fp,
                challenge_candidates,
                filename_basename
            )
            
            if selected_idx is not None and selected_idx >= 0 and selected_idx < len(challenge_candidates):
                selected_candidate = challenge_candidates[selected_idx][0]
                logger.info(f"Candidat sélectionné par l'utilisateur: {selected_candidate['title']}")
                bdgest_meta = {k: v for k, v in selected_candidate.items() if k not in ['comicrack_meta', 'cover_path']}
                comicrack_meta = selected_candidate['comicrack_meta']
                cover_web_fp = selected_candidate['cover_path']
                selected_score = challenge_candidates[selected_idx][1]
            else:
                # Fallback to manual selection (user clicked "None of these")
                logger.info(f"Utilisateur a rejeté tous les candidats. Début de la recherche manuelle pour {colored(filename_basename, 'red', attrs=['bold'])}")
                album_url = BdGestParse().search_album_from_sitemaps_interactive()
                bdgest_meta, comicrack_meta = BdGestParse().parse_album_metadata_mobile(album_name, album_url=album_url)
                cover_web_fp = get_bdgest_cover(bdgest_meta["cover_url"])
                selected_score = 1.0  # Manual search considered 100% confident

        # Final check and apply metadata
        percentage_similarity = front_cover_similarity(cover_archive_fp, cover_web_fp)

        if percentage_similarity > bdnex_conf['cover'].get('match_percentage', 50):
            comicInfo(filename, comicrack_meta).append_comicinfo_to_archive()
            logger.info(f"Métadonnées appliquées avec succès")
            result = ProcessingResult(
                filename=filename_basename,
                success=True,
                score=best_score if best_score >= challenge_threshold else selected_score,
                title=bdgest_meta.get('title', 'Unknown'),
                metadata=bdgest_meta
            )
            if batch_processor:
                batch_processor.add_result(result)
        else:
            logger.warning("Confiance de correspondance de couverture faible")
            if interactive:
                ans = yesno("La correspondance de couverture a une confiance faible. Voulez-vous quand même ajouter les métadonnées ?")
            else:
                ans = False  # Skip in batch mode on low cover match
            
            if ans:
                comicInfo(filename, comicrack_meta).append_comicinfo_to_archive()
                logger.info(f"Métadonnées appliquées avec succès")
                result = ProcessingResult(
                    filename=filename_basename,
                    success=True,
                    score=best_score if best_score >= challenge_threshold else selected_score,
                    title=bdgest_meta.get('title', 'Unknown'),
                    metadata=bdgest_meta
                )
                if batch_processor:
                    batch_processor.add_result(result)
            else:
                logger.info(f"Recherche manuelle pour {colored(filename_basename, 'red', attrs=['bold'])}")
                album_url = BdGestParse().search_album_from_sitemaps_interactive()
                bdgest_meta, comicrack_meta = BdGestParse().parse_album_metadata_mobile(album_name, album_url=album_url)
                comicInfo(filename, comicrack_meta).append_comicinfo_to_archive()
                logger.info(f"Métadonnées appliquées avec succès")
                result = ProcessingResult(
                    filename=filename_basename,
                    success=True,
                    score=1.0,
                    title=bdgest_meta.get('title', 'Unknown'),
                    metadata=bdgest_meta
                )
                if batch_processor:
                    batch_processor.add_result(result)

        cover_path = Path(cover_archive_fp).parent.as_posix()
        shutil.rmtree(cover_path)

        logger.info(f"Traitement de l'album terminé")
        return result

    except Exception as e:
        logger.error(f"Erreur lors du traitement: {str(e)}")
        result = ProcessingResult(
            filename=filename_basename,
            success=False,
            score=0.0,
            title="Unknown",
            error=str(e)
        )
        if batch_processor:
            batch_processor.add_result(result)
        return result


def main():
    """Main entry point with advanced batch processing support."""
    from bdnex.lib.batch_config import SitemapCache
    from bdnex.lib.advanced_batch_processor import AdvancedBatchProcessor
    from bdnex.lib.cli_session_manager import CLISessionManager
    
    vargs = args()
    logger = logging.getLogger(__name__)

    # Database-aware CLI commands (Phase 2A)
    cli_manager = CLISessionManager()
    session_handled = cli_manager.handle_cli_session_args(vargs)
    
    # Handle different return types from CLI manager
    resume_session_id = None
    if session_handled is True:
        # Command completed successfully (--list-sessions or --session-info)
        return
    elif session_handled is False:
        # Command failed
        return
    elif isinstance(session_handled, tuple) and session_handled[0] == 'resume':
        # Resume mode requested
        resume_session_id = session_handled[1]
        logger.info(f"Resuming session {resume_session_id}...")
        # Continue processing with resume mode enabled

    # Determine skip/force flags
    skip_processed = bool(vargs.skip_processed) and not bool(getattr(vargs, 'force_reprocess', False))

    if vargs.init:
        BdGestParse().download_sitemaps()

    if vargs.input_dir:
        dirpath = vargs.input_dir
        files = []

        for path in Path(dirpath).rglob('*.cbz'):
            files.append(path.absolute().as_posix())

        for path in Path(dirpath).rglob('*.cbr'):
            files.append(path.absolute().as_posix())

        logger.info(f"Trouvé {len(files)} fichier(s) BD à traiter")
        
        # Use advanced batch processor for parallel processing
        processor = AdvancedBatchProcessor(
            batch_mode=vargs.batch,
            strict_mode=vargs.strict,
            num_workers=4,  # Default 4 workers
            use_database=True,
            skip_processed=skip_processed,
        )
        
        # If resuming a session, load files from that session
        if resume_session_id is not None:
            logger.info(f"Chargement de la session {resume_session_id}...")
            files = processor.load_session_files(resume_session_id)
            if not files:
                logger.warning("Aucun fichier à reprendre dans cette session")
                return
            # Use the resume_session to create a new child session
            new_session_id = processor.db.resume_session(resume_session_id)
            processor.session_id = new_session_id
            logger.info(f"Session reprise avec nouvel ID: {new_session_id}")
        
        # Process files (parallel if multiple workers)
        if processor.config.num_workers > 1 and len(files) > 1:
            results = processor.process_files_parallel(
                files,
                directory=dirpath,
                interactive=not vargs.batch,  # Interactive only if not batch mode
                strict_mode=vargs.strict,
                max_retries=3,
            )
        else:
            results = processor.process_files_sequential(
                files,
                interactive=not vargs.batch,
                strict_mode=vargs.strict,
                max_retries=3,
            )
        
        # After all files processed in batch mode, show consolidated challenge UI if needed
        low_conf_files = processor.get_low_confidence_files(results)
        if low_conf_files and not vargs.strict and not vargs.batch:
            logger.info(f"\n{len(low_conf_files)} fichier(s) nécessite(nt) une révision manuelle")
            batch_challenge = BatchChallengeUI()
            try:
                # TODO: Implement consolidated challenge UI for low-confidence files
                logger.info("Révision par lot des fichiers avec faible confiance")
            except Exception as e:
                logger.warning(f"Interface de révision indisponible: {e}")
        
        # Print summary and save logs
        processor.print_summary(results)

    elif vargs.input_file:
        file = vargs.input_file

        # Skip if already processed and user requested skip
        if skip_processed and cli_manager.db and cli_manager.db.is_processed(file):
            logger.info(f"Fichier déjà traité, ignoré grâce à --skip-processed: {file}")
            return

        result = add_metadata_from_bdgest(
            file,
            batch_processor=None,
            interactive=True,
            strict_mode=False
        )
        if result:
            logger.info(f"Résultat: {result.filename} - {'✓ Succès' if result.success else '✗ Échoué'}")



