"""
BDfugue.com Scraper Plugin for BDneX - Phase 4

Scrapes metadata from BDfugue.com (https://www.bdfugue.com/)
French online BD store with comprehensive metadata.
"""

import re
import logging
from typing import List, Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScraperResult


class BDfugueScraper(BaseScraper):
    """Scraper for BDfugue.com metadata."""
    
    BASE_URL = "https://www.bdfugue.com"
    SEARCH_URL = f"{BASE_URL}/recherche"
    
    @property
    def name(self) -> str:
        return "bdfugue"
    
    @property
    def priority(self) -> int:
        return 30  # Lower priority (commercial site)
    
    def search(
        self,
        query: str,
        series: Optional[str] = None,
        volume: Optional[int] = None,
        year: Optional[int] = None,
        limit: int = 10
    ) -> List[ScraperResult]:
        """Search BDfugue for matching albums."""
        results = []
        
        try:
            # Build search query
            search_query = query
            if series:
                search_query = f"{series} {query}"
            
            # Perform search
            params = {
                'q': search_query,
                'type': 'product'
            }
            
            response = requests.get(
                self.SEARCH_URL,
                params=params,
                timeout=self.timeout,
                headers={'User-Agent': 'BDneX/1.0'}
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse search results - BDfugue uses product listings
            products = soup.find_all('div', class_='product-item') or soup.find_all('article', class_='product')
            
            for product in products[:limit]:
                try:
                    result = self._parse_product(product, year)
                    if result and result.confidence > 0:
                        results.append(result)
                except Exception as e:
                    self.logger.debug(f"Error parsing product: {e}")
            
            self.logger.info(f"BDfugue search for '{query}': {len(results)} results")
            
        except Exception as e:
            self.logger.error(f"BDfugue search error: {e}")
        
        return results
    
    def _parse_product(self, product, filter_year: Optional[int] = None) -> Optional[ScraperResult]:
        """Parse a product listing."""
        try:
            # Extract link
            link_tag = product.find('a', class_='product-link') or product.find('a')
            if not link_tag or not link_tag.get('href'):
                return None
            
            url = urljoin(self.BASE_URL, link_tag['href'])
            
            # Extract title
            title_tag = product.find('h3', class_='product-title') or product.find('h2')
            if not title_tag:
                return None
            
            title_text = title_tag.get_text(strip=True)
            
            # Parse series and volume from title
            # Common format: "Series - Tome X - Title"
            series = None
            volume = None
            title = title_text
            
            # Try to match tome pattern
            tome_match = re.search(r'(.+?)\s*[-–]\s*(?:Tome|T\.?|Vol\.?)\s*(\d+)\s*[-–]\s*(.+)', title_text, re.IGNORECASE)
            if tome_match:
                series = tome_match.group(1).strip()
                volume = int(tome_match.group(2))
                title = tome_match.group(3).strip()
            else:
                # Alternative format: "Series T.X - Title"
                tome_match2 = re.search(r'(.+?)\s+T\.?(\d+)\s*[-–]\s*(.+)', title_text, re.IGNORECASE)
                if tome_match2:
                    series = tome_match2.group(1).strip()
                    volume = int(tome_match2.group(2))
                    title = tome_match2.group(3).strip()
            
            # Extract metadata from product info
            metadata_div = product.find('div', class_='product-info') or product.find('div', class_='product-meta')
            
            publisher = None
            year = None
            writer = None
            
            if metadata_div:
                # Look for publisher
                pub_span = metadata_div.find('span', text=re.compile(r'Éditeur|Editeur'))
                if pub_span:
                    pub_value = pub_span.find_next_sibling()
                    if pub_value:
                        publisher = pub_value.get_text(strip=True)
                
                # Look for year
                year_span = metadata_div.find('span', text=re.compile(r'Date de parution|Année'))
                if year_span:
                    year_value = year_span.find_next_sibling()
                    if year_value:
                        year_match = re.search(r'(\d{4})', year_value.get_text())
                        if year_match:
                            year = int(year_match.group(1))
                
                # Look for author
                author_span = metadata_div.find('span', text=re.compile(r'Auteur|Scénariste'))
                if author_span:
                    author_value = author_span.find_next_sibling()
                    if author_value:
                        writer = author_value.get_text(strip=True)
            
            # Filter by year if specified
            if filter_year and year and abs(year - filter_year) > 2:
                return None
            
            # Extract cover URL
            cover_url = None
            img_tag = product.find('img', class_='product-image') or product.find('img')
            if img_tag:
                cover_url = urljoin(self.BASE_URL, img_tag.get('src') or img_tag.get('data-src', ''))
            
            # Calculate confidence
            confidence = 60.0
            if series and volume:
                confidence += 15
            if year:
                confidence += 10
            if cover_url:
                confidence += 10
            if publisher:
                confidence += 5
            
            return ScraperResult(
                source=self.name,
                url=url,
                confidence=confidence,
                title=title,
                series=series,
                volume=volume,
                writer=writer,
                editor=publisher,
                year=year,
                cover_url=cover_url
            )
            
        except Exception as e:
            self.logger.debug(f"Error parsing product: {e}")
            return None
    
    def get_details(self, url: str) -> Optional[ScraperResult]:
        """Get detailed metadata for a specific product."""
        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={'User-Agent': 'BDneX/1.0'}
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract main title
            title_tag = soup.find('h1', class_='product-title') or soup.find('h1')
            if not title_tag:
                return None
            
            title_text = title_tag.get_text(strip=True)
            
            # Parse series, volume, title
            series = None
            volume = None
            title = title_text
            
            tome_match = re.search(r'(.+?)\s*[-–]\s*(?:Tome|T\.?)\s*(\d+)\s*[-–]\s*(.+)', title_text, re.IGNORECASE)
            if tome_match:
                series = tome_match.group(1).strip()
                volume = int(tome_match.group(2))
                title = tome_match.group(3).strip()
            
            # Extract product details table
            metadata = {}
            details_table = soup.find('table', class_='product-details') or soup.find('dl', class_='product-attributes')
            
            if details_table:
                if details_table.name == 'table':
                    rows = details_table.find_all('tr')
                    for row in rows:
                        label_td = row.find('th') or row.find('td', class_='label')
                        value_td = row.find('td', class_='value') or row.find_all('td')[1] if len(row.find_all('td')) > 1 else None
                        
                        if label_td and value_td:
                            self._extract_metadata_field(label_td.get_text(strip=True), value_td.get_text(strip=True), metadata)
                else:
                    # dl/dt/dd format
                    dts = details_table.find_all('dt')
                    dds = details_table.find_all('dd')
                    
                    for dt, dd in zip(dts, dds):
                        self._extract_metadata_field(dt.get_text(strip=True), dd.get_text(strip=True), metadata)
            
            # Extract description/summary
            summary = None
            desc_div = soup.find('div', class_='product-description') or soup.find('div', id='description')
            if desc_div:
                summary = desc_div.get_text(strip=True)
            
            # Extract cover image
            cover_url = None
            cover_img = soup.find('img', class_='product-image-main') or soup.find('img', itemprop='image')
            if cover_img:
                cover_url = urljoin(self.BASE_URL, cover_img.get('src') or cover_img.get('data-src', ''))
            
            return ScraperResult(
                source=self.name,
                url=url,
                confidence=90.0,
                title=title,
                series=series,
                volume=volume,
                writer=metadata.get('writer'),
                penciller=metadata.get('penciller'),
                colorist=metadata.get('colorist'),
                editor=metadata.get('publisher'),
                year=metadata.get('year'),
                isbn=metadata.get('isbn'),
                pages=metadata.get('pages'),
                format=metadata.get('format'),
                summary=summary,
                cover_url=cover_url
            )
            
        except Exception as e:
            self.logger.error(f"BDfugue get_details error for {url}: {e}")
            return None
    
    def _extract_metadata_field(self, label: str, value: str, metadata: dict) -> None:
        """Extract and store a metadata field."""
        label_lower = label.lower()
        
        if 'scénariste' in label_lower or 'scenario' in label_lower or 'auteur' in label_lower:
            metadata['writer'] = value
        elif 'dessinateur' in label_lower or 'dessin' in label_lower:
            metadata['penciller'] = value
        elif 'coloriste' in label_lower:
            metadata['colorist'] = value
        elif 'éditeur' in label_lower or 'editeur' in label_lower:
            metadata['publisher'] = value
        elif 'date' in label_lower or 'parution' in label_lower or 'année' in label_lower:
            year_match = re.search(r'(\d{4})', value)
            if year_match:
                metadata['year'] = int(year_match.group(1))
        elif 'isbn' in label_lower or 'ean' in label_lower:
            metadata['isbn'] = self.normalize_isbn(value)
        elif 'pages' in label_lower or 'planches' in label_lower:
            pages_match = re.search(r'(\d+)', value)
            if pages_match:
                metadata['pages'] = int(pages_match.group(1))
        elif 'format' in label_lower or 'reliure' in label_lower:
            metadata['format'] = value
