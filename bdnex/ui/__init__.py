#!/usr/bin/env python3
import os
import logging
import shutil

from bdnex.lib.archive_tools import archive_get_front_cover
from bdnex.lib.bdgest import BdGestParse
from bdnex.lib.comicrack import comicInfo
from bdnex.lib.cover import front_cover_similarity, get_bdgest_cover
from bdnex.lib.utils import yesno, args, bdnex_config
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

    # Extract archive cover first for disambiguation
    cover_archive_fp = archive_get_front_cover(filename)

    # Try disambiguation using cover similarity across top fuzzy candidates
    parser = BdGestParse()
    candidates = parser.search_album_candidates_fast(album_name, top_k=5)
    chosen_url = None
    best_sim = -1
    best_cover_web_fp = None
    for _, _, url in candidates:
        try:
            bd_meta_candidate, _ = parser.parse_album_metadata_mobile(album_name, album_url=url)
            cover_web_fp_candidate = get_bdgest_cover(bd_meta_candidate["cover_url"])
            sim = front_cover_similarity(cover_archive_fp, cover_web_fp_candidate)
            if sim > best_sim:
                best_sim = sim
                chosen_url = url
                best_cover_web_fp = cover_web_fp_candidate
        except Exception:
            continue

    # If best similarity passes threshold, use that URL; else fallback to default fuzzy URL
    if best_sim >= bdnex_conf['cover']['match_percentage'] and chosen_url:
        bdgest_meta, comicrack_meta = parser.parse_album_metadata_mobile(album_name, album_url=chosen_url)
        cover_web_fp = best_cover_web_fp
    else:
        bdgest_meta, comicrack_meta = parser.parse_album_metadata_mobile(album_name)
        cover_web_fp = get_bdgest_cover(bdgest_meta["cover_url"])

    percentage_similarity = front_cover_similarity(cover_archive_fp, cover_web_fp)

    if percentage_similarity > bdnex_conf['cover']['match_percentage']:
        comicInfo(filename, comicrack_meta).append_comicinfo_to_archive()
    else:
        logger.warning("UserPrompt required")
        ans = yesno("Cover matching confidence is low. Do you still want to append the metadata to the file?")
        if ans:
            comicInfo(filename, comicrack_meta).append_comicinfo_to_archive()
        else:
            logger.info(f"Looking manually for {colored(os.path.basename(filename), 'red', attrs=['bold'])}")
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


