import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import shutil

from bdnex.ui import main, add_metadata_from_bdgest


class TestUI(unittest.TestCase):
    """Tests for the UI module"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('bdnex.ui.args')
    @patch('bdnex.ui.BdGestParse')
    def test_main_with_init(self, mock_bdgest, mock_args):
        """Test main function with --init flag"""
        mock_vargs = MagicMock()
        mock_vargs.init = True
        mock_vargs.input_dir = None
        mock_vargs.input_file = None
        mock_args.return_value = mock_vargs
        
        mock_bdgest_instance = MagicMock()
        mock_bdgest.return_value = mock_bdgest_instance
        
        main()
        
        mock_bdgest_instance.download_sitemaps.assert_called_once()

    @patch('bdnex.ui.args')
    @patch('bdnex.ui.add_metadata_from_bdgest')
    def test_main_with_input_file(self, mock_add_metadata, mock_args):
        """Test main function with input file"""
        test_file = os.path.join(self.test_dir, 'test.cbz')
        with open(test_file, 'w') as f:
            f.write('test')
        
        mock_vargs = MagicMock()
        mock_vargs.init = False
        mock_vargs.input_dir = None
        mock_vargs.input_file = test_file
        mock_args.return_value = mock_vargs
        
        main()
        
        mock_add_metadata.assert_called_once_with(test_file)

    @patch('bdnex.ui.args')
    @patch('bdnex.ui.add_metadata_from_bdgest')
    def test_main_with_input_dir(self, mock_add_metadata, mock_args):
        """Test main function with input directory"""
        # Create test files
        cbz_file = os.path.join(self.test_dir, 'test1.cbz')
        cbr_file = os.path.join(self.test_dir, 'test2.cbr')
        
        with open(cbz_file, 'w') as f:
            f.write('test cbz')
        with open(cbr_file, 'w') as f:
            f.write('test cbr')
        
        mock_vargs = MagicMock()
        mock_vargs.init = False
        mock_vargs.input_dir = self.test_dir
        mock_vargs.input_file = None
        mock_args.return_value = mock_vargs
        
        main()
        
        # Should be called for both files
        self.assertEqual(mock_add_metadata.call_count, 2)

    @patch('bdnex.ui.args')
    @patch('bdnex.ui.add_metadata_from_bdgest')
    def test_main_with_input_dir_error_handling(self, mock_add_metadata, mock_args):
        """Test main function handles errors in directory processing"""
        # Create test file
        test_file = os.path.join(self.test_dir, 'test.cbz')
        with open(test_file, 'w') as f:
            f.write('test')
        
        mock_vargs = MagicMock()
        mock_vargs.init = False
        mock_vargs.input_dir = self.test_dir
        mock_vargs.input_file = None
        mock_args.return_value = mock_vargs
        
        # Make add_metadata raise an exception
        mock_add_metadata.side_effect = Exception("Test error")
        
        # Should not raise, should handle error
        try:
            main()
        except Exception:
            self.fail("main() should handle exceptions gracefully")

    @patch('bdnex.ui.BdGestParse')
    @patch('bdnex.ui.comicInfo')
    @patch('bdnex.ui.front_cover_similarity')
    @patch('bdnex.ui.get_bdgest_cover')
    @patch('bdnex.ui.archive_get_front_cover')
    @patch('bdnex.ui.bdnex_config')
    @patch('bdnex.ui.yesno')
    def test_add_metadata_low_confidence_user_rejects_then_manual(
        self,
        mock_yesno,
        mock_config,
        mock_get_front_cover,
        mock_get_bdgest_cover,
        mock_cover_similarity,
        mock_comic_info,
        mock_bdgest_parse
    ):
        """Test workflow when user rejects low confidence match and does manual search"""
        
        mock_config.return_value = {
            'cover': {'match_percentage': 40},
            'bdnex': {'share_path': self.test_dir}
        }
        
        test_comic = os.path.join(self.test_dir, 'test_comic.cbz')
        with open(test_comic, 'w') as f:
            f.write('dummy content')
        
        mock_bdgest_instance = MagicMock()
        mock_bdgest_instance.parse_album_metadata_mobile.return_value = (
            {'cover_url': 'https://example.com/cover.jpg', 'album_url': 'https://example.com/album.html'},
            {'Title': 'Test Comic', 'Series': 'Test Series'}
        )
        mock_bdgest_instance.search_album_from_sitemaps_interactive.return_value = 'https://example.com/manual.html'
        mock_bdgest_parse.return_value = mock_bdgest_instance
        
        # Create cover directory
        os.makedirs(os.path.join(self.test_dir, 'temp_covers'), exist_ok=True)
        mock_get_front_cover.return_value = os.path.join(self.test_dir, 'temp_covers', 'cover.jpg')
        mock_get_bdgest_cover.return_value = '/tmp/cover_web.jpg'
        mock_cover_similarity.return_value = 25.0  # Low confidence
        
        # User rejects first, triggering manual search
        mock_yesno.return_value = False
        
        mock_comic_info_instance = MagicMock()
        mock_comic_info.return_value = mock_comic_info_instance
        
        add_metadata_from_bdgest(test_comic)
        
        # Verify manual search was triggered
        mock_bdgest_instance.search_album_from_sitemaps_interactive.assert_called_once()
        # Should call parse_album_metadata_mobile twice (once automatic, once manual)
        self.assertEqual(mock_bdgest_instance.parse_album_metadata_mobile.call_count, 2)


if __name__ == '__main__':
    unittest.main()
