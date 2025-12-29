import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

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


if __name__ == '__main__':
    unittest.main()
