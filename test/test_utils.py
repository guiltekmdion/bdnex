import os
import tempfile
import unittest
from unittest.mock import patch, mock_open
from bdnex.lib.utils import (
    bdnex_config, yesno, enter_album_url, 
    dump_json, load_json, download_link, temporary_directory
)


class TestUtils(unittest.TestCase):

    @patch('bdnex.lib.utils._init_config')
    def test_bdnex_config(self, _init_config_mock):
        _init_config_mock.return_value = os.path.join(os.path.join(os.path.dirname(__file__), "bdnex.yaml"))
        conf = bdnex_config()
        self.assertTrue('bdnex' in conf)

    @patch('builtins.input', side_effect=['nooooo', 'Y'])
    def test_yesno_yes(self, input):
        self.assertTrue(yesno('do you need this? Y/N'))

    @patch('builtins.input', side_effect=['nooooo', 'def nop', 'i give up', 'n'])
    def test_yesno_no(self, input):
        self.assertFalse(yesno('do you need this? Y/N'))

    @patch('builtins.input', side_effect=['a', 'b', 'https://www.bedetheque.com/nain.html'])
    def test_enter_album_url_with_retries(self, input):
        # After 2 retries (iter < 2), it returns the last value even if invalid
        result = enter_album_url()
        # The function has a bug where it returns the last input after 2 retries
        # The current behavior returns the URL after conversion
        self.assertEqual('https://m.bedetheque.com/nain.html', result)

    @patch('builtins.input', side_effect=['a', 'b', 'https://www.bedetheque.com/nain.html'])
    def test_enter_album_url_success(self, input):
        self.assertEqual('https://m.bedetheque.com/nain.html', enter_album_url())

    def test_dump_and_load_json(self):
        """Test JSON dump and load functions"""
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Test dump_json
            dump_json(tmp_path, test_data)
            self.assertTrue(os.path.exists(tmp_path))
            
            # Test load_json
            loaded_data = load_json(tmp_path)
            self.assertEqual(test_data, loaded_data)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_load_json_nonexistent(self):
        """Test load_json with non-existent file"""
        nonexistent_path = os.path.join(tempfile.gettempdir(), 'nonexistent_file_12345.json')
        result = load_json(nonexistent_path)
        self.assertIsNone(result)

    @patch('urllib.request.urlretrieve')
    def test_download_link(self, mock_urlretrieve):
        """Test download_link function"""
        test_url = "https://example.com/file.jpg"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_path = download_link(test_url, tmpdir)
            expected_path = os.path.join(tmpdir, "file.jpg")
            self.assertEqual(result_path, expected_path)
            mock_urlretrieve.assert_called_once()

    @patch('urllib.request.urlretrieve')
    def test_download_link_no_folder(self, mock_urlretrieve):
        """Test download_link without specifying output folder"""
        test_url = "https://example.com/file.jpg"
        result_path = download_link(test_url)
        self.assertTrue(result_path.endswith("file.jpg"))
        mock_urlretrieve.assert_called_once()

    def test_temporary_directory(self):
        """Test temporary_directory context manager"""
        temp_path = None
        with temporary_directory() as tmpdir:
            temp_path = tmpdir
            self.assertTrue(os.path.exists(tmpdir))
            self.assertTrue(os.path.isdir(tmpdir))
        
        # Directory should be cleaned up after context
        self.assertFalse(os.path.exists(temp_path))
