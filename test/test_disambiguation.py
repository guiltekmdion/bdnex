"""
Tests unitaires pour bdnex.lib.disambiguation
"""
import unittest

from bdnex.lib.disambiguation import FilenameMetadataExtractor, CandidateScorer


class TestFilenameMetadataExtractor(unittest.TestCase):
    """Tests pour la classe FilenameMetadataExtractor"""
    
    def test_extract_volume_number_tome(self):
        """Test extraction du numéro de tome"""
        extractor = FilenameMetadataExtractor()
        
        # Test various "Tome" patterns
        self.assertEqual(extractor.extract_volume_number('Astérix Tome 1.cbz'), 1)
        self.assertEqual(extractor.extract_volume_number('Astérix tome 12.cbz'), 12)
        self.assertEqual(extractor.extract_volume_number('Astérix Tom 5.cbz'), 5)
        self.assertEqual(extractor.extract_volume_number('Série - Tome 42.cbr'), 42)
    
    def test_extract_volume_number_vol(self):
        """Test extraction avec 'Vol'"""
        extractor = FilenameMetadataExtractor()
        
        self.assertEqual(extractor.extract_volume_number('Series Vol 1.cbz'), 1)
        self.assertEqual(extractor.extract_volume_number('Series vol 23.cbz'), 23)
        self.assertEqual(extractor.extract_volume_number('Series V 7.cbz'), 7)
        self.assertEqual(extractor.extract_volume_number('Series v 15.cbr'), 15)
    
    def test_extract_volume_number_t(self):
        """Test extraction avec 'T'"""
        extractor = FilenameMetadataExtractor()
        
        self.assertEqual(extractor.extract_volume_number('Album T1.cbz'), 1)
        self.assertEqual(extractor.extract_volume_number('Album t 8.cbz'), 8)
        self.assertEqual(extractor.extract_volume_number('Album T 99.cbr'), 99)
    
    def test_extract_volume_number_hash(self):
        """Test extraction avec '#'"""
        extractor = FilenameMetadataExtractor()
        
        self.assertEqual(extractor.extract_volume_number('Comic #1.cbz'), 1)
        self.assertEqual(extractor.extract_volume_number('Comic #42.cbr'), 42)
    
    def test_extract_volume_number_trailing(self):
        """Test extraction avec numéro en fin de nom"""
        extractor = FilenameMetadataExtractor()
        
        self.assertEqual(extractor.extract_volume_number('Astérix 3 tome.cbz'), 3)
        self.assertEqual(extractor.extract_volume_number('Series 12vol.cbz'), 12)
    
    def test_extract_volume_number_not_found(self):
        """Test quand aucun numéro n'est trouvé"""
        extractor = FilenameMetadataExtractor()
        
        self.assertEqual(extractor.extract_volume_number('Album.cbz'), -1)
        self.assertEqual(extractor.extract_volume_number('NoNumber.cbr'), -1)
        self.assertEqual(extractor.extract_volume_number('Just Text.cbz'), -1)
    
    def test_extract_title(self):
        """Test extraction du titre"""
        extractor = FilenameMetadataExtractor()
        
        self.assertEqual(extractor.extract_title('Astérix Tome 1.cbz'), 'Astérix')
        self.assertEqual(extractor.extract_title('Lucky Luke Vol 12.cbz'), 'Lucky Luke')
        self.assertEqual(extractor.extract_title('Tintin T5.cbr'), 'Tintin')
        self.assertEqual(extractor.extract_title('XIII #3.cbz'), 'XIII')
    
    def test_extract_title_no_volume(self):
        """Test extraction du titre sans numéro de volume"""
        extractor = FilenameMetadataExtractor()
        
        self.assertEqual(extractor.extract_title('Album Name.cbz'), 'Album Name')
        self.assertEqual(extractor.extract_title('Simple Title.cbr'), 'Simple Title')
    
    def test_extract_title_removes_extension(self):
        """Test que l'extension est bien supprimée"""
        extractor = FilenameMetadataExtractor()
        
        self.assertEqual(extractor.extract_title('Title.cbz'), 'Title')
        self.assertEqual(extractor.extract_title('Title.CBZ'), 'Title')
        self.assertEqual(extractor.extract_title('Title.cbr'), 'Title')
        self.assertEqual(extractor.extract_title('Title.CBR'), 'Title')


class TestCandidateScorer(unittest.TestCase):
    """Tests pour la classe CandidateScorer"""
    
    def test_calculate_cover_score_high(self):
        """Test score de cover avec haute similarité"""
        scorer = CandidateScorer()
        
        self.assertAlmostEqual(scorer.calculate_cover_score(100), 1.0)
        self.assertAlmostEqual(scorer.calculate_cover_score(85), 0.786, places=2)
        self.assertAlmostEqual(scorer.calculate_cover_score(65), 0.5, places=2)
    
    def test_calculate_cover_score_low(self):
        """Test score de cover avec basse similarité"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_cover_score(29), 0.0)
        self.assertEqual(scorer.calculate_cover_score(0), 0.0)
        self.assertAlmostEqual(scorer.calculate_cover_score(30), 0.0)
    
    def test_calculate_cover_score_boundary(self):
        """Test score de cover aux limites"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_cover_score(30), 0.0)
        self.assertGreater(scorer.calculate_cover_score(31), 0.0)
        self.assertEqual(scorer.calculate_cover_score(100), 1.0)
    
    def test_calculate_volume_score_match(self):
        """Test score de volume avec correspondance"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_volume_score(1, 1), 1.0)
        self.assertEqual(scorer.calculate_volume_score(42, 42), 1.0)
    
    def test_calculate_volume_score_no_match(self):
        """Test score de volume sans correspondance"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_volume_score(1, 2), 0.0)
        self.assertEqual(scorer.calculate_volume_score(10, 20), 0.0)
    
    def test_calculate_volume_score_unknown(self):
        """Test score de volume inconnu"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_volume_score(-1, 5), 0.5)
        self.assertEqual(scorer.calculate_volume_score(-1, -1), 0.5)
    
    def test_calculate_editor_score_match(self):
        """Test score d'éditeur avec correspondance"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_editor_score('Dupuis', 'Dupuis'), 1.0)
        self.assertEqual(scorer.calculate_editor_score('dupuis', 'DUPUIS'), 1.0)
    
    def test_calculate_editor_score_no_match(self):
        """Test score d'éditeur sans correspondance"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_editor_score('Dupuis', 'Dargaud'), 0.0)
        self.assertEqual(scorer.calculate_editor_score('Marvel', 'DC'), 0.0)
    
    def test_calculate_editor_score_unknown(self):
        """Test score d'éditeur inconnu"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_editor_score('', 'Dupuis'), 0.5)
        self.assertEqual(scorer.calculate_editor_score('unknown', 'Dupuis'), 0.5)
        self.assertEqual(scorer.calculate_editor_score(None, 'Dupuis'), 0.5)
    
    def test_calculate_year_score_exact_match(self):
        """Test score d'année avec correspondance exacte"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_year_score(2020, 2020), 1.0)
        self.assertEqual(scorer.calculate_year_score(1999, 1999), 1.0)
    
    def test_calculate_year_score_within_tolerance(self):
        """Test score d'année dans la tolérance"""
        scorer = CandidateScorer()
        
        # Within tolerance (±2 years)
        self.assertGreater(scorer.calculate_year_score(2020, 2021), 0.5)
        self.assertGreater(scorer.calculate_year_score(2020, 2019), 0.5)
        self.assertGreater(scorer.calculate_year_score(2020, 2022), 0.0)
        self.assertGreater(scorer.calculate_year_score(2020, 2018), 0.0)
    
    def test_calculate_year_score_outside_tolerance(self):
        """Test score d'année hors tolérance"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_year_score(2020, 2025), 0.0)
        self.assertEqual(scorer.calculate_year_score(2020, 2015), 0.0)
        self.assertEqual(scorer.calculate_year_score(2000, 2010), 0.0)
    
    def test_calculate_year_score_unknown(self):
        """Test score d'année inconnue"""
        scorer = CandidateScorer()
        
        self.assertEqual(scorer.calculate_year_score(-1, 2020), 0.5)
        self.assertEqual(scorer.calculate_year_score(-1, -1), 0.5)
    
    def test_score_candidate_perfect_match(self):
        """Test scoring d'un candidat parfait"""
        scorer = CandidateScorer()
        
        score = scorer.score_candidate(
            cover_similarity=100,
            filename_volume=1,
            candidate_volume=1,
            filename_editor='Dupuis',
            candidate_editor='Dupuis',
            filename_year=2020,
            candidate_year=2020,
        )
        
        # Perfect match should be 1.0
        self.assertEqual(score, 1.0)
    
    def test_score_candidate_no_match(self):
        """Test scoring d'un candidat sans correspondance"""
        scorer = CandidateScorer()
        
        score = scorer.score_candidate(
            cover_similarity=10,
            filename_volume=1,
            candidate_volume=2,
            filename_editor='Dupuis',
            candidate_editor='Dargaud',
            filename_year=2020,
            candidate_year=2010,
        )
        
        # Poor match should be close to 0
        self.assertLess(score, 0.2)
    
    def test_score_candidate_cover_only(self):
        """Test scoring basé uniquement sur la cover"""
        scorer = CandidateScorer()
        
        score = scorer.score_candidate(
            cover_similarity=100,
            filename_volume=-1,  # Unknown
            candidate_volume=1,
            filename_editor='unknown',
            candidate_editor='Dupuis',
            filename_year=-1,
            candidate_year=2020,
        )
        
        # With unknowns (neutral 0.5), only cover (40%) matters
        # cover_score=1.0 * 0.40 + 0.5 * 0.30 + 0.5 * 0.15 + 0.5 * 0.15 = 0.70
        self.assertAlmostEqual(score, 0.7, places=2)
    
    def test_score_candidate_weights(self):
        """Test que les poids sont appliqués correctement"""
        scorer = CandidateScorer()
        
        # Perfect cover (40%), perfect volume (30%), no editor (15% neutral), no year (15% neutral)
        score = scorer.score_candidate(
            cover_similarity=100,
            filename_volume=1,
            candidate_volume=1,
            filename_editor='unknown',
            candidate_editor='Dupuis',
            filename_year=-1,
            candidate_year=2020,
        )
        
        # 1.0*0.40 + 1.0*0.30 + 0.5*0.15 + 0.5*0.15 = 0.85
        self.assertAlmostEqual(score, 0.85, places=2)
    
    def test_score_candidates_sorting(self):
        """Test le tri des candidats par score"""
        scorer = CandidateScorer()
        
        filename_metadata = {
            'volume': 1,
            'editor': 'Dupuis',
            'year': 2020,
        }
        
        candidates_metadata = [
            {'volume': 1, 'editor': 'Dupuis', 'year': 2020},  # Perfect match
            {'volume': 2, 'editor': 'Dargaud', 'year': 2015},  # Poor match
            {'volume': 1, 'editor': 'Dupuis', 'year': 2019},  # Good match
        ]
        
        cover_similarities = [100, 50, 90]
        
        scored = scorer.score_candidates(
            filename_metadata,
            candidates_metadata,
            cover_similarities
        )
        
        # Should be sorted by score descending
        self.assertEqual(len(scored), 3)
        self.assertGreater(scored[0][1], scored[1][1])
        self.assertGreater(scored[1][1], scored[2][1])
        
        # Best candidate should be the perfect match
        self.assertEqual(scored[0][0]['volume'], 1)
        self.assertEqual(scored[0][0]['editor'], 'Dupuis')
        self.assertEqual(scored[0][0]['year'], 2020)
    
    def test_score_candidates_empty_list(self):
        """Test scoring avec liste vide"""
        scorer = CandidateScorer()
        
        scored = scorer.score_candidates({}, [], [])
        
        self.assertEqual(scored, [])
    
    def test_score_candidates_single_candidate(self):
        """Test scoring avec un seul candidat"""
        scorer = CandidateScorer()
        
        filename_metadata = {'volume': 1}
        candidates_metadata = [{'volume': 1}]
        cover_similarities = [80]
        
        scored = scorer.score_candidates(
            filename_metadata,
            candidates_metadata,
            cover_similarities
        )
        
        self.assertEqual(len(scored), 1)
        self.assertIsInstance(scored[0][1], float)
        self.assertGreater(scored[0][1], 0)


if __name__ == '__main__':
    unittest.main()
