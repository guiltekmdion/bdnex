"""
BDGest.com Scraper Plugin for BDneX - Phase 4

Scrapes metadata from BDGest.com (https://www.bdgest.com/)
French comic book database with extensive metadata.
"""

import re
import logging
from typing import List, Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScraperResult


class BDGestScraper(BaseScraper):
    """Scraper for BDGest.com metadata."""
    
    BASE_URL = "https://www.bdgest.com"
    SEARCH_URL = f"{BASE_URL}/search.php"
    
    @property
    def name(self) -> str:
        return "bdgest"
    
    @property
    def priority(self) -> int:
        return 20  # Medium priority (after bedetheque)
    
    def search(
        self,
        query: str,
        series: Optional[str] = None,
        volume: Optional[int] = None,
        year: Optional[int] = None,
        limit: int = 10
    ) -> List[ScraperResult]:
        """Search BDGest for matching albums."""
        results = []
        
        try:
            # Build search query
            search_query = query
            if series:
                search_query = f"{series} {query}"
            
            # Perform search
            params = {
                'q': search_query,
                'type': 'album'
            }
            
            response = requests.get(
                self.SEARCH_URL,
                params=params,
                timeout=self.timeout,
                headers={'User-Agent': 'BDneX/1.0'}
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse search results
            album_items = soup.find_all('div', class_='album-item') or soup.find_all('div', class_='search-result')
            
            for item in album_items[:limit]:
                try:
                    result = self._parse_search_result(item, year)
                    if result and result.confidence > 0:
                        results.append(result)
                except Exception as e:
                    self.logger.debug(f"Error parsing search result: {e}")
            
            self.logger.info(f"BDGest search for '{query}': {len(results)} results")
            
        except Exception as e:
            self.logger.error(f"BDGest search error: {e}")
        
        return results
    
    def _parse_search_result(self, item, filter_year: Optional[int] = None) -> Optional[ScraperResult]:
        """Parse a search result item."""
        try:
            # Extract link
            link_tag = item.find('a', href=re.compile(r'/album-\d+'))
            if not link_tag:
                return None
            
            url = urljoin(self.BASE_URL, link_tag['href'])
            
            # Extract title and series
            title_tag = item.find('h3') or item.find('div', class_='title')
            if not title_tag:
                return None
            
            title_text = title_tag.get_text(strip=True)
            
            # Try to extract series and volume from title
            # Format is usually: "Series Tome X - Title"
            series = None
            volume = None
            title = title_text
            
            tome_match = re.search(r'(.+?)\s+Tome\s+(\d+)\s*[-:]\s*(.+)', title_text, re.IGNORECASE)
            if tome_match:
                series = tome_match.group(1).strip()
                volume = int(tome_match.group(2))
                title = tome_match.group(3).strip()
            
            # Extract year
            year = None
            year_tag = item.find('span', class_='year') or item.find('span', text=re.compile(r'\d{4}'))
            if year_tag:
                year_match = re.search(r'(\d{4})', year_tag.get_text())
                if year_match:
                    year = int(year_match.group(1))
            
            # Filter by year if specified
            if filter_year and year and abs(year - filter_year) > 2:
                return None
            
            # Extract publisher
            publisher = None
            pub_tag = item.find('span', class_='publisher') or item.find('span', text=re.compile(r'Éditeur|Editeur'))
            if pub_tag:
                publisher = pub_tag.get_text(strip=True).replace('Éditeur:', '').replace('Editeur:', '').strip()
            
            # Extract cover URL
            cover_url = None
            img_tag = item.find('img')
            if img_tag and img_tag.get('src'):
                cover_url = urljoin(self.BASE_URL, img_tag['src'])
            
            # Calculate confidence score
            confidence = 70.0
            if series and volume:
                confidence += 10
            if year:
                confidence += 10
            if cover_url:
                confidence += 10
            
            return ScraperResult(
                source=self.name,
                url=url,
                confidence=confidence,
                title=title,
                series=series,
                volume=volume,
                editor=publisher,
                year=year,
                cover_url=cover_url
            )
            
        except Exception as e:
            self.logger.debug(f"Error parsing search result: {e}")
            return None
    
    def get_details(self, url: str) -> Optional[ScraperResult]:
        """Get detailed metadata for a specific album."""
        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={'User-Agent': 'BDneX/1.0'}
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract main title
            title_tag = soup.find('h1', class_='album-title') or soup.find('h1')
            if not title_tag:
                return None
            
            title_text = title_tag.get_text(strip=True)
            
            # Parse series, volume, title
            series = None
            volume = None
            title = title_text
            
            tome_match = re.search(r'(.+?)\s+Tome\s+(\d+)\s*[-:]\s*(.+)', title_text, re.IGNORECASE)
            if tome_match:
                series = tome_match.group(1).strip()
                volume = int(tome_match.group(2))
                title = tome_match.group(3).strip()
            
            # Extract metadata table
            metadata = {}
            info_table = soup.find('table', class_='info') or soup.find('div', class_='metadata')
            
            if info_table:
                rows = info_table.find_all('tr') if info_table.name == 'table' else info_table.find_all('div', class_='row')
                
                for row in rows:
                    label_tag = row.find('th') or row.find('span', class_='label')
                    value_tag = row.find('td') or row.find('span', class_='value')
                    
                    if label_tag and value_tag:
                        label = label_tag.get_text(strip=True).lower()
                        value = value_tag.get_text(strip=True)
                        
                        if 'scénariste' in label or 'scenario' in label:
                            metadata['writer'] = value
                        elif 'dessinateur' in label or 'dessin' in label:
                            metadata['penciller'] = value
                        elif 'coloriste' in label or 'couleur' in label:
                            metadata['colorist'] = value
                        elif 'encreur' in label:
                            metadata['inker'] = value
                        elif 'éditeur' in label or 'editeur' in label:
                            metadata['publisher'] = value
                        elif 'année' in label or 'annee' in label or 'date' in label:
                            year_match = re.search(r'(\d{4})', value)
                            if year_match:
                                metadata['year'] = int(year_match.group(1))
                        elif 'isbn' in label:
                            metadata['isbn'] = self.normalize_isbn(value)
                        elif 'pages' in label or 'planches' in label:
                            pages_match = re.search(r'(\d+)', value)
                            if pages_match:
                                metadata['pages'] = int(pages_match.group(1))
                        elif 'format' in label:
                            metadata['format'] = value
            
            # Extract summary
            summary = None
            summary_tag = soup.find('div', class_='summary') or soup.find('div', class_='synopsis')
            if summary_tag:
                summary = summary_tag.get_text(strip=True)
            
            # Extract cover URL
            cover_url = None
            cover_img = soup.find('img', class_='cover') or soup.find('img', alt=re.compile(r'couverture', re.IGNORECASE))
            if cover_img and cover_img.get('src'):
                cover_url = urljoin(self.BASE_URL, cover_img['src'])
            
            return ScraperResult(
                source=self.name,
                url=url,
                confidence=95.0,  # High confidence for direct detail page
                title=title,
                series=series,
                volume=volume,
                writer=metadata.get('writer'),
                penciller=metadata.get('penciller'),
                colorist=metadata.get('colorist'),
                inker=metadata.get('inker'),
                editor=metadata.get('publisher'),
                year=metadata.get('year'),
                isbn=metadata.get('isbn'),
                pages=metadata.get('pages'),
                format=metadata.get('format'),
                summary=summary,
                cover_url=cover_url
            )
            
        except Exception as e:
            self.logger.error(f"BDGest get_details error for {url}: {e}")
            return None
