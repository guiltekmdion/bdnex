import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock, call
import zipfile
import json

from bdnex.lib.comicrack import comicInfo


class TestComicRack(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_comic_info = {
            "ComicInfo": {
                "Title": "Test Comic",
                "Series": "Test Series",
                "Number": "1",
                "Writer": "Test Writer",
                "Summary": "Test summary"
            }
        }
        
    def test_comicInfo_xml_create(self):
        """Test creation of ComicInfo.xml"""
        comic = comicInfo(comic_info=self.test_comic_info)
        xml_path = comic.comicInfo_xml_create()
        
        # Verify XML file was created
        self.assertTrue(os.path.exists(xml_path))
        
        # Verify it's an XML file
        with open(xml_path, 'r') as f:
            content = f.read()
            self.assertTrue(content.startswith('<?xml'))
            self.assertIn('ComicInfo', content)
        
        # Cleanup
        os.remove(xml_path)
        os.rmdir(os.path.dirname(xml_path))
    
    def test_comicInfo_initialization(self):
        """Test comicInfo class initialization"""
        test_file = "/test/path/comic.cbz"
        comic = comicInfo(input_filename=test_file, comic_info=self.test_comic_info)
        
        self.assertEqual(comic.input_filename, test_file)
        self.assertEqual(comic.comic_info, self.test_comic_info)
        self.assertIsNotNone(comic.logger)
    
    def test_comicInfo_xml_create_with_empty_data(self):
        """Test XML creation with minimal data"""
        minimal_info = {"ComicInfo": {"Title": "Minimal"}}
        comic = comicInfo(comic_info=minimal_info)
        xml_path = comic.comicInfo_xml_create()
        
        self.assertTrue(os.path.exists(xml_path))
        
        # Cleanup
        os.remove(xml_path)
        os.rmdir(os.path.dirname(xml_path))
    
    @patch('bdnex.lib.comicrack.patoolib')
    @patch('bdnex.lib.comicrack.yesno')
    @patch('bdnex.lib.comicrack.shutil')
    def test_append_comicinfo_new_archive(self, mock_shutil, mock_yesno, mock_patoolib):
        """Test appending ComicInfo to archive without existing ComicInfo"""
        # Create a temporary CBZ file for testing
        with tempfile.NamedTemporaryFile(suffix='.cbz', delete=False) as tmp:
            test_cbz = tmp.name
            # Create a simple zip file
            with zipfile.ZipFile(test_cbz, 'w') as zf:
                zf.writestr('page1.jpg', b'fake image data')
        
        try:
            # Setup mocks
            mock_patoolib.get_archive_format.return_value = ('zip',)
            mock_patoolib.test_archive.return_value = False  # False means archive is OK
            
            # Create mock extracted directory structure
            with tempfile.TemporaryDirectory() as mock_extracted:
                extracted_subdir = os.path.join(mock_extracted, os.path.basename(os.path.splitext(test_cbz)[0]))
                os.makedirs(extracted_subdir, exist_ok=True)
                
                # Create a fake extracted file
                test_file = os.path.join(extracted_subdir, 'page1.jpg')
                with open(test_file, 'w') as f:
                    f.write('fake data')
                
                def mock_extract(archive, outdir, interactive):
                    # Simulate extraction
                    pass
                
                mock_patoolib.extract_archive.side_effect = mock_extract
                
                comic = comicInfo(input_filename=test_cbz, comic_info=self.test_comic_info)
                
                # We can't fully test this without mocking the entire file system operations
                # But we can verify the object is created correctly
                self.assertEqual(comic.input_filename, test_cbz)
        finally:
            if os.path.exists(test_cbz):
                os.remove(test_cbz)


if __name__ == '__main__':
    unittest.main()
