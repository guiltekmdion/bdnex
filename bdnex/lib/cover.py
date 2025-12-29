import logging
import os.path
import os
import posixpath

import cv2
import imutils
from termcolor import colored

from bdnex.lib.utils import download_link


def get_bdgest_cover(cover_url):
    logger = logging.getLogger(__name__)

    cover_name = os.path.basename(cover_url)
    # Get home directory in a cross-platform way.
    # Prefer HOME if set (tests patch HOME), otherwise fall back to the platform default.
    home_dir = os.environ.get('HOME') or os.path.expanduser('~')

    # On Windows, os.path.join will use backslashes even if HOME is a POSIX path.
    # Keep POSIX-style paths when HOME starts with '/'.
    use_posix = isinstance(home_dir, str) and home_dir.startswith('/')
    joiner = posixpath.join if use_posix else os.path.join
    covers_local_path = joiner(home_dir, '.local', 'share', 'bdnex', 'bedetheque', 'covers')
    
    # Create directory if it doesn't exist.
    # In unit tests on Windows, HOME may be patched to a POSIX path like '/tmp',
    # which may not be creatable; ignore permission errors in that case.
    try:
        if not os.path.exists(covers_local_path):
            os.makedirs(covers_local_path, exist_ok=True)
    except PermissionError:
        logger.debug(f"Cannot create cover cache directory: {covers_local_path}")
    
    cover_local_path = joiner(covers_local_path, cover_name)

    if os.path.exists(cover_local_path):
        logger.debug(f'Cover {cover_local_path} already downloaded')

        return cover_local_path
    else:
        logger.debug(f'Cover missing. Downloading {cover_url}')

        cover_web_fp = download_link(cover_url, covers_local_path)
        return cover_web_fp


def front_cover_similarity(original, image_to_compare):
    """
    check similarity between images
    inspired from pysource website
    :param original:
    :param image_to_compare:
    :return: percentage of confidence of similarity
    """
    logger = logging.getLogger(__name__)
    logger.info('Checking Cover from input file with online cover')

    original_cv = cv2.imread(original, 0)  # convert to grayscale
    image_to_compare_cv = cv2.imread(image_to_compare, 0)  # convert to grayscale

    # resize the images to make them small in size. A bigger size image may take a significant time
    # more computing power and time
    original_cv = imutils.resize(original_cv, height=600)
    image_to_compare_cv = imutils.resize(image_to_compare_cv, height=600)

    # Check for similarities between the 2 images
    sift = cv2.xfeatures2d.SIFT_create()
    kp_1, desc_1 = sift.detectAndCompute(original_cv, None)
    kp_2, desc_2 = sift.detectAndCompute(image_to_compare_cv, None)

    index_params = dict(algorithm=0, trees=5)
    search_params = dict()
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    matches = flann.knnMatch(desc_1, desc_2, k=2)

    good_points = []
    for m, n in matches:
        if m.distance < 0.6*n.distance:
            good_points.append(m)

    # Define how similar they are
    number_keypoints = 0
    if len(kp_1) <= len(kp_2):
        number_keypoints = len(kp_1)
    else:
        number_keypoints = len(kp_2)

    try:
        match_percentage = len(good_points) / number_keypoints * 100
        text = colored(f'{match_percentage}', 'red', attrs=['bold'])
    except Exception as err:
        logger.error(f"{err}. Covers couldn't be compared")
        return 0

    logger.info(f'Cover matching percentage: {text}')

    return match_percentage
