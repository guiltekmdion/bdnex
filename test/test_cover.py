import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import shutil
import cv2
import numpy as np

from bdnex.lib.cover import front_cover_similarity, get_bdgest_cover

TEST_ROOT = os.path.dirname(__file__)

BDGEST_COVER = os.path.join(TEST_ROOT, 'Couv_245127.jpg')
ARCHIVE_COVER = os.path.join(TEST_ROOT, 'Nains 1 00a.jpg')
BDGEST_OTHER_COVER = os.path.join(TEST_ROOT, 'Couv_272757.jpg')


class TestCover(unittest.TestCase):
    def test_front_cover_similarity_good_match(self):
        """Test front cover similarity with matching covers"""
        match_res = front_cover_similarity(ARCHIVE_COVER, BDGEST_COVER)
        self.assertGreater(match_res, 50)

    def test_front_cover_similarity_bad_match(self):
        """Test front cover similarity with non-matching covers"""
        match_res = front_cover_similarity(ARCHIVE_COVER, BDGEST_OTHER_COVER)
        self.assertLess(match_res, 5)

    def test_front_cover_similarity_same_image(self):
        """Test front cover similarity with identical images"""
        match_res = front_cover_similarity(BDGEST_COVER, BDGEST_COVER)
        # Same image should have very high similarity
        self.assertGreater(match_res, 90)

    @patch.dict(os.environ, {'HOME': '/tmp'})
    @patch('bdnex.lib.cover.download_link')
    @patch('os.path.exists')
    def test_get_bdgest_cover_existing(self, mock_exists, mock_download):
        """Test get_bdgest_cover when cover already exists"""
        mock_exists.return_value = True
        test_url = "https://example.com/covers/test_cover.jpg"
        
        result = get_bdgest_cover(test_url)
        
        expected_path = "/tmp/.local/share/bdnex/bedetheque/covers/test_cover.jpg"
        self.assertEqual(result, expected_path)
        mock_download.assert_not_called()

    @patch.dict(os.environ, {'HOME': '/tmp'})
    @patch('bdnex.lib.cover.download_link')
    @patch('os.path.exists')
    def test_get_bdgest_cover_download(self, mock_exists, mock_download):
        """Test get_bdgest_cover when cover needs to be downloaded"""
        mock_exists.return_value = False
        test_url = "https://example.com/covers/new_cover.jpg"
        expected_path = "/tmp/.local/share/bdnex/bedetheque/covers/new_cover.jpg"
        mock_download.return_value = expected_path
        
        result = get_bdgest_cover(test_url)
        
        self.assertEqual(result, expected_path)
        mock_download.assert_called_once()

    def test_front_cover_similarity_division_by_zero(self):
        """Test front_cover_similarity handles division by zero"""
        # This test ensures the exception handling works
        # We need to create images that would cause zero keypoints
        import cv2
        import numpy as np
        
        # Create blank images that might have no features
        blank_img = np.zeros((100, 100), dtype=np.uint8)
        temp_dir = tempfile.mkdtemp()
        
        try:
            img1_path = os.path.join(temp_dir, 'blank1.jpg')
            img2_path = os.path.join(temp_dir, 'blank2.jpg')
            
            cv2.imwrite(img1_path, blank_img)
            cv2.imwrite(img2_path, blank_img)
            
            # This should handle the error and return 0
            result = front_cover_similarity(img1_path, img2_path)
            
            # The function should return 0 or a valid percentage
            self.assertIsInstance(result, (int, float))
            self.assertGreaterEqual(result, 0)
        finally:
            # Cleanup
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    unittest.main()
