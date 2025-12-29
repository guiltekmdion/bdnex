#!/usr/bin/env python3
import os
import logging
import shutil
import sys
import http.server
import socketserver
import json
from threading import Thread
from urllib.parse import urlparse, parse_qs

from bdnex.lib.archive_tools import archive_get_front_cover
from bdnex.lib.bdgest import BdGestParse
from bdnex.lib.comicrack import comicInfo
from bdnex.lib.renaming import RenameManager
from bdnex.lib.catalog_manager import CatalogManager
from bdnex.lib.cover import front_cover_similarity, get_bdgest_cover
from bdnex.lib.utils import yesno, args, bdnex_config
from bdnex.lib.disambiguation import FilenameMetadataExtractor, CandidateScorer
from bdnex.lib.batch_processor import ProcessingResult
from bdnex.lib.progress import progress_for
from bdnex.ui.challenge import ChallengeUI
from bdnex.ui.batch_challenge import BatchChallengeUI
from pathlib import Path
from termcolor import colored


def _scraper_result_to_candidate(sr):
    """Convert a ScraperResult to an internal candidate dict compatible with scoring/UI."""
    # ComicInfo keys (subset)
    comicrack_meta = {}
    if getattr(sr, 'series', None):
        comicrack_meta['Series'] = sr.series
    if getattr(sr, 'volume', None) is not None:
        comicrack_meta['Number'] = str(sr.volume)
    if getattr(sr, 'title', None):
        comicrack_meta['Title'] = sr.title
    if getattr(sr, 'writer', None):
        comicrack_meta['Writer'] = sr.writer
    if getattr(sr, 'penciller', None):
        comicrack_meta['Penciller'] = sr.penciller
    if getattr(sr, 'editor', None):
        comicrack_meta['Publisher'] = sr.editor
    if getattr(sr, 'year', None):
        comicrack_meta['Year'] = int(sr.year)

    return {
        'title': sr.title or 'Unknown',
        'series': getattr(sr, 'series', None) or 'Unknown',
        'volume': getattr(sr, 'volume', None) if getattr(sr, 'volume', None) is not None else -1,
        'editor': getattr(sr, 'editor', None) or 'Unknown',
        'year': getattr(sr, 'year', None) if getattr(sr, 'year', None) is not None else -1,
        'pages': getattr(sr, 'pages', None) or '?',
        'url': getattr(sr, 'url', None) or '#',
        'source': getattr(sr, 'source', None) or 'unknown',
        'comicrack_meta': comicrack_meta,
        'cover_url': getattr(sr, 'cover_url', None),
    }


def handle_file_renaming(result, rename_manager, template, logger):
    """
    Handle file renaming after metadata has been applied.
    
    Args:
        result: ProcessingResult containing filepath and metadata
        rename_manager: RenameManager instance
        template: Renaming template string
        logger: Logger instance
    
    Returns:
        Tuple (success, old_path, new_path)
    """
    if not result or not result.success or not hasattr(result, 'filepath'):
        return False, None, None
    
    filepath = result.filepath
    metadata = result.metadata if hasattr(result, 'metadata') else {}
    
    try:
        success, old_path, new_path = rename_manager.rename_file(filepath, template, metadata)
        
        if success:
            if old_path != new_path:
                if rename_manager.dry_run:
                    logger.info(f"[DRY-RUN] Renommage: {Path(old_path).name} → {Path(new_path).name}")
                else:
                    logger.info(f"Fichier renommé: {Path(old_path).name} → {Path(new_path).name}")
            return True, old_path, new_path
        else:
            logger.warning(f"Échec du renommage: {new_path}")
            return False, old_path, new_path
    except Exception as e:
        logger.error(f"Erreur lors du renommage: {e}")
        return False, filepath, str(e)


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

    filename = str(filename)
    file_path = os.path.abspath(filename)
    album_name = os.path.splitext(os.path.basename(file_path))[0]
    filename_basename = os.path.basename(file_path)

    try:
        # Extract archive cover first for disambiguation
        cover_archive_fp = archive_get_front_cover(file_path)

        # Extract filename metadata
        extractor = FilenameMetadataExtractor()
        filename_volume = extractor.extract_volume_number(album_name)
        filename_title = extractor.extract_title(album_name)

        # Try disambiguation using multi-criteria scoring across top fuzzy candidates
        parser = BdGestParse()
        candidates = parser.search_album_candidates_fast(album_name, top_k=5)
        
        # Score all candidates
        scored_candidates = []
        cover_similarities = []
        candidate_covers = []

        seen_urls = set()
        
        # candidates is expected to be a list of tuples (title, score, url)
        for _, _, url in (candidates or []):
            try:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                bd_meta_candidate, comicrack_meta_candidate = parser.parse_album_metadata_mobile(album_name, album_url=url)
                cover_web_fp_candidate = None
                sim = 0.0
                try:
                    cover_web_fp_candidate = get_bdgest_cover(bd_meta_candidate["cover_url"])
                    sim = front_cover_similarity(cover_archive_fp, cover_web_fp_candidate)
                except Exception as e:
                    logger.debug(f"Cover fetch/compare failed for candidate {url}: {e}")

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
                    'series': bd_meta_candidate.get('Série', 'Unknown'),
                    'volume': bd_meta_candidate.get('Tome', -1),
                    'editor': bd_meta_candidate.get('Éditeur', 'Unknown'),
                    'year': candidate_year,
                    'pages': bd_meta_candidate.get('Planches', '?'),
                    'url': url,
                    'source': 'bedetheque',
                    'comicrack_meta': comicrack_meta_candidate,
                    'cover_path': cover_web_fp_candidate,
                }
                candidate_meta['_cover_similarity'] = sim
                scored_candidates.append(candidate_meta)
            except Exception as e:
                logger.debug(f"Error processing candidate: {e}")
                continue

        # Backward-compatible fallback: if candidate search yields nothing (or is mocked),
        # try a single direct metadata parse to get at least one candidate.
        if not scored_candidates:
            try:
                bd_meta_candidate, comicrack_meta_candidate = parser.parse_album_metadata_mobile(album_name)
                cover_web_fp_candidate = get_bdgest_cover(bd_meta_candidate["cover_url"])
                sim = front_cover_similarity(cover_archive_fp, cover_web_fp_candidate)

                candidate_year = -1
                try:
                    if 'Dépot_légal' in bd_meta_candidate:
                        published_date = parser.parse_date_from_depot_legal(bd_meta_candidate['Dépot_légal'])
                        if published_date:
                            candidate_year = published_date.year
                except Exception:
                    pass

                candidate_meta = {
                    'title': bd_meta_candidate.get('Titre', bd_meta_candidate.get('title', 'Unknown')),
                    'series': bd_meta_candidate.get('Série', bd_meta_candidate.get('series', 'Unknown')),
                    'volume': bd_meta_candidate.get('Tome', bd_meta_candidate.get('volume', -1)),
                    'editor': bd_meta_candidate.get('Éditeur', bd_meta_candidate.get('editor', 'Unknown')),
                    'year': candidate_year,
                    'pages': bd_meta_candidate.get('Planches', bd_meta_candidate.get('pages', '?')),
                    'url': bd_meta_candidate.get('album_url', '#'),
                    'source': 'bedetheque',
                    'comicrack_meta': comicrack_meta_candidate,
                    'cover_path': cover_web_fp_candidate,
                }
                candidate_meta['_cover_similarity'] = sim
                scored_candidates.append(candidate_meta)
                cover_similarities.append(sim)
            except Exception as e:
                logger.debug(f"Direct metadata fallback unavailable: {e}")

        # Filename metadata
        filename_metadata = {
            'volume': filename_volume,
            'title': filename_title,
            'editor': 'unknown',
            'year': -1,
        }

        # Score candidates from bedetheque first (if any)
        scorer = CandidateScorer()
        scored = scorer.score_candidates(filename_metadata, scored_candidates, cover_similarities) if scored_candidates else []

        # If we have no candidates or low score, try external scrapers (BDGest/BDfugue)
        challenge_threshold = bdnex_conf['cover'].get('challenge_threshold', 0.70)  # Default 70%
        current_best_score = scored[0][1] if scored else 0.0
        if not scored_candidates or current_best_score < challenge_threshold:
            try:
                from bdnex.lib.scrapers.plugin_manager import PluginManager

                pm = PluginManager(config=bdnex_conf.get('scrapers', {}))
                # Use album name as query, and provide volume hint when available
                best = pm.search_best(
                    query=album_name,
                    series=None,
                    volume=filename_volume if filename_volume != -1 else None,
                    year=None,
                    min_confidence=50.0,
                    limit=5,
                )

                for sr in best:
                    try:
                        candidate_meta = _scraper_result_to_candidate(sr)

                        url = candidate_meta.get('url')
                        if url and url in seen_urls:
                            continue
                        if url:
                            seen_urls.add(url)

                        cover_web_fp_candidate = None
                        sim = 0.0
                        if candidate_meta.get('cover_url'):
                            try:
                                cover_web_fp_candidate = get_bdgest_cover(candidate_meta['cover_url'])
                                sim = front_cover_similarity(cover_archive_fp, cover_web_fp_candidate)
                            except Exception as e:
                                logger.debug(f"Cover fetch/compare failed for scraper candidate {url}: {e}")

                        candidate_meta['cover_path'] = cover_web_fp_candidate
                        candidate_meta['_cover_similarity'] = sim

                        scored_candidates.append(candidate_meta)
                        cover_similarities.append(sim)
                    except Exception as e:
                        logger.debug(f"Error processing scraper candidate: {e}")
                        continue

                if scored_candidates and cover_similarities:
                    scored = scorer.score_candidates(filename_metadata, scored_candidates, cover_similarities)
            except Exception as e:
                logger.debug(f"Scraper integration unavailable: {e}")

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
            result.filepath = file_path
            if batch_processor:
                batch_processor.add_result(result)
            return result
        
        best_candidate, best_score = scored[0]
        cover_auto_threshold = float(bdnex_conf['cover'].get('match_percentage', 50))
        best_cover_similarity = None
        try:
            best_cover_similarity = float(best_candidate.get('_cover_similarity'))
        except Exception:
            best_cover_similarity = None
        
        logger.info(f"Score de meilleure correspondance: {best_score * 100:.1f}%")
        
        selected_score = best_score  # Default to best_score
        manual_selection_used = False
        
        if best_score >= challenge_threshold or (best_cover_similarity is not None and best_cover_similarity >= cover_auto_threshold):
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
                    candidates=[(c, s, c.get('cover_path', '')) for c, s in scored[:3]],
                    cover_path=cover_archive_fp
                )
                result.filepath = file_path
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
                    candidates=[(c, s, c.get('cover_path', '')) for c, s in scored[:3]],
                    cover_path=cover_archive_fp,
                    metadata=filename_metadata
                )
                result.filepath = file_path
                if batch_processor:
                    batch_processor.add_result(result)
                return result

            # Interactive mode:
            # If cover similarity is already below the cover acceptance threshold, the disambiguation UI
            # won't help much (covers don't match). Keep the legacy flow: proceed to cover prompt/manual search.
            if best_cover_similarity is not None and best_cover_similarity < cover_auto_threshold:
                bdgest_meta = {k: v for k, v in best_candidate.items() if k not in ['comicrack_meta', 'cover_path']}
                comicrack_meta = best_candidate['comicrack_meta']
                cover_web_fp = best_candidate['cover_path']
                selected_score = best_score
            else:
            
                # Use enhanced CLI UI for low-confidence review
                logger.warning(f"Revue manuelle requise (faible confiance).")

                # Prepare candidates (top 5)
                challenge_candidates = []
                for candidate, score in scored[:5]:
                    challenge_candidates.append((candidate, score, candidate.get('cover_path')))

                selected_idx = None
                selected_candidate = None
                try:
                    from bdnex.ui.interactive_ui import InteractiveUI

                    rich_ui = InteractiveUI()
                    selected_candidate = rich_ui.select_candidate(
                        filename=filename_basename,
                        file_metadata=filename_metadata,
                        candidates=challenge_candidates,
                        show_covers=False,
                    )
                except Exception as e:
                    logger.debug(f"InteractiveUI unavailable, falling back to browser UI: {e}")
                    challenge_ui = ChallengeUI()
                    selected_idx = challenge_ui.show_challenge_interactive(
                        cover_archive_fp,
                        challenge_candidates,
                        filename_basename,
                    )
                    if selected_idx is not None and selected_idx >= 0 and selected_idx < len(challenge_candidates):
                        selected_candidate = challenge_candidates[selected_idx][0]
                        selected_score = challenge_candidates[selected_idx][1]
                
                if isinstance(selected_candidate, dict) and selected_candidate.get('action') == 'quit':
                    raise KeyboardInterrupt()

                if selected_candidate and isinstance(selected_candidate, dict) and selected_candidate.get('action') in ('skip', 'manual', 'manual_search'):
                    selected_candidate = None

                if selected_candidate is not None:
                    logger.info(f"Candidat sélectionné par l'utilisateur: {selected_candidate['title']}")
                    bdgest_meta = {k: v for k, v in selected_candidate.items() if k not in ['comicrack_meta', 'cover_path']}
                    comicrack_meta = selected_candidate.get('comicrack_meta', {})
                    cover_web_fp = selected_candidate.get('cover_path')
                    # If coming from InteractiveUI, the score is already in the ranked list
                    if selected_idx is None:
                        # Keep previously computed best_score unless we can find the exact tuple
                        selected_score = best_score
                else:
                    # Fallback to manual selection (user clicked "None of these")
                    logger.info(f"Utilisateur a rejeté tous les candidats. Début de la recherche manuelle pour {colored(filename_basename, 'red', attrs=['bold'])}")
                    album_url = BdGestParse().search_album_from_sitemaps_interactive()
                    bdgest_meta, comicrack_meta = BdGestParse().parse_album_metadata_mobile(album_name, album_url=album_url)
                    cover_web_fp = get_bdgest_cover(bdgest_meta["cover_url"])
                    selected_score = 1.0  # Manual search considered 100% confident
                    manual_selection_used = True

        # Final check and apply metadata
        percentage_similarity = None
        if best_cover_similarity is not None:
            percentage_similarity = best_cover_similarity
        else:
            percentage_similarity = front_cover_similarity(cover_archive_fp, cover_web_fp)

        # If the user explicitly selected an album manually, trust that choice even if
        # cover similarity is low, to avoid looping forever.
        if manual_selection_used or (percentage_similarity > bdnex_conf['cover'].get('match_percentage', 50)):
            comicInfo(file_path, comicrack_meta).append_comicinfo_to_archive()
            logger.info(f"Métadonnées appliquées avec succès")
            result = ProcessingResult(
                filename=filename_basename,
                success=True,
                score=best_score if best_score >= challenge_threshold else selected_score,
                title=bdgest_meta.get('title', 'Unknown'),
                metadata=bdgest_meta
            )
            result.filepath = file_path
            if batch_processor:
                batch_processor.add_result(result)
        else:
            logger.warning("Confiance de correspondance de couverture faible")
            if interactive:
                ans = yesno("La correspondance de couverture a une confiance faible. Voulez-vous quand même ajouter les métadonnées ?")
            else:
                ans = False  # Skip in batch mode on low cover match
            
            if ans:
                comicInfo(file_path, comicrack_meta).append_comicinfo_to_archive()
                logger.info(f"Métadonnées appliquées avec succès")
                result = ProcessingResult(
                    filename=filename_basename,
                    success=True,
                    score=best_score if best_score >= challenge_threshold else selected_score,
                    title=bdgest_meta.get('title', 'Unknown'),
                    metadata=bdgest_meta
                )
                result.filepath = file_path
                if batch_processor:
                    batch_processor.add_result(result)
            else:
                logger.info(f"Recherche manuelle pour {colored(filename_basename, 'red', attrs=['bold'])}")
                album_url = BdGestParse().search_album_from_sitemaps_interactive()
                bdgest_meta, comicrack_meta = BdGestParse().parse_album_metadata_mobile(album_name, album_url=album_url)
                comicInfo(file_path, comicrack_meta).append_comicinfo_to_archive()
                logger.info(f"Métadonnées appliquées avec succès")
                result = ProcessingResult(
                    filename=filename_basename,
                    success=True,
                    score=1.0,
                    title=bdgest_meta.get('title', 'Unknown'),
                    metadata=bdgest_meta
                )
                result.filepath = file_path
                if batch_processor:
                    batch_processor.add_result(result)

        cover_path = Path(cover_archive_fp).parent.as_posix()
        shutil.rmtree(cover_path)

        logger.info(f"Traitement de l'album terminé")
        
        # Store final filepath in result for potential renaming
        if result:
            result.filepath = file_path
        
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
        result.filepath = file_path
        if batch_processor:
            batch_processor.add_result(result)
        return result


def handle_catalog_commands(vargs, logger):
    """
    Handle catalog subcommands.
    
    Args:
        vargs: Parsed arguments
        logger: Logger instance
        
    Returns:
        True if catalog command was handled, False otherwise
    """
    if vargs.command != 'catalog':
        return False
    
    catalog = CatalogManager()
    
    if vargs.catalog_command == 'list':
        # List BDs by category
        limit = vargs.limit
        
        if vargs.list_by == 'series':
            results = catalog.list_by_series(limit=limit)
            print("\n" + "=" * 80)
            print(f"SÉRIES (Top {len(results)})")
            print("=" * 80)
            for series, count in results:
                print(f"  {series:<65} {count:>5} album(s)")
            print("=" * 80 + "\n")
        
        elif vargs.list_by == 'publisher':
            results = catalog.list_by_publisher(limit=limit)
            print("\n" + "=" * 80)
            print(f"ÉDITEURS (Top {len(results)})")
            print("=" * 80)
            for publisher, count in results:
                print(f"  {publisher:<65} {count:>5} album(s)")
            print("=" * 80 + "\n")
        
        elif vargs.list_by == 'year':
            results = catalog.list_by_year(limit=limit)
            print("\n" + "=" * 80)
            print(f"ANNÉES (Top {len(results)})")
            print("=" * 80)
            for year, count in results:
                print(f"  {year:<10} {count:>5} album(s)")
            print("=" * 80 + "\n")
    
    elif vargs.catalog_command == 'search':
        # Search in catalog
        results = catalog.search(
            vargs.query,
            publisher=vargs.publisher,
            year=vargs.year,
            limit=vargs.limit
        )
        
        print("\n" + "=" * 80)
        print(f"RÉSULTATS DE RECHERCHE: \"{vargs.query}\" ({len(results)} résultat(s))")
        print("=" * 80)
        
        for album in results:
            series = album.get('series', 'N/A')
            number = album.get('number', 'N/A')
            title = album.get('title', 'N/A')
            year = album.get('year', 'N/A')
            
            print(f"\n  {series} - Tome {number}: {title} ({year})")
            print(f"    Scénario: {album.get('writer', 'N/A')}")
            print(f"    Dessin: {album.get('penciller', 'N/A')}")
            print(f"    Éditeur: {album.get('publisher', 'N/A')}")
            print(f"    Fichier: {Path(album.get('file_path', 'N/A')).name}")
        
        print("\n" + "=" * 80 + "\n")
    
    elif vargs.catalog_command == 'stats':
        # Show statistics
        catalog.print_stats_summary()
    
    elif vargs.catalog_command == 'export':
        # Export catalog
        filters = {}
        if vargs.publisher:
            filters['publisher'] = vargs.publisher
        if vargs.year:
            filters['year'] = vargs.year
        if vargs.series:
            filters['series'] = vargs.series
        
        if vargs.export_format == 'csv':
            count = catalog.export_csv(vargs.export_output, filters)
        else:  # json
            count = catalog.export_json(vargs.export_output, filters)
        
        filter_str = ""
        if filters:
            filter_str = f" (filtré: {', '.join(f'{k}={v}' for k, v in filters.items())})"
        
        print(f"\n[OK] {count} album(s) exporté(s) vers {vargs.export_output}{filter_str}\n")
    
    else:
        logger.error(f"Commande catalog inconnue: {vargs.catalog_command}")
        return False
    
    return True


def main():
    """Main entry point with advanced batch processing support."""
    from bdnex.lib.batch_config import SitemapCache
    from bdnex.lib.advanced_batch_processor import AdvancedBatchProcessor
    from bdnex.lib.cli_session_manager import CLISessionManager
    
    vargs = args()
    logger = logging.getLogger(__name__)

    # NOTE: unit tests mock args() with MagicMock. Accessing missing attributes on MagicMock
    # yields new truthy mocks, which can accidentally enable unrelated code paths.
    # Using vars(vargs) keeps behavior aligned with argparse.Namespace.
    v = vars(vargs) if hasattr(vargs, '__dict__') else {}
    def _get(name, default=None):
        return v.get(name, default)

    if bool(_get('no_progress', False)):
        os.environ['BDNEX_NO_PROGRESS'] = '1'
    
    # Handle catalog commands first
    if handle_catalog_commands(vargs, logger):
        return

    # Database-aware CLI commands (Phase 2A)
    # Only invoke if the flags exist and are set, otherwise unit tests that mock
    # only a subset of args would unexpectedly list sessions.
    cli_manager = CLISessionManager()
    wants_session_cmd = any(
        bool(_get(attr))
        for attr in ("list_sessions", "session_info", "resume_session", "resume")
        if attr in v
    )
    session_handled = cli_manager.handle_cli_session_args(vargs) if wants_session_cmd else None
    
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
    skip_processed = bool(_get('skip_processed', False)) and not bool(_get('force_reprocess', False))

    if bool(_get('init', False)):
        BdGestParse().download_sitemaps()

    if _get('input_dir'):
        dirpath = _get('input_dir')
        files = []

        for path in Path(dirpath).rglob('*.cbz'):
            files.append(path.absolute().as_posix())

        for path in Path(dirpath).rglob('*.cbr'):
            files.append(path.absolute().as_posix())

        logger.info(f"Trouvé {len(files)} fichier(s) BD à traiter")

        # Backward-compatible non-batch behavior: simple iteration.
        if not bool(_get('batch', False)) and resume_session_id is None:
            show_progress = (not bool(_get('no_progress', False))) and bool(getattr(sys.stdout, 'isatty', lambda: False)())
            with progress_for(len(files), enabled=show_progress, description="Traitement") as prog:
                for fp in files:
                    try:
                        prog.update(message=Path(fp).name)
                        add_metadata_from_bdgest(fp)
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement: {e}")
            return

        # Batch/resume mode: advanced processor for parallel processing
        processor = AdvancedBatchProcessor(
            batch_mode=bool(_get('batch', False)),
            strict_mode=bool(_get('strict', False)),
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
                interactive=not bool(_get('batch', False)),  # Interactive only if not batch mode
                strict_mode=bool(_get('strict', False)),
                max_retries=3,
            )
        else:
            results = processor.process_files_sequential(
                files,
                interactive=not bool(_get('batch', False)),
                strict_mode=bool(_get('strict', False)),
                max_retries=3,
            )
        
        # After all files processed in batch mode, show consolidated challenge UI if needed
        low_conf_files = processor.get_low_confidence_files(results)
        if low_conf_files and not bool(_get('strict', False)) and not bool(_get('batch', False)):
            logger.info(f"\n{len(low_conf_files)} fichier(s) nécessite(nt) une révision manuelle")
            batch_challenge = BatchChallengeUI()
            try:
                # TODO: Implement consolidated challenge UI for low-confidence files
                logger.info("Révision par lot des fichiers avec faible confiance")
            except Exception as e:
                logger.warning(f"Interface de révision indisponible: {e}")
        
        # Print summary and save logs
        processor.print_summary(results)
        
        # Handle file renaming if requested
        if _get('rename_template'):
            logger.info("\n=== Renommage des fichiers ===")
            rename_manager = RenameManager(
                backup_enabled=not bool(_get('no_backup', False)),
                dry_run=bool(_get('rename_dry_run', False))
            )
            
            renamed_count = 0
            failed_count = 0
            
            for result in results:
                if result and result.success:
                    success, old_path, new_path = handle_file_renaming(
                        result, rename_manager, _get('rename_template'), logger
                    )
                    if success and old_path != new_path:
                        renamed_count += 1
                    elif not success:
                        failed_count += 1
            
            if bool(_get('rename_dry_run', False)):
                logger.info(f"\n[DRY-RUN] {renamed_count} fichier(s) seraient renommés")
            else:
                logger.info(f"\n{renamed_count} fichier(s) renommé(s) avec succès")
                if failed_count > 0:
                    logger.warning(f"{failed_count} fichier(s) n'ont pas pu être renommés")

    elif _get('input_file'):
        file = _get('input_file')

        # Skip if already processed and user requested skip
        if skip_processed and cli_manager.db and cli_manager.db.is_processed(file):
            logger.info(f"Fichier déjà traité, ignoré grâce à --skip-processed: {file}")
            return

        result = add_metadata_from_bdgest(file)
        if result:
            logger.info(f"Résultat: {result.filename} - {'[OK] Succès' if result.success else '[FAIL] Échoué'}")
            
            # Handle file renaming if requested
            if _get('rename_template') and result.success:
                rename_manager = RenameManager(
                    backup_enabled=not bool(_get('no_backup', False)),
                    dry_run=bool(_get('rename_dry_run', False))
                )
                success, old_path, new_path = handle_file_renaming(
                    result, rename_manager, _get('rename_template'), logger
                )
                if success and old_path != new_path:
                    if vargs.rename_dry_run:
                        logger.info(f"[DRY-RUN] Fichier serait renommé")
                    else:
                        logger.info(f"Fichier renommé avec succès")



