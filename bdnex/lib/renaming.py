"""
Module de renommage automatique des fichiers BD selon des templates configurables.

Ce module permet de renommer automatiquement les fichiers BD en utilisant des templates
personnalisables avec des variables extraites des métadonnées.

Variables supportées:
    %Series - Nom de la série
    %Number - Numéro du tome
    %Title - Titre de l'album
    %Year - Année de publication
    %Publisher - Éditeur
    %Author - Auteur
    %ISBN - ISBN
    %Edition - Édition

Exemples de templates:
    "%Series - Tome %Number - %Title (%Year)"
    "%Series/%Series - %Number"
    "%Publisher/%Series/%Number - %Title"
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import unicodedata


class TemplateParser:
    """Parse et valide les templates de renommage."""
    
    VALID_VARIABLES = {
        '%Series', '%Number', '%Title', '%Year', 
        '%Publisher', '%Author', '%ISBN', '%Edition'
    }
    
    def __init__(self):
        self.variable_pattern = re.compile(r'%[A-Za-z]+')
    
    def parse(self, template: str) -> List[str]:
        """
        Parse un template et retourne la liste des variables utilisées.
        
        Args:
            template: Template à parser (ex: "%Series - Tome %Number")
            
        Returns:
            Liste des variables trouvées (ex: ['%Series', '%Number'])
            
        Raises:
            ValueError: Si le template contient des variables invalides
        """
        variables = self.variable_pattern.findall(template)
        
        # Valider les variables
        invalid = [v for v in variables if v not in self.VALID_VARIABLES]
        if invalid:
            raise ValueError(f"Variables invalides dans le template: {invalid}")
        
        return variables
    
    def validate(self, template: str) -> bool:
        """
        Valide un template.
        
        Args:
            template: Template à valider
            
        Returns:
            True si valide, False sinon
        """
        try:
            self.parse(template)
            return True
        except ValueError:
            return False


class VariableSubstitutor:
    """Substitue les variables dans un template avec des valeurs réelles."""
    
    def substitute(self, template: str, metadata: Dict[str, any]) -> str:
        """
        Remplace les variables du template par les valeurs des métadonnées.
        
        Args:
            template: Template avec variables (ex: "%Series - Tome %Number")
            metadata: Dictionnaire des métadonnées (ex: {'Series': 'Asterix', 'Number': 12})
            
        Returns:
            Template avec valeurs substituées (ex: "Asterix - Tome 12")
        """
        result = template
        
        # Mapper les noms de variables aux clés de métadonnées
        variable_map = {
            '%Series': 'Series',
            '%Number': 'Number',
            '%Title': 'Title',
            '%Year': 'Year',
            '%Publisher': 'Publisher',
            '%Author': 'Writer',  # Writer dans ComicInfo
            '%ISBN': 'ISBN',
            '%Edition': 'AlternateSeries'  # Édition dans AlternateSeries
        }
        
        for var, key in variable_map.items():
            if var in result:
                value = metadata.get(key, '')
                if value:
                    # Formater le numéro avec zéro padding si c'est Number
                    if key == 'Number' and isinstance(value, (int, float)):
                        value = f"{int(value):02d}"
                    result = result.replace(var, str(value))
                else:
                    # Si la variable n'a pas de valeur, la retirer proprement
                    # Ex: "Series - Tome %Number" devient "Series" si Number vide
                    result = self._clean_empty_variable(result, var)
        
        return result.strip()
    
    def _clean_empty_variable(self, text: str, variable: str) -> str:
        """
        Nettoie une variable vide et les séparateurs adjacents.
        
        Args:
            text: Texte contenant la variable
            variable: Variable à nettoyer
            
        Returns:
            Texte nettoyé
        """
        # Retirer la variable et les séparateurs adjacents (-, /, etc.)
        patterns = [
            f' - {variable}',  # " - %Var"
            f'{variable} - ',  # "%Var - "
            f'/{variable}',     # "/%Var"
            f'{variable}/',     # "%Var/"
            f'({variable})',    # "(%Var)"
            f' {variable}',     # " %Var"
            f'{variable} ',     # "%Var "
            variable            # "%Var" seul
        ]
        
        for pattern in patterns:
            text = text.replace(pattern, '')
        
        # Nettoyer les espaces/séparateurs en trop
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s*-\s*$', '', text)  # Tiret final
        text = re.sub(r'^\s*-\s*', '', text)  # Tiret initial
        
        return text


class FilenameSanitizer:
    """Sanitize les noms de fichiers pour les rendre valides sur tous les OS."""
    
    INVALID_CHARS = r'[<>:"/\\|?*]'
    MAX_FILENAME_LENGTH = 255
    
    def sanitize(self, filename: str, replacement: str = '_') -> str:
        """
        Sanitize un nom de fichier.
        
        Args:
            filename: Nom de fichier à sanitizer
            replacement: Caractère de remplacement pour les caractères invalides
            
        Returns:
            Nom de fichier sanitized
        """
        # Normaliser les caractères Unicode (NFD -> NFC)
        filename = unicodedata.normalize('NFC', filename)
        
        # Remplacer les caractères invalides
        filename = re.sub(self.INVALID_CHARS, replacement, filename)
        
        # Retirer les espaces multiples
        filename = re.sub(r'\s+', ' ', filename)
        
        # Limiter la longueur
        name, ext = os.path.splitext(filename)
        
        # Retirer les points en fin de nom (problème sur Windows)
        name = name.rstrip('.')
        
        if len(name) > self.MAX_FILENAME_LENGTH - len(ext):
            name = name[:self.MAX_FILENAME_LENGTH - len(ext)]
        filename = name + ext
        
        return filename.strip()


class RenameManager:
    """Gère le renommage des fichiers avec backup et dry-run."""
    
    def __init__(self, backup_enabled: bool = True, dry_run: bool = False):
        """
        Initialize le RenameManager.
        
        Args:
            backup_enabled: Si True, crée un backup avant de renommer
            dry_run: Si True, simule le renommage sans modifier les fichiers
        """
        self.backup_enabled = backup_enabled
        self.dry_run = dry_run
        self.parser = TemplateParser()
        self.substitutor = VariableSubstitutor()
        self.sanitizer = FilenameSanitizer()
    
    def generate_new_filename(self, template: str, metadata: Dict[str, any], 
                            current_filepath: str) -> str:
        """
        Génère le nouveau nom de fichier basé sur le template et les métadonnées.
        
        Args:
            template: Template de renommage
            metadata: Métadonnées du fichier
            current_filepath: Chemin actuel du fichier
            
        Returns:
            Nouveau nom de fichier (avec extension)
            
        Raises:
            ValueError: Si le template est invalide
        """
        # Valider le template
        if not self.parser.validate(template):
            raise ValueError(f"Template invalide: {template}")
        
        # Substituer les variables
        new_name = self.substitutor.substitute(template, metadata)
        
        # Ajouter l'extension d'origine
        _, ext = os.path.splitext(current_filepath)
        new_name = new_name + ext
        
        # Sanitizer le nom
        new_name = self.sanitizer.sanitize(new_name)
        
        return new_name
    
    def rename_file(self, filepath: str, template: str, 
                   metadata: Dict[str, any]) -> Tuple[bool, str, str]:
        """
        Renomme un fichier selon le template et les métadonnées.
        
        Args:
            filepath: Chemin du fichier à renommer
            template: Template de renommage
            metadata: Métadonnées du fichier
            
        Returns:
            Tuple (success, old_path, new_path)
            success: True si le renommage a réussi
            old_path: Ancien chemin du fichier
            new_path: Nouveau chemin du fichier
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le template est invalide
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable: {filepath}")
        
        # Générer le nouveau nom
        new_filename = self.generate_new_filename(template, metadata, str(filepath))
        
        # Construire le nouveau chemin (même répertoire)
        new_filepath = filepath.parent / new_filename
        
        # Si le nom ne change pas, ne rien faire
        if filepath == new_filepath:
            return True, str(filepath), str(new_filepath)
        
        # Si le fichier cible existe déjà, ajouter un suffixe
        if new_filepath.exists() and not self.dry_run:
            counter = 1
            name, ext = os.path.splitext(new_filename)
            while new_filepath.exists():
                new_filename = f"{name} ({counter}){ext}"
                new_filepath = filepath.parent / new_filename
                counter += 1
        
        # Mode dry-run: juste simuler
        if self.dry_run:
            return True, str(filepath), str(new_filepath)
        
        # Backup si activé
        if self.backup_enabled:
            backup_path = filepath.parent / f".backup_{filepath.name}"
            try:
                shutil.copy2(filepath, backup_path)
            except Exception as e:
                return False, str(filepath), f"Erreur backup: {e}"
        
        # Renommer le fichier
        try:
            filepath.rename(new_filepath)
            
            # Supprimer le backup si réussi
            if self.backup_enabled:
                backup_path.unlink(missing_ok=True)
            
            return True, str(filepath), str(new_filepath)
        except Exception as e:
            # Restaurer le backup en cas d'erreur
            if self.backup_enabled and backup_path.exists():
                shutil.copy2(backup_path, filepath)
                backup_path.unlink(missing_ok=True)
            
            return False, str(filepath), f"Erreur: {e}"
    
    def rename_batch(self, files: List[Tuple[str, Dict[str, any]]], 
                    template: str) -> List[Tuple[bool, str, str]]:
        """
        Renomme plusieurs fichiers en batch.
        
        Args:
            files: Liste de tuples (filepath, metadata)
            template: Template de renommage
            
        Returns:
            Liste de tuples (success, old_path, new_path) pour chaque fichier
        """
        results = []
        for filepath, metadata in files:
            try:
                result = self.rename_file(filepath, template, metadata)
                results.append(result)
            except Exception as e:
                results.append((False, filepath, f"Erreur: {e}"))
        
        return results
