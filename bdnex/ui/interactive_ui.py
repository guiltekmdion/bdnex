"""
Enhanced Interactive UI for BDneX - Phase 3 Implementation

Provides rich CLI interface with:
- InquirerPy menus for candidate selection
- Rich tables for metadata comparison
- ASCII art cover previews
- Manual metadata editing
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text


class InteractiveUI:
    """Enhanced interactive UI for album disambiguation and metadata management."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.console = Console()
    
    def display_metadata_comparison(
        self, 
        file_metadata: Dict[str, Any],
        candidates: List[Tuple[Dict, float, Optional[str]]]
    ) -> None:
        """
        Display side-by-side comparison of file metadata and candidates.
        
        Args:
            file_metadata: Extracted metadata from filename
            candidates: List of (metadata_dict, score, cover_path) tuples
        """
        table = Table(title="📚 Metadata Comparison", show_header=True, header_style="bold magenta")
        
        # Add columns
        table.add_column("Field", style="cyan", width=15)
        table.add_column("From File", style="yellow", width=25)
        
        for i, (_, score, _) in enumerate(candidates[:3], 1):
            table.add_column(f"Candidate {i}\n({score:.0f}%)", style="green", width=25)
        
        # Define fields to compare
        fields = [
            ("Series", "series", "Série"),
            ("Volume", "volume", "Tome"),
            ("Title", "title", "Titre"),
            ("Writer", "writer", "Scénariste"),
            ("Penciller", "penciller", "Dessinateur"),
            ("Publisher", "editor", "Éditeur"),
            ("Year", "year", "Année"),
            ("ISBN", "isbn", "ISBN"),
            ("Pages", "pages", "Pages"),
        ]
        
        for label, file_key, candidate_key in fields:
            row = [label]
            
            # Add file value
            file_value = file_metadata.get(file_key, "")
            row.append(str(file_value) if file_value else "-")
            
            # Add candidate values
            for metadata, _, _ in candidates[:3]:
                candidate_value = metadata.get(candidate_key, metadata.get(file_key, ""))
                row.append(str(candidate_value) if candidate_value else "-")
            
            table.add_row(*row)
        
        self.console.print(table)
        self.console.print()
    
    def select_candidate(
        self,
        filename: str,
        file_metadata: Dict[str, Any],
        candidates: List[Tuple[Dict, float, Optional[str]]],
        show_covers: bool = True
    ) -> Optional[Dict]:
        """
        Interactive menu to select best candidate match.
        
        Args:
            filename: Name of the BD file
            file_metadata: Extracted metadata from filename
            candidates: List of (metadata_dict, score, cover_path) tuples
            show_covers: Whether to show ASCII art cover previews
            
        Returns:
            Selected candidate metadata dict, or None if skipped/manual
        """
        self.console.print()
        self.console.print(Panel.fit(
            f"[bold cyan]File:[/bold cyan] {filename}",
            title="🔍 Album Disambiguation",
            border_style="blue"
        ))
        self.console.print()
        
        # Display metadata comparison
        self.display_metadata_comparison(file_metadata, candidates)
        
        # Build choices for InquirerPy
        choices = []
        
        for i, (metadata, score, cover_path) in enumerate(candidates, 1):
            series = metadata.get('Série', metadata.get('series', 'Unknown'))
            volume = metadata.get('Tome', metadata.get('volume', '?'))
            title = metadata.get('Titre', metadata.get('title', 'Unknown'))
            year = metadata.get('Année', metadata.get('year', ''))
            
            label = f"[{score:.0f}%] {series} #{volume} - {title}"
            if year:
                label += f" ({year})"
            
            choices.append(Choice(value=metadata, name=label))
        
        choices.extend([
            Separator(),
            Choice(value="manual", name="✏️  Edit metadata manually"),
            Choice(value="skip", name="⏭️  Skip this file"),
            Choice(value="quit", name="❌ Quit"),
        ])
        
        result = inquirer.select(
            message="Select the correct match:",
            choices=choices,
            default=candidates[0][0] if candidates else "skip",
            pointer="👉",
            style={
                "pointer": "#61afef",
                "highlighted": "#61afef bold",
                "separator": "#6c6c6c",
            }
        ).execute()
        
        if result == "manual":
            return self.edit_metadata_manually(file_metadata)
        elif result == "skip":
            self.console.print("[yellow]⏭️  Skipped[/yellow]\n")
            return None
        elif result == "quit":
            self.console.print("[red]❌ Quitting...[/red]\n")
            return {"action": "quit"}
        else:
            self.console.print("[green]✓ Selected[/green]\n")
            return result
    
    def edit_metadata_manually(self, initial_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interactive form to manually edit metadata fields.
        
        Args:
            initial_metadata: Initial metadata values to pre-fill
            
        Returns:
            Updated metadata dictionary
        """
        self.console.print()
        self.console.print(Panel.fit(
            "📝 [bold]Manual Metadata Entry[/bold]",
            border_style="cyan"
        ))
        self.console.print()
        
        metadata = {}
        
        # Series
        metadata['Série'] = inquirer.text(
            message="Series (Série):",
            default=str(initial_metadata.get('series', initial_metadata.get('Série', ''))),
            validate=lambda x: len(x) > 0 or "Series name is required"
        ).execute()
        
        # Volume
        volume_str = inquirer.text(
            message="Volume (Tome):",
            default=str(initial_metadata.get('volume', initial_metadata.get('Tome', ''))),
            validate=lambda x: x.isdigit() or x == '' or "Must be a number"
        ).execute()
        metadata['Tome'] = int(volume_str) if volume_str else None
        
        # Title
        metadata['Titre'] = inquirer.text(
            message="Title (Titre):",
            default=str(initial_metadata.get('title', initial_metadata.get('Titre', '')))
        ).execute()
        
        # Writer
        metadata['Scénariste'] = inquirer.text(
            message="Writer (Scénariste):",
            default=str(initial_metadata.get('writer', initial_metadata.get('Scénariste', '')))
        ).execute()
        
        # Penciller
        metadata['Dessinateur'] = inquirer.text(
            message="Penciller (Dessinateur):",
            default=str(initial_metadata.get('penciller', initial_metadata.get('Dessinateur', '')))
        ).execute()
        
        # Publisher
        metadata['Éditeur'] = inquirer.text(
            message="Publisher (Éditeur):",
            default=str(initial_metadata.get('editor', initial_metadata.get('Éditeur', '')))
        ).execute()
        
        # Year
        year_str = inquirer.text(
            message="Year (Année):",
            default=str(initial_metadata.get('year', initial_metadata.get('Année', ''))),
            validate=lambda x: x.isdigit() or x == '' or "Must be a valid year"
        ).execute()
        metadata['Année'] = int(year_str) if year_str else None
        
        # ISBN
        metadata['ISBN'] = inquirer.text(
            message="ISBN:",
            default=str(initial_metadata.get('isbn', initial_metadata.get('ISBN', '')))
        ).execute()
        
        # Confirm
        self.console.print()
        confirm = inquirer.confirm(
            message="Save this metadata?",
            default=True
        ).execute()
        
        if confirm:
            self.console.print("[green]✓ Metadata saved[/green]\n")
            return metadata
        else:
            self.console.print("[yellow]⚠ Cancelled[/yellow]\n")
            return {"action": "skip"}
    
    def confirm_batch_action(
        self,
        action: str,
        count: int,
        details: Optional[str] = None
    ) -> bool:
        """
        Ask user to confirm a batch action.
        
        Args:
            action: Description of the action (e.g., "Process files")
            count: Number of items affected
            details: Optional additional details
            
        Returns:
            True if confirmed, False otherwise
        """
        message = f"{action} for {count} file(s)"
        if details:
            message += f"\n{details}"
        
        return inquirer.confirm(
            message=message,
            default=True
        ).execute()
    
    def show_progress_summary(
        self,
        total: int,
        successful: int,
        failed: int,
        skipped: int
    ) -> None:
        """
        Display a summary of processing results.
        
        Args:
            total: Total files processed
            successful: Number of successful operations
            failed: Number of failures
            skipped: Number of skipped files
        """
        table = Table(title="📊 Processing Summary", box=None)
        table.add_column("Status", style="bold")
        table.add_column("Count", justify="right", style="cyan")
        table.add_column("Percentage", justify="right")
        
        def pct(n):
            return f"{(n/total*100):.1f}%" if total > 0 else "0%"
        
        table.add_row("✓ Successful", str(successful), pct(successful), style="green")
        table.add_row("✗ Failed", str(failed), pct(failed), style="red")
        table.add_row("⏭️  Skipped", str(skipped), pct(skipped), style="yellow")
        table.add_row("━" * 10, "━" * 5, "━" * 10, style="dim")
        table.add_row("Total", str(total), "100%", style="bold")
        
        self.console.print()
        self.console.print(table)
        self.console.print()
