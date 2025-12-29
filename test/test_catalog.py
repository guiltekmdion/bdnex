"""
Tests unitaires pour le gestionnaire de catalogue.
"""

import unittest
import tempfile
import os
import json
import csv
from pathlib import Path
import sys

# Ajouter le chemin parent pour importer bdnex
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bdnex.lib.catalog_manager import CatalogManager
from bdnex.lib.database import BDneXDB


class TestCatalogManager(unittest.TestCase):
    """Tests pour le CatalogManager."""
    
    def setUp(self):
        """Setup test database with sample data."""
        # Créer une DB temporaire
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.db = BDneXDB(self.temp_db.name)
        self.catalog = CatalogManager(self.temp_db.name)
        
        # Ajouter des données de test
        self._populate_test_data()
    
    def tearDown(self):
        """Clean up test database."""
        # Fermer les connexions
        if hasattr(self, 'catalog') and hasattr(self.catalog, 'db'):
            self.catalog.db.conn.close()
        if hasattr(self, 'db'):
            self.db.conn.close()
        # Supprimer le fichier de test
        if hasattr(self, 'temp_db'):
            try:
                os.unlink(self.temp_db.name)
            except:
                pass  # Ignore si déjà supprimé
    
    def _populate_test_data(self):
        """Populate database with test data."""
        # Créer une session directement en SQL
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO processing_sessions (
                directory, batch_mode, num_workers, status
            ) VALUES (?, ?, ?, ?)
        """, ('/test/dir', 0, 1, 'completed'))
        session_id = cursor.lastrowid
        self.db.conn.commit()
        
        # Ajouter des albums de test
        test_albums = [
            {
                'file_path': '/test/asterix1.cbz',
                'Series': 'Asterix',
                'Number': 1,
                'Title': 'Asterix le Gaulois',
                'Writer': 'Goscinny',
                'Penciller': 'Uderzo',
                'Publisher': 'Dargaud',
                'Year': 1961,
                'ISBN': '9782012101210',
                'Format': 'Cartonné',
                'Pages': 48,
                'Summary': 'Les aventures d\'Asterix le Gaulois'
            },
            {
                'file_path': '/test/asterix2.cbz',
                'Series': 'Asterix',
                'Number': 2,
                'Title': 'La Serpe d\'or',
                'Writer': 'Goscinny',
                'Penciller': 'Uderzo',
                'Publisher': 'Dargaud',
                'Year': 1962,
                'ISBN': '9782012101227',
                'Format': 'Cartonné',
                'Pages': 48,
                'Summary': 'Asterix cherche une serpe d\'or'
            },
            {
                'file_path': '/test/tintin1.cbz',
                'Series': 'Tintin',
                'Number': 1,
                'Title': 'Tintin au Congo',
                'Writer': 'Hergé',
                'Penciller': 'Hergé',
                'Publisher': 'Casterman',
                'Year': 1931,
                'ISBN': '9782203001152',
                'Format': 'Cartonné',
                'Pages': 62,
                'Summary': 'Tintin voyage au Congo'
            },
            {
                'file_path': '/test/luckyluke1.cbz',
                'Series': 'Lucky Luke',
                'Number': 1,
                'Title': 'La Mine d\'or de Dick Digger',
                'Writer': 'Morris',
                'Penciller': 'Morris',
                'Publisher': 'Dupuis',
                'Year': 1949,
                'ISBN': '9782800100012',
                'Format': 'Cartonné',
                'Pages': 46,
                'Summary': 'Lucky Luke cherche de l\'or'
            },
            {
                'file_path': '/test/luckyluke2.cbz',
                'Series': 'Lucky Luke',
                'Number': 2,
                'Title': 'Rodeo',
                'Writer': 'Morris',
                'Penciller': 'Morris',
                'Publisher': 'Dupuis',
                'Year': 1949,
                'ISBN': '9782800100029',
                'Format': 'Cartonné',
                'Pages': 46,
                'Summary': 'Lucky Luke participe à un rodeo'
            },
        ]
        
        for album in test_albums:
            # Ajouter l'album à bdgest_albums directement via SQL
            cursor = self.db.conn.cursor()
            # Métadonnées complètes en JSON
            metadata_json = json.dumps({
                'Writer': album['Writer'],
                'Penciller': album['Penciller'],
                'Format': album['Format'],
                'Summary': album['Summary']
            })
            
            cursor.execute("""
                INSERT INTO bdgest_albums (
                    series, volume, title, editor, year,
                    isbn, pages, metadata, url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                album['Series'], album['Number'], album['Title'],
                album['Publisher'], album['Year'], album['ISBN'],
                album['Pages'], metadata_json,
                f"https://m.bedetheque.com/BD-{album['Series']}-{album['Number']}.html"
            ))
            album_id = cursor.lastrowid
            
            # Ajouter le fichier traité directement (sans hash car fichier n'existe pas)
            cursor.execute("""
                INSERT INTO processed_files (
                    file_path, file_hash, file_size, bdgest_id, status, session_id,
                    confidence_score, processed_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                album['file_path'], 'test_hash_' + str(album_id), 1000000,
                album_id, 'success', session_id, 0.95
            ))
            
            self.db.conn.commit()
    
    def test_list_by_series(self):
        """Test listing BDs by series."""
        results = self.catalog.list_by_series(limit=10)
        
        # Vérifier qu'on a 3 séries
        self.assertEqual(len(results), 3)
        
        # Vérifier qu'Asterix et Lucky Luke ont 2 albums chacun
        series_counts = {row[0]: row[1] for row in results}
        self.assertEqual(series_counts.get('Asterix'), 2)
        self.assertEqual(series_counts.get('Lucky Luke'), 2)
        self.assertEqual(series_counts.get('Tintin'), 1)
        
        # Vérifier que Tintin est troisième (1 album)
        self.assertEqual(results[2][0], 'Tintin')
        self.assertEqual(results[2][1], 1)
    
    def test_list_by_publisher(self):
        """Test listing BDs by publisher."""
        results = self.catalog.list_by_publisher(limit=10)
        
        # Vérifier qu'on a 3 éditeurs
        self.assertEqual(len(results), 3)
        
        # Vérifier les counts
        publisher_counts = {pub: count for pub, count in results}
        self.assertEqual(publisher_counts['Dupuis'], 2)
        self.assertEqual(publisher_counts['Dargaud'], 2)
        self.assertEqual(publisher_counts['Casterman'], 1)
    
    def test_list_by_year(self):
        """Test listing BDs by year."""
        results = self.catalog.list_by_year(limit=10)
        
        # Vérifier qu'on a des résultats
        self.assertGreater(len(results), 0)
        
        # Vérifier que les années sont triées décroissant
        years = [year for year, count in results]
        self.assertEqual(years, sorted(years, reverse=True))
        
        # Vérifier les années présentes
        self.assertIn(1961, years)
        self.assertIn(1949, years)
    
    def test_search_by_title(self):
        """Test searching by title."""
        results = self.catalog.search('Gaulois')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Asterix le Gaulois')
    
    def test_search_by_series(self):
        """Test searching by series."""
        results = self.catalog.search('Lucky')
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result['series'], 'Lucky Luke')
    
    def test_search_by_writer(self):
        """Test searching by writer."""
        results = self.catalog.search('Goscinny')
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result['writer'], 'Goscinny')
    
    def test_search_with_publisher_filter(self):
        """Test searching with publisher filter."""
        results = self.catalog.search('Luke', publisher='Dupuis')
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result['publisher'], 'Dupuis')
    
    def test_search_with_year_filter(self):
        """Test searching with year filter."""
        results = self.catalog.search('Asterix', year=1961)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['year'], 1961)
    
    def test_search_no_results(self):
        """Test searching with no results."""
        results = self.catalog.search('NonExistent')
        
        self.assertEqual(len(results), 0)
    
    def test_get_stats(self):
        """Test getting library statistics."""
        stats = self.catalog.get_stats()
        
        # Vérifier les totaux
        self.assertEqual(stats['total_albums'], 5)
        self.assertEqual(stats['total_series'], 3)
        self.assertEqual(stats['total_publishers'], 3)
        
        # Vérifier les années
        self.assertEqual(stats['min_year'], 1931)
        self.assertEqual(stats['max_year'], 1962)
        self.assertEqual(stats['year_range'], '1931-1962')
        
        # Vérifier les top series
        self.assertEqual(len(stats['top_series']), 3)
        
        # Vérifier les top publishers
        self.assertEqual(len(stats['top_publishers']), 3)
    
    def test_export_csv(self):
        """Test exporting catalog to CSV."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w') as f:
            output_path = f.name
        
        try:
            count = self.catalog.export_csv(output_path)
            
            # Vérifier le nombre d'albums exportés
            self.assertEqual(count, 5)
            
            # Vérifier le contenu du CSV
            with open(output_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                self.assertEqual(len(rows), 5)
                
                # Vérifier les en-têtes
                self.assertIn('series', rows[0])
                self.assertIn('title', rows[0])
                self.assertIn('year', rows[0])
                
                # Vérifier qu'un album Asterix est présent
                asterix_albums = [r for r in rows if r['series'] == 'Asterix']
                self.assertEqual(len(asterix_albums), 2)
        finally:
            os.unlink(output_path)
    
    def test_export_csv_with_filters(self):
        """Test exporting catalog to CSV with filters."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w') as f:
            output_path = f.name
        
        try:
            filters = {'publisher': 'Dupuis'}
            count = self.catalog.export_csv(output_path, filters)
            
            # Vérifier que seuls les albums Dupuis sont exportés
            self.assertEqual(count, 2)
            
            # Vérifier le contenu
            with open(output_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                for row in rows:
                    self.assertEqual(row['publisher'], 'Dupuis')
        finally:
            os.unlink(output_path)
    
    def test_export_json(self):
        """Test exporting catalog to JSON."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w') as f:
            output_path = f.name
        
        try:
            count = self.catalog.export_json(output_path)
            
            # Vérifier le nombre d'albums exportés
            self.assertEqual(count, 5)
            
            # Vérifier le contenu du JSON
            with open(output_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                self.assertEqual(data['total'], 5)
                self.assertEqual(len(data['albums']), 5)
                
                # Vérifier la structure d'un album
                album = data['albums'][0]
                self.assertIn('series', album)
                self.assertIn('title', album)
                self.assertIn('year', album)
                self.assertIn('summary', album)
        finally:
            os.unlink(output_path)
    
    def test_export_json_with_filters(self):
        """Test exporting catalog to JSON with filters."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w') as f:
            output_path = f.name
        
        try:
            filters = {'series': 'Asterix'}
            count = self.catalog.export_json(output_path, filters)
            
            # Vérifier que seuls les albums Asterix sont exportés
            self.assertEqual(count, 2)
            
            # Vérifier le contenu
            with open(output_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                for album in data['albums']:
                    self.assertEqual(album['series'], 'Asterix')
        finally:
            os.unlink(output_path)


if __name__ == '__main__':
    unittest.main()
