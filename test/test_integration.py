import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import shutil

from bdnex.ui import add_metadata_from_bdgest


class TestIntegration(unittest.TestCase):
    """Integration tests for end-to-end workflows"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('bdnex.ui.BdGestParse')
    @patch('bdnex.ui.comicInfo')
    @patch('bdnex.ui.front_cover_similarity')
    @patch('bdnex.ui.get_bdgest_cover')
    @patch('bdnex.ui.archive_get_front_cover')
    @patch('bdnex.ui.bdnex_config')
    def test_add_metadata_workflow_high_confidence(
        self, 
        mock_config,
        mock_get_front_cover,
        mock_get_bdgest_cover,
        mock_cover_similarity,
        mock_comic_info,
        mock_bdgest_parse
    ):
        """Test the complete metadata addition workflow with high cover match"""
        
        # Setup mocks
        mock_config.return_value = {
            'cover': {'match_percentage': 40},
            'bdnex': {'share_path': self.test_dir}
        }
        
        # Create a dummy comic file
        test_comic = os.path.join(self.test_dir, 'test_comic.cbz')
        with open(test_comic, 'w') as f:
            f.write('dummy content')
        
        # Mock BdGestParse methods
        mock_bdgest_instance = MagicMock()
        mock_bdgest_instance.parse_album_metadata_mobile.return_value = (
            {'cover_url': 'https://example.com/cover.jpg', 'album_url': 'https://example.com/album.html'},
            {'Title': 'Test Comic', 'Series': 'Test Series'}
        )
        mock_bdgest_parse.return_value = mock_bdgest_instance
        
        # Mock cover operations
        mock_get_front_cover.return_value = '/tmp/cover_archive.jpg'
        mock_get_bdgest_cover.return_value = '/tmp/cover_web.jpg'
        mock_cover_similarity.return_value = 85.0  # High confidence match
        
        # Mock comicInfo
        mock_comic_info_instance = MagicMock()
        mock_comic_info.return_value = mock_comic_info_instance
        
        # Create necessary directories for cleanup
        os.makedirs(os.path.join(self.test_dir, 'temp_covers'), exist_ok=True)
        mock_get_front_cover.return_value = os.path.join(self.test_dir, 'temp_covers', 'cover.jpg')
        
        # Run the function
        add_metadata_from_bdgest(test_comic)
        
        # Verify the workflow
        mock_bdgest_instance.parse_album_metadata_mobile.assert_called_once()
        mock_get_front_cover.assert_called_once_with(test_comic)
        mock_cover_similarity.assert_called_once()
        mock_comic_info_instance.append_comicinfo_to_archive.assert_called_once()
    
    @patch('bdnex.ui.BdGestParse')
    @patch('bdnex.ui.comicInfo')
    @patch('bdnex.ui.front_cover_similarity')
    @patch('bdnex.ui.get_bdgest_cover')
    @patch('bdnex.ui.archive_get_front_cover')
    @patch('bdnex.ui.bdnex_config')
    @patch('bdnex.ui.yesno')
    def test_add_metadata_workflow_low_confidence_user_accepts(
        self,
        mock_yesno,
        mock_config,
        mock_get_front_cover,
        mock_get_bdgest_cover,
        mock_cover_similarity,
        mock_comic_info,
        mock_bdgest_parse
    ):
        """Test workflow when cover match is low but user accepts"""
        
        # Setup mocks
        mock_config.return_value = {
            'cover': {'match_percentage': 40},
            'bdnex': {'share_path': self.test_dir}
        }
        
        # Create a dummy comic file
        test_comic = os.path.join(self.test_dir, 'test_comic.cbz')
        with open(test_comic, 'w') as f:
            f.write('dummy content')
        
        # Mock BdGestParse methods
        mock_bdgest_instance = MagicMock()
        mock_bdgest_instance.parse_album_metadata_mobile.return_value = (
            {'cover_url': 'https://example.com/cover.jpg', 'album_url': 'https://example.com/album.html'},
            {'Title': 'Test Comic', 'Series': 'Test Series'}
        )
        mock_bdgest_parse.return_value = mock_bdgest_instance
        
        # Mock cover operations with LOW similarity
        mock_get_front_cover.return_value = '/tmp/cover_archive.jpg'
        mock_get_bdgest_cover.return_value = '/tmp/cover_web.jpg'
        mock_cover_similarity.return_value = 25.0  # Low confidence match
        
        # User accepts despite low confidence
        mock_yesno.return_value = True
        
        # Mock comicInfo
        mock_comic_info_instance = MagicMock()
        mock_comic_info.return_value = mock_comic_info_instance
        
        # Create necessary directories for cleanup
        os.makedirs(os.path.join(self.test_dir, 'temp_covers'), exist_ok=True)
        mock_get_front_cover.return_value = os.path.join(self.test_dir, 'temp_covers', 'cover.jpg')
        
        # Run the function
        add_metadata_from_bdgest(test_comic)
        
        # Verify the workflow
        mock_yesno.assert_called_once()
        mock_comic_info_instance.append_comicinfo_to_archive.assert_called_once()


if __name__ == '__main__':
    unittest.main()
