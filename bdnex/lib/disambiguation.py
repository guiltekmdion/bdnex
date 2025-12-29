"""
Module de désambiguation pour gérer les correspondances ambiguës d'albums
à l'aide d'un système de notation multi-critères.
"""
import re
import logging
from typing import List, Tuple, Dict

from rapidfuzz import fuzz


class FilenameMetadataExtractor:
    """Extraire les métadonnées des noms de fichiers BD."""
    
    @staticmethod
    def extract_volume_number(filename: str) -> int:
        """
        Extraire le numéro de volume/tome du nom de fichier.
        Gère: "Tome 1", "Vol 1", "T1", "V1", etc.
        Retourne: numéro de volume ou -1 si non trouvé
        """
        # Remove file extension
        name = re.sub(r'\.(cbz|cbr)$', '', filename, flags=re.IGNORECASE)
        
        # Match patterns like "Tome 1", "Tom 1", "Vol 1", "V 1", "T 1", "#1", etc.
        patterns = [
            r'(?:tome|tom|vol|v|t|#)\s*(\d+)',
            r'(\d+)\s*(?:tome|tom|vol|v|t)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return -1
    
    @staticmethod
    def extract_title(filename: str) -> str:
        """
        Extraire le titre du nom de fichier.
        Supprime les informations de volume et l'extension du fichier.
        """
        # Remove file extension
        name = re.sub(r'\.(cbz|cbr)$', '', filename, flags=re.IGNORECASE)
        
        # Remove volume info
        name = re.sub(r'\s*(?:tome|tom|vol|v|t|#)\s*\d+.*?$', '', name, flags=re.IGNORECASE)
        
        return name.strip()


class CandidateScorer:
    """Évaluer et classer les candidats selon plusieurs critères."""
    
    # Poids pour différents critères
    WEIGHTS = {
        'cover_similarity': 0.40,      # 40%
        'volume_match': 0.30,          # 30%
        'editor_match': 0.15,          # 15%
        'year_match': 0.15,            # 15%
    }
    
    YEAR_TOLERANCE = 2  # Accepter l'année dans ±2 ans
    
    @staticmethod
    def calculate_cover_score(similarity: float) -> float:
        """
        Normalize cover similarity (0-100) to score (0-1).
        Considers similarities >= 30% as having some value.
        """
        if similarity < 30:
            return 0.0
        # Normalize from [30, 100] to [0, 1]
        return min((similarity - 30) / 70, 1.0)

    @staticmethod
    def calculate_title_score(filename_title: str, candidate_title: str) -> float:
        """Calculate fuzzy title match score (0-1).

        Returns 0.5 (neutral) when filename title is missing.
        """
        if not filename_title or filename_title.lower() == 'unknown':
            return 0.5
        if not candidate_title or candidate_title.lower() == 'unknown':
            return 0.0
        ratio = fuzz.token_set_ratio(filename_title, candidate_title)
        return round(ratio / 100.0, 3)

    @staticmethod
    def _should_apply_title_score(filename_title: str, candidate_title: str) -> bool:
        if not filename_title or filename_title.lower() == 'unknown':
            return False
        if not candidate_title or candidate_title.lower() == 'unknown':
            return False
        return True
    
    @staticmethod
    def calculate_volume_score(filename_volume: int, candidate_volume: int) -> float:
        """
        Calculate volume match score.
        1.0 if volumes match exactly, 0.0 if different.
        Returns 0.5 if volume not found in filename (neutral).
        """
        if filename_volume == -1:
            return 0.5  # Unknown, neutral score
        if filename_volume == candidate_volume:
            return 1.0
        return 0.0
    
    @staticmethod
    def calculate_editor_score(filename_editor: str, candidate_editor: str) -> float:
        """
        Calculate editor match score.
        1.0 if exact match, 0.0 otherwise.
        Returns 0.5 if editor not found in filename.
        """
        if not filename_editor or filename_editor.lower() == 'unknown':
            return 0.5  # Unknown, neutral score
        
        return 1.0 if filename_editor.lower() == candidate_editor.lower() else 0.0
    
    @staticmethod
    def calculate_year_score(filename_year: int, candidate_year: int) -> float:
        """
        Calculate year match score.
        1.0 if within tolerance, 0.0 if too far.
        Returns 0.5 if year not found in filename.
        """
        if filename_year == -1:
            return 0.5  # Unknown, neutral score
        
        if abs(filename_year - candidate_year) <= CandidateScorer.YEAR_TOLERANCE:
            return 1.0 - (abs(filename_year - candidate_year) / CandidateScorer.YEAR_TOLERANCE * 0.3)
        return 0.0
    
    @classmethod
    def score_candidate(
        cls,
        cover_similarity: float,
        filename_title: str = 'unknown',
        candidate_title: str = 'unknown',
        filename_volume: int = -1,
        candidate_volume: int = -1,
        filename_editor: str = "unknown",
        candidate_editor: str = "unknown",
        filename_year: int = -1,
        candidate_year: int = -1,
    ) -> float:
        """
        Calculate weighted score for a candidate.
        Returns: score between 0 and 1.
        """
        scores = {
            'cover_similarity': cls.calculate_cover_score(cover_similarity),
            'volume_match': cls.calculate_volume_score(filename_volume, candidate_volume),
            'editor_match': cls.calculate_editor_score(filename_editor, candidate_editor),
            'year_match': cls.calculate_year_score(filename_year, candidate_year),
        }

        base_score = sum(scores[key] * cls.WEIGHTS[key] for key in scores)

        # Optional: apply a small title-based adjustment when we have usable titles.
        # Kept separate from the base weights to preserve legacy behavior when titles are unknown.
        if cls._should_apply_title_score(filename_title, candidate_title):
            title_score = cls.calculate_title_score(filename_title, candidate_title)
            base_score += 0.2 * (title_score - 0.5)

        base_score = max(0.0, min(1.0, base_score))
        return round(base_score, 3)
    
    @classmethod
    def score_candidates(
        cls,
        filename_metadata: Dict,
        candidates_metadata: List[Dict],
        cover_similarities: List[float],
    ) -> List[Tuple[Dict, float]]:
        """
        Score multiple candidates and return ranked list.
        
        Args:
            filename_metadata: Extracted metadata from filename
            candidates_metadata: List of metadata dicts from candidates
            cover_similarities: List of cover similarity scores
        
        Returns:
            List of (candidate_metadata, score) tuples, sorted by score descending
        """
        scored = []
        
        for candidate, similarity in zip(candidates_metadata, cover_similarities):
            candidate_full_title = f"{candidate.get('series', '')} {candidate.get('title', '')}".strip()
            score = cls.score_candidate(
                cover_similarity=similarity,
                filename_title=filename_metadata.get('title', 'unknown'),
                candidate_title=candidate_full_title or candidate.get('title', 'unknown'),
                filename_volume=filename_metadata.get('volume', -1),
                candidate_volume=candidate.get('volume', -1),
                filename_editor=filename_metadata.get('editor', 'unknown'),
                candidate_editor=candidate.get('editor', 'unknown'),
                filename_year=filename_metadata.get('year', -1),
                candidate_year=candidate.get('year', -1),
            )
            scored.append((candidate, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
