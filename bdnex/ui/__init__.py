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
from bdnex.ui.challenge import ChallengeUI
from pathlib import Path
from termcolor import colored


def add_metadata_from_bdgest(filename):
    bdnex_conf = bdnex_config()
    logger = logging.getLogger(__name__)
    start_separator = colored(f'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~',
                              'red', attrs=['bold'])

    logger.info(start_separator)
    logger.info(f"Processing {filename}")

    album_name = os.path.splitext(os.path.basename(filename))[0]
    filename_basename = os.path.basename(filename)

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
        logger.error("No valid candidates found")
        return

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
    
    logger.info(f"Top match score: {best_score * 100:.1f}%")
    
    # Determine if we need challenge UI
    challenge_threshold = bdnex_conf['cover'].get('challenge_threshold', 0.70)  # Default 70%
    
    if best_score >= challenge_threshold:
        # High confidence, use automatically
        logger.info(f"High confidence match ({best_score * 100:.1f}%). Using automatically.")
        bdgest_meta = {k: v for k, v in best_candidate.items() if k not in ['comicrack_meta', 'cover_path']}
        comicrack_meta = best_candidate['comicrack_meta']
        cover_web_fp = best_candidate['cover_path']
    else:
        # Low confidence, show challenge
        logger.warning(f"Low confidence match ({best_score * 100:.1f}%). Showing challenge UI.")
        
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
            logger.info(f"User selected candidate: {selected_candidate['title']}")
            bdgest_meta = {k: v for k, v in selected_candidate.items() if k not in ['comicrack_meta', 'cover_path']}
            comicrack_meta = selected_candidate['comicrack_meta']
            cover_web_fp = selected_candidate['cover_path']
        else:
            # Fallback to manual selection (user clicked "None of these")
            logger.info(f"User rejected all candidates. Starting manual search for {colored(filename_basename, 'red', attrs=['bold'])}")
            album_url = BdGestParse().search_album_from_sitemaps_interactive()
            bdgest_meta, comicrack_meta = BdGestParse().parse_album_metadata_mobile(album_name, album_url=album_url)
            cover_web_fp = get_bdgest_cover(bdgest_meta["cover_url"])

    # Final check and apply metadata
    percentage_similarity = front_cover_similarity(cover_archive_fp, cover_web_fp)

    if percentage_similarity > bdnex_conf['cover'].get('match_percentage', 50):
        comicInfo(filename, comicrack_meta).append_comicinfo_to_archive()
    else:
        logger.warning("UserPrompt required")
        ans = yesno("Cover matching confidence is low. Do you still want to append the metadata to the file?")
        if ans:
            comicInfo(filename, comicrack_meta).append_comicinfo_to_archive()
        else:
            logger.info(f"Looking manually for {colored(filename_basename, 'red', attrs=['bold'])}")
            album_url = BdGestParse().search_album_from_sitemaps_interactive()
            bdgest_meta, comicrack_meta = BdGestParse().parse_album_metadata_mobile(album_name, album_url=album_url)
            comicInfo(filename, comicrack_meta).append_comicinfo_to_archive()

    cover_path = Path(cover_archive_fp).parent.as_posix()
    shutil.rmtree(cover_path)

    logger.info(f"Processing album done")


def main():
    vargs = args()

    if vargs.init:
        BdGestParse().download_sitemaps()

    if vargs.input_dir:
        dirpath = vargs.input_dir

        files = []

        for path in Path(dirpath).rglob('*.cbz'):
            files.append(path.absolute().as_posix())

        for path in Path(dirpath).rglob('*.cbr'):
            files.append(path.absolute().as_posix())

        for file in files:
            try:
                add_metadata_from_bdgest(file)
            except:
                logger = logging.getLogger(__name__)
                logger.error(f"{file} couldn't be processed")

    elif vargs.input_file:
        file = vargs.input_file
        add_metadata_from_bdgest(file)


