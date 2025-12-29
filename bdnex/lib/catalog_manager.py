"""
Gestionnaire de catalogue pour explorer et exporter la bibliothèque BD.

Ce module fournit des fonctionnalités pour:
- Lister les BD par série, éditeur, année
- Rechercher dans la bibliothèque
- Afficher des statistiques
- Exporter en CSV/JSON
"""

import logging
import csv
import json
from typing import List, Dict, Optional, Tuple
from collections import Counter
from pathlib import Path

from bdnex.lib.database import BDneXDB


class CatalogManager:
    """Gestionnaire de catalogue pour la bibliothèque BD."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize le CatalogManager.
        
        Args:
            db_path: Chemin vers la base de données (None = base par défaut)
        """
        self.logger = logging.getLogger(__name__)
        self.db = BDneXDB(db_path)
    
    def list_by_series(self, limit: int = 100) -> List[Tuple[str, int]]:
        """
        Liste les séries avec leur nombre d'albums.
        
        Args:
            limit: Nombre maximum de résultats
            
        Returns:
            Liste de tuples (série, nombre_albums) triée par nombre décroissant
        """
        query = """
            SELECT b.series, COUNT(*) as count
            FROM processed_files pf
            JOIN bdgest_albums b ON pf.bdgest_id = b.id
            WHERE pf.status IN ('success', 'manual')
            AND b.series IS NOT NULL
            AND b.series != ''
            GROUP BY b.series
            ORDER BY count DESC, b.series ASC
            LIMIT ?
        """
        
        cursor = self.db.conn.cursor()
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        return [(row[0], row[1]) for row in results]
    
    def list_by_publisher(self, limit: int = 100) -> List[Tuple[str, int]]:
        """
        Liste les éditeurs avec leur nombre d'albums.
        
        Args:
            limit: Nombre maximum de résultats
            
        Returns:
            Liste de tuples (éditeur, nombre_albums) triée par nombre décroissant
        """
        query = """
            SELECT b.editor, COUNT(*) as count
            FROM processed_files pf
            JOIN bdgest_albums b ON pf.bdgest_id = b.id
            WHERE pf.status IN ('success', 'manual')
            AND b.editor IS NOT NULL
            AND b.editor != ''
            GROUP BY b.editor
            ORDER BY count DESC, b.editor ASC
            LIMIT ?
        """
        
        cursor = self.db.conn.cursor()
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        return [(row[0], row[1]) for row in results]
    
    def list_by_year(self, limit: int = 100) -> List[Tuple[int, int]]:
        """
        Liste les années avec leur nombre d'albums.
        
        Args:
            limit: Nombre maximum de résultats
            
        Returns:
            Liste de tuples (année, nombre_albums) triée par année décroissante
        """
        query = """
            SELECT b.year, COUNT(*) as count
            FROM processed_files pf
            JOIN bdgest_albums b ON pf.bdgest_id = b.id
            WHERE pf.status IN ('success', 'manual')
            AND b.year IS NOT NULL
            AND b.year > 0
            GROUP BY b.year
            ORDER BY b.year DESC
            LIMIT ?
        """
        
        cursor = self.db.conn.cursor()
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        return [(int(row[0]), row[1]) for row in results]
    
    def search(self, query: str, publisher: Optional[str] = None, 
              year: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """
        Recherche dans la bibliothèque.
        
        Args:
            query: Terme de recherche (dans titre, série)
            publisher: Filtre par éditeur (optionnel)
            year: Filtre par année (optionnel)
            limit: Nombre maximum de résultats
            
        Returns:
            Liste de dictionnaires contenant les métadonnées des albums trouvés
        """
        sql = """
            SELECT DISTINCT
                pf.file_path,
                b.series,
                b.volume,
                b.title,
                b.editor,
                b.year,
                b.isbn,
                b.url,
                b.metadata
            FROM processed_files pf
            JOIN bdgest_albums b ON pf.bdgest_id = b.id
            WHERE pf.status IN ('success', 'manual')
            AND (
                b.title LIKE ? OR
                b.series LIKE ? OR
                b.metadata LIKE ?
            )
        """
        
        params = [f"%{query}%"] * 3
        
        if publisher:
            sql += " AND b.editor = ?"
            params.append(publisher)
        
        if year:
            sql += " AND b.year = ?"
            params.append(year)
        
        sql += " ORDER BY b.series, b.volume LIMIT ?"
        params.append(limit)
        
        cursor = self.db.conn.cursor()
        cursor.execute(sql, tuple(params))
        results = cursor.fetchall()
        
        return_list = []
        for row in results:
            metadata_dict = {}
            try:
                if row[8]:  # metadata JSON
                    metadata_dict = json.loads(row[8])
            except:
                pass
            
            return_list.append({
                'file_path': row[0],
                'series': row[1],
                'number': row[2],
                'title': row[3],
                'publisher': row[4],
                'year': row[5],
                'isbn': row[6],
                'url': row[7],
                'writer': metadata_dict.get('Writer', 'N/A'),
                'penciller': metadata_dict.get('Penciller', 'N/A')
            })
        
        return return_list
    
    def get_stats(self) -> Dict:
        """
        Récupère les statistiques de la bibliothèque.
        
        Returns:
            Dictionnaire contenant les statistiques
        """
        # Total albums
        query_total = """
            SELECT COUNT(*)
            FROM processed_files
            WHERE status IN ('success', 'manual')
        """
        cursor = self.db.conn.cursor()
        cursor.execute(query_total)
        total = cursor.fetchone()[0]
        
        # Nombre de séries uniques
        query_series = """
            SELECT COUNT(DISTINCT b.series)
            FROM processed_files pf
            JOIN bdgest_albums b ON pf.bdgest_id = b.id
            WHERE pf.status IN ('success', 'manual')
            AND b.series IS NOT NULL
            AND b.series != ''
        """
        cursor.execute(query_series)
        series_count = cursor.fetchone()[0]
        
        # Nombre d'éditeurs uniques
        query_publishers = """
            SELECT COUNT(DISTINCT b.editor)
            FROM processed_files pf
            JOIN bdgest_albums b ON pf.bdgest_id = b.id
            WHERE pf.status IN ('success', 'manual')
            AND b.editor IS NOT NULL
            AND b.editor != ''
        """
        cursor.execute(query_publishers)
        publishers_count = cursor.fetchone()[0]
        
        # Années (min, max)
        query_years = """
            SELECT MIN(b.year), MAX(b.year)
            FROM processed_files pf
            JOIN bdgest_albums b ON pf.bdgest_id = b.id
            WHERE pf.status IN ('success', 'manual')
            AND b.year IS NOT NULL
            AND b.year > 0
        """
        cursor.execute(query_years)
        years = cursor.fetchone()
        min_year = years[0] if years[0] else 0
        max_year = years[1] if years[1] else 0
        
        # Top 5 séries
        top_series = self.list_by_series(limit=5)
        
        # Top 5 éditeurs
        top_publishers = self.list_by_publisher(limit=5)
        
        return {
            'total_albums': total,
            'total_series': series_count,
            'total_publishers': publishers_count,
            'year_range': f"{min_year}-{max_year}" if min_year and max_year else "N/A",
            'min_year': min_year,
            'max_year': max_year,
            'top_series': top_series,
            'top_publishers': top_publishers
        }
    
    def export_csv(self, output_path: str, filters: Optional[Dict] = None) -> int:
        """
        Exporte la bibliothèque en CSV.
        
        Args:
            output_path: Chemin du fichier CSV de sortie
            filters: Filtres optionnels (publisher, year, series)
            
        Returns:
            Nombre de lignes exportées
        """
        filters = filters or {}
        
        sql = """
            SELECT
                pf.file_path,
                b.series,
                b.volume,
                b.title,
                b.editor,
                b.year,
                b.isbn,
                b.pages,
                b.url,
                b.metadata
            FROM processed_files pf
            JOIN bdgest_albums b ON pf.bdgest_id = b.id
            WHERE pf.status IN ('success', 'manual')
        """
        
        params = []
        
        if filters.get('publisher'):
            sql += " AND b.editor = ?"
            params.append(filters['publisher'])
        
        if filters.get('year'):
            sql += " AND b.year = ?"
            params.append(filters['year'])
        
        if filters.get('series'):
            sql += " AND b.series = ?"
            params.append(filters['series'])
        
        sql += " ORDER BY b.series, b.volume"
        
        cursor = self.db.conn.cursor()
        cursor.execute(sql, tuple(params))
        results = cursor.fetchall()
        
        # Écrire le CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['file_path', 'series', 'number', 'title', 'writer', 
                         'penciller', 'publisher', 'year', 'isbn', 'format', 
                         'pages', 'url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in results:
                # Extraire métadonnées JSON
                metadata_dict = {}
                try:
                    if row[9]:  # metadata JSON
                        metadata_dict = json.loads(row[9])
                except:
                    pass
                
                writer.writerow({
                    'file_path': row[0],
                    'series': row[1],
                    'number': row[2],
                    'title': row[3],
                    'writer': metadata_dict.get('Writer', ''),
                    'penciller': metadata_dict.get('Penciller', ''),
                    'publisher': row[4],
                    'year': row[5],
                    'isbn': row[6],
                    'format': metadata_dict.get('Format', ''),
                    'pages': row[7],
                    'url': row[8]
                })
        
        self.logger.info(f"Exporté {len(results)} album(s) vers {output_path}")
        return len(results)
    
    def export_json(self, output_path: str, filters: Optional[Dict] = None) -> int:
        """
        Exporte la bibliothèque en JSON.
        
        Args:
            output_path: Chemin du fichier JSON de sortie
            filters: Filtres optionnels (publisher, year, series)
            
        Returns:
            Nombre de lignes exportées
        """
        filters = filters or {}
        
        sql = """
            SELECT
                pf.file_path,
                b.series,
                b.volume,
                b.title,
                b.editor,
                b.year,
                b.isbn,
                b.pages,
                b.url,
                b.metadata
            FROM processed_files pf
            JOIN bdgest_albums b ON pf.bdgest_id = b.id
            WHERE pf.status IN ('success', 'manual')
        """
        
        params = []
        
        if filters.get('publisher'):
            sql += " AND b.editor = ?"
            params.append(filters['publisher'])
        
        if filters.get('year'):
            sql += " AND b.year = ?"
            params.append(filters['year'])
        
        if filters.get('series'):
            sql += " AND b.series = ?"
            params.append(filters['series'])
        
        sql += " ORDER BY b.series, b.volume"
        
        cursor = self.db.conn.cursor()
        cursor.execute(sql, tuple(params))
        results = cursor.fetchall()
        
        # Construire la liste de dictionnaires
        albums = []
        for row in results:
            # Extraire métadonnées JSON
            metadata_dict = {}
            try:
                if row[9]:  # metadata JSON
                    metadata_dict = json.loads(row[9])
            except:
                pass
            
            albums.append({
                'file_path': row[0],
                'series': row[1],
                'number': row[2],
                'title': row[3],
                'writer': metadata_dict.get('Writer', ''),
                'penciller': metadata_dict.get('Penciller', ''),
                'publisher': row[4],
                'year': row[5],
                'isbn': row[6],
                'format': metadata_dict.get('Format', ''),
                'pages': row[7],
                'summary': metadata_dict.get('Summary', ''),
                'url': row[8]
            })
        
        # Écrire le JSON
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump({
                'total': len(albums),
                'albums': albums
            }, jsonfile, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Exporté {len(results)} album(s) vers {output_path}")
        return len(results)
    
    def print_stats_summary(self):
        """Affiche un résumé des statistiques de la bibliothèque."""
        stats = self.get_stats()
        
        print("\n" + "=" * 80)
        print("STATISTIQUES DE LA BIBLIOTHÈQUE")
        print("=" * 80)
        print(f"Total d'albums: {stats['total_albums']}")
        print(f"Séries uniques: {stats['total_series']}")
        print(f"Éditeurs uniques: {stats['total_publishers']}")
        print(f"Années: {stats['year_range']}")
        print()
        
        if stats['top_series']:
            print("Top 5 séries:")
            print("-" * 80)
            for series, count in stats['top_series']:
                print(f"  {series:<60} {count:>5} albums")
            print()
        
        if stats['top_publishers']:
            print("Top 5 éditeurs:")
            print("-" * 80)
            for publisher, count in stats['top_publishers']:
                print(f"  {publisher:<60} {count:>5} albums")
        
        print("=" * 80 + "\n")
