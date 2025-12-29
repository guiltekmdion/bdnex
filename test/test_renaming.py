"""
Tests unitaires pour le module de renommage automatique.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Ajouter le chemin parent pour importer bdnex
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bdnex.lib.renaming import (
    TemplateParser, VariableSubstitutor, FilenameSanitizer, RenameManager
)


class TestTemplateParser(unittest.TestCase):
    """Tests pour le TemplateParser."""
    
    def setUp(self):
        self.parser = TemplateParser()
    
    def test_parse_simple_template(self):
        """Test parsing d'un template simple."""
        template = "%Series - Tome %Number"
        variables = self.parser.parse(template)
        self.assertEqual(variables, ['%Series', '%Number'])
    
    def test_parse_complex_template(self):
        """Test parsing d'un template complexe."""
        template = "%Publisher/%Series/%Series - %Number - %Title (%Year)"
        variables = self.parser.parse(template)
        self.assertEqual(variables, ['%Publisher', '%Series', '%Series', '%Number', '%Title', '%Year'])
    
    def test_parse_no_variables(self):
        """Test parsing d'un template sans variables."""
        template = "Static Filename"
        variables = self.parser.parse(template)
        self.assertEqual(variables, [])
    
    def test_parse_invalid_variable(self):
        """Test parsing avec variable invalide."""
        template = "%Series - %InvalidVar"
        with self.assertRaises(ValueError) as cm:
            self.parser.parse(template)
        self.assertIn("Variables invalides", str(cm.exception))
    
    def test_validate_valid_template(self):
        """Test validation d'un template valide."""
        template = "%Series - Tome %Number - %Title"
        self.assertTrue(self.parser.validate(template))
    
    def test_validate_invalid_template(self):
        """Test validation d'un template invalide."""
        template = "%Series - %BadVariable"
        self.assertFalse(self.parser.validate(template))


class TestVariableSubstitutor(unittest.TestCase):
    """Tests pour le VariableSubstitutor."""
    
    def setUp(self):
        self.substitutor = VariableSubstitutor()
    
    def test_substitute_all_variables(self):
        """Test substitution de toutes les variables."""
        template = "%Series - Tome %Number - %Title (%Year)"
        metadata = {
            'Series': 'Asterix',
            'Number': 12,
            'Title': 'Asterix aux Jeux Olympiques',
            'Year': 1968
        }
        result = self.substitutor.substitute(template, metadata)
        self.assertEqual(result, "Asterix - Tome 12 - Asterix aux Jeux Olympiques (1968)")
    
    def test_substitute_with_padding(self):
        """Test substitution avec zero padding sur Number."""
        template = "%Series - %Number"
        metadata = {'Series': 'Lucky Luke', 'Number': 5}
        result = self.substitutor.substitute(template, metadata)
        self.assertEqual(result, "Lucky Luke - 05")
    
    def test_substitute_missing_variable(self):
        """Test substitution avec variable manquante."""
        template = "%Series - Tome %Number - %Title"
        metadata = {'Series': 'Tintin', 'Number': 1}
        result = self.substitutor.substitute(template, metadata)
        # %Title manquant doit être nettoyé
        self.assertEqual(result, "Tintin - Tome 01")
    
    def test_substitute_empty_metadata(self):
        """Test substitution avec métadonnées vides."""
        template = "%Series - Tome %Number"
        metadata = {}
        result = self.substitutor.substitute(template, metadata)
        # Toutes les variables doivent être nettoyées, "Tome" peut rester
        self.assertIn(result, ["", "Tome"])
    
    def test_substitute_author_mapping(self):
        """Test mapping Writer vers %Author."""
        template = "%Series par %Author"
        metadata = {'Series': 'Asterix', 'Writer': 'Goscinny'}
        result = self.substitutor.substitute(template, metadata)
        self.assertEqual(result, "Asterix par Goscinny")
    
    def test_clean_empty_variable_with_dash(self):
        """Test nettoyage de variable vide avec tiret."""
        text = "Series - %Title"
        result = self.substitutor._clean_empty_variable(text, '%Title')
        self.assertEqual(result, "Series")
    
    def test_clean_empty_variable_with_slash(self):
        """Test nettoyage de variable vide avec slash."""
        text = "Publisher/%Series"
        result = self.substitutor._clean_empty_variable(text, '%Series')
        self.assertEqual(result, "Publisher")


class TestFilenameSanitizer(unittest.TestCase):
    """Tests pour le FilenameSanitizer."""
    
    def setUp(self):
        self.sanitizer = FilenameSanitizer()
    
    def test_sanitize_invalid_chars(self):
        """Test sanitization des caractères invalides."""
        filename = 'File<>:"/\\|?*.cbz'
        result = self.sanitizer.sanitize(filename)
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)
        self.assertNotIn(':', result)
        self.assertNotIn('"', result)
        self.assertNotIn('/', result)
        self.assertNotIn('\\', result)
        self.assertNotIn('|', result)
        self.assertNotIn('?', result)
        self.assertNotIn('*', result)
    
    def test_sanitize_unicode(self):
        """Test sanitization des caractères Unicode."""
        filename = "Astérix - L'été.cbz"
        result = self.sanitizer.sanitize(filename)
        # Les accents doivent être préservés (NFC normalization)
        self.assertIn('é', result)
        self.assertIn('é', result)
    
    def test_sanitize_multiple_spaces(self):
        """Test sanitization des espaces multiples."""
        filename = "Series   -   Title.cbz"
        result = self.sanitizer.sanitize(filename)
        self.assertEqual(result, "Series - Title.cbz")
    
    def test_sanitize_trailing_dot(self):
        """Test sanitization du point final."""
        filename = "Series - Title..cbz"
        result = self.sanitizer.sanitize(filename)
        # Le point final (avant extension) doit être retiré
        self.assertFalse(result.endswith('..cbz'))
    
    def test_sanitize_long_filename(self):
        """Test sanitization de nom trop long."""
        long_name = "A" * 300 + ".cbz"
        result = self.sanitizer.sanitize(long_name)
        # Le nom doit être tronqué (255 - len('.cbz') = 251)
        self.assertLessEqual(len(result), 255)
        self.assertTrue(result.endswith('.cbz'))
    
    def test_sanitize_custom_replacement(self):
        """Test sanitization avec remplacement personnalisé."""
        filename = "File/Name.cbz"
        result = self.sanitizer.sanitize(filename, replacement='-')
        self.assertEqual(result, "File-Name.cbz")


class TestRenameManager(unittest.TestCase):
    """Tests pour le RenameManager."""
    
    def setUp(self):
        # Créer un répertoire temporaire pour les tests
        self.temp_dir = tempfile.mkdtemp()
        self.manager = RenameManager(backup_enabled=False, dry_run=True)
    
    def tearDown(self):
        # Nettoyer le répertoire temporaire
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generate_new_filename(self):
        """Test génération d'un nouveau nom de fichier."""
        template = "%Series - Tome %Number"
        metadata = {'Series': 'Asterix', 'Number': 12}
        current_filepath = "/path/to/file.cbz"
        
        new_filename = self.manager.generate_new_filename(template, metadata, current_filepath)
        self.assertEqual(new_filename, "Asterix - Tome 12.cbz")
    
    def test_generate_new_filename_invalid_template(self):
        """Test génération avec template invalide."""
        template = "%Series - %BadVar"
        metadata = {'Series': 'Asterix'}
        current_filepath = "/path/to/file.cbz"
        
        with self.assertRaises(ValueError):
            self.manager.generate_new_filename(template, metadata, current_filepath)
    
    def test_rename_file_dry_run(self):
        """Test renommage en mode dry-run."""
        # Créer un fichier temporaire
        test_file = Path(self.temp_dir) / "original.cbz"
        test_file.write_text("test content")
        
        template = "%Series - %Number"
        metadata = {'Series': 'Test', 'Number': 1}
        
        success, old_path, new_path = self.manager.rename_file(str(test_file), template, metadata)
        
        self.assertTrue(success)
        self.assertIn("original.cbz", old_path)
        self.assertIn("Test - 01.cbz", new_path)
        # En dry-run, le fichier ne doit pas être renommé
        self.assertTrue(test_file.exists())
        self.assertFalse(Path(new_path).exists())
    
    def test_rename_file_real(self):
        """Test renommage réel."""
        # Créer un fichier temporaire
        test_file = Path(self.temp_dir) / "original.cbz"
        test_file.write_text("test content")
        
        # Manager en mode réel (pas dry-run)
        manager = RenameManager(backup_enabled=False, dry_run=False)
        
        template = "%Series - %Number"
        metadata = {'Series': 'Test', 'Number': 1}
        
        success, old_path, new_path = manager.rename_file(str(test_file), template, metadata)
        
        self.assertTrue(success)
        self.assertFalse(test_file.exists())
        self.assertTrue(Path(new_path).exists())
        
        # Vérifier le contenu
        self.assertEqual(Path(new_path).read_text(), "test content")
    
    def test_rename_file_with_backup(self):
        """Test renommage avec backup."""
        # Créer un fichier temporaire
        test_file = Path(self.temp_dir) / "original.cbz"
        test_file.write_text("test content")
        
        # Manager avec backup activé
        manager = RenameManager(backup_enabled=True, dry_run=False)
        
        template = "%Series - %Number"
        metadata = {'Series': 'Test', 'Number': 1}
        
        success, old_path, new_path = manager.rename_file(str(test_file), template, metadata)
        
        self.assertTrue(success)
        # Le backup doit être supprimé après succès
        backup_file = Path(self.temp_dir) / ".backup_original.cbz"
        self.assertFalse(backup_file.exists())
    
    def test_rename_file_not_found(self):
        """Test renommage d'un fichier inexistant."""
        template = "%Series - %Number"
        metadata = {'Series': 'Test', 'Number': 1}
        
        with self.assertRaises(FileNotFoundError):
            self.manager.rename_file("/nonexistent/file.cbz", template, metadata)
    
    def test_rename_file_no_change(self):
        """Test renommage sans changement de nom."""
        # Créer un fichier avec le nom cible
        test_file = Path(self.temp_dir) / "Test - 01.cbz"
        test_file.write_text("test content")
        
        template = "%Series - %Number"
        metadata = {'Series': 'Test', 'Number': 1}
        
        success, old_path, new_path = self.manager.rename_file(str(test_file), template, metadata)
        
        self.assertTrue(success)
        self.assertEqual(old_path, new_path)
    
    def test_rename_file_duplicate_target(self):
        """Test renommage avec fichier cible existant."""
        # Créer deux fichiers
        test_file1 = Path(self.temp_dir) / "original1.cbz"
        test_file2 = Path(self.temp_dir) / "Test - 01.cbz"
        test_file1.write_text("content1")
        test_file2.write_text("content2")
        
        # Manager en mode réel
        manager = RenameManager(backup_enabled=False, dry_run=False)
        
        template = "%Series - %Number"
        metadata = {'Series': 'Test', 'Number': 1}
        
        success, old_path, new_path = manager.rename_file(str(test_file1), template, metadata)
        
        self.assertTrue(success)
        # Le fichier doit avoir un suffixe (1)
        self.assertIn("Test - 01 (1).cbz", new_path)
    
    def test_rename_batch(self):
        """Test renommage en batch."""
        # Créer plusieurs fichiers
        files_metadata = []
        for i in range(3):
            test_file = Path(self.temp_dir) / f"file{i}.cbz"
            test_file.write_text(f"content{i}")
            files_metadata.append((str(test_file), {'Series': 'Test', 'Number': i+1}))
        
        template = "%Series - %Number"
        results = self.manager.rename_batch(files_metadata, template)
        
        self.assertEqual(len(results), 3)
        for success, old_path, new_path in results:
            self.assertTrue(success)
            self.assertIn("Test -", new_path)


if __name__ == '__main__':
    unittest.main()
