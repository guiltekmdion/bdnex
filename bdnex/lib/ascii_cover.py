"""
ASCII Art Cover Preview for BDneX - Phase 3

Converts cover images to ASCII art for terminal display.
Uses PIL for image processing and custom character mapping.
"""

import logging
from typing import Optional
from pathlib import Path
from io import BytesIO

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ASCIICoverGenerator:
    """Generate ASCII art from cover images."""
    
    # Character sets for different detail levels
    ASCII_CHARS_DETAILED = "@%#*+=-:. "
    ASCII_CHARS_SIMPLE = "@#*=-:. "
    ASCII_CHARS_BLOCKS = "█▓▒░ "
    
    def __init__(self, width: int = 40, height: int = 50, char_set: str = "blocks"):
        """
        Initialize ASCII cover generator.
        
        Args:
            width: Width in characters
            height: Height in characters
            char_set: Character set to use ("detailed", "simple", "blocks")
        """
        self.logger = logging.getLogger(__name__)
        self.width = width
        self.height = height
        
        if char_set == "detailed":
            self.chars = self.ASCII_CHARS_DETAILED
        elif char_set == "simple":
            self.chars = self.ASCII_CHARS_SIMPLE
        else:
            self.chars = self.ASCII_CHARS_BLOCKS
    
    def image_to_ascii(self, image_path: str, add_border: bool = True) -> Optional[str]:
        """
        Convert image to ASCII art.
        
        Args:
            image_path: Path to image file
            add_border: Whether to add a border around the ASCII art
            
        Returns:
            ASCII art string, or None if conversion failed
        """
        if not PIL_AVAILABLE:
            self.logger.warning("PIL not available, cannot generate ASCII art")
            return None
        
        try:
            # Open and process image
            img = Image.open(image_path)
            
            # Resize image to fit terminal
            # Account for character aspect ratio (roughly 2:1)
            aspect_ratio = img.height / img.width
            new_height = int(self.width * aspect_ratio * 0.5)
            if new_height > self.height:
                new_height = self.height
                new_width = int(new_height / aspect_ratio * 2)
            else:
                new_width = self.width
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to grayscale
            img = img.convert('L')
            
            # Convert pixels to ASCII
            pixels = img.getdata()
            ascii_str = ""
            
            for i, pixel in enumerate(pixels):
                # Map pixel brightness (0-255) to character
                char_index = int((pixel / 255) * (len(self.chars) - 1))
                ascii_str += self.chars[char_index]
                
                # Add newline at end of row
                if (i + 1) % new_width == 0:
                    ascii_str += "\n"
            
            if add_border:
                ascii_str = self._add_border(ascii_str, new_width)
            
            return ascii_str
            
        except Exception as e:
            self.logger.error(f"Error converting image to ASCII: {e}")
            return None
    
    def _add_border(self, ascii_art: str, width: int) -> str:
        """Add a border around ASCII art."""
        lines = ascii_art.strip().split('\n')
        
        # Top border
        bordered = "┌" + "─" * width + "┐\n"
        
        # Content with side borders
        for line in lines:
            bordered += "│" + line + "│\n"
        
        # Bottom border
        bordered += "└" + "─" * width + "┘\n"
        
        return bordered
    
    def generate_preview(
        self,
        cover_path: str,
        title: str = "",
        width: int = 30,
        height: int = 40
    ) -> str:
        """
        Generate a preview with title and ASCII cover.
        
        Args:
            cover_path: Path to cover image
            title: Title to display above cover
            width: Width in characters
            height: Height in characters
            
        Returns:
            Formatted preview string
        """
        # Temporarily adjust dimensions
        old_width, old_height = self.width, self.height
        self.width, self.height = width, height
        
        ascii_art = self.image_to_ascii(cover_path, add_border=True)
        
        # Restore original dimensions
        self.width, self.height = old_width, old_height
        
        if not ascii_art:
            return f"\n{title}\n[Cover preview not available]\n"
        
        preview = ""
        if title:
            # Center title
            title_line = title[:width].center(width + 2)
            preview = f"\n{title_line}\n"
        
        preview += ascii_art
        return preview
    
    @staticmethod
    def get_simple_placeholder(width: int = 30, height: int = 20) -> str:
        """
        Get a simple placeholder when image is not available.
        
        Args:
            width: Width in characters
            height: Height in characters
            
        Returns:
            Placeholder ASCII art
        """
        lines = []
        lines.append("┌" + "─" * width + "┐")
        
        # Top padding
        for _ in range(height // 2 - 2):
            lines.append("│" + " " * width + "│")
        
        # Text in middle
        text = "NO COVER"
        text_line = "│" + text.center(width) + "│"
        lines.append(text_line)
        
        text2 = "AVAILABLE"
        text_line2 = "│" + text2.center(width) + "│"
        lines.append(text_line2)
        
        # Bottom padding
        for _ in range(height // 2 - 2):
            lines.append("│" + " " * width + "│")
        
        lines.append("└" + "─" * width + "┘")
        
        return "\n".join(lines)
