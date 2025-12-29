"""
Challenge UI module - generates interactive HTML interface for album disambiguation.
"""
import os
import webbrowser
import tempfile
import base64
import logging
import http.server
import socketserver
import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from urllib.parse import urlparse, parse_qs


class ChallengeUI:
    """Generate and display interactive HTML challenge for album disambiguation."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def image_to_base64(image_path: str) -> str:
        """Convert image file to base64 data URL."""
        try:
            with open(image_path, 'rb') as img_file:
                data = base64.b64encode(img_file.read()).decode()
                # Determine file extension
                ext = Path(image_path).suffix.lower()
                mime_type = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.bmp': 'image/bmp',
                    '.webp': 'image/webp',
                }.get(ext, 'image/jpeg')
                return f"data:{mime_type};base64,{data}"
        except Exception as e:
            logging.getLogger(__name__).error(f"Error converting image to base64: {e}")
            return ""
    
    @staticmethod
    def generate_html(
        local_cover_path: str,
        candidates: List[Tuple[Dict, float, str]],  # (metadata, score, cover_path)
        filename: str,
    ) -> str:
        """
        Generate HTML page for disambiguation challenge.
        
        Args:
            local_cover_path: Path to local cover image
            candidates: List of (metadata_dict, score, cover_image_path) tuples
            filename: Name of the BD file being processed
        
        Returns:
            HTML content as string
        """
        local_cover_b64 = ChallengeUI.image_to_base64(local_cover_path)
        
        # Build candidates HTML
        candidates_html = ""
        for idx, (metadata, score, cover_path) in enumerate(candidates, 1):
            cover_b64 = ChallengeUI.image_to_base64(cover_path)
            score_percent = int(score * 100)
            score_color = ChallengeUI.get_score_color(score)
            
            title = metadata.get('title', 'Unknown')
            volume = metadata.get('volume', '?')
            editor = metadata.get('editor', 'Unknown')
            year = metadata.get('year', '?')
            pages = metadata.get('pages', '?')
            url = metadata.get('url', '#')
            
            candidates_html += f"""
            <div class="candidate-card" data-idx="{idx}">
                <div class="candidate-header">
                    <h3>Option {idx}</h3>
                    <div class="score-badge" style="background-color: {score_color};">
                        <span class="score-value">{score_percent}%</span>
                        <span class="score-label">Match</span>
                    </div>
                </div>
                
                <div class="candidate-image">
                    <img src="{cover_b64}" alt="Candidate {idx} cover" />
                </div>
                
                <div class="candidate-info">
                    <div class="info-row">
                        <span class="info-label">Title:</span>
                        <span class="info-value">{title}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Volume:</span>
                        <span class="info-value">{volume}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Editor:</span>
                        <span class="info-value">{editor}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Year:</span>
                        <span class="info-value">{year}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Pages:</span>
                        <span class="info-value">{pages}</span>
                    </div>
                </div>
                
                <div class="candidate-actions">
                    <button class="btn-select" onclick="selectCandidate({idx})">Select This</button>
                    <a class="btn-bedetheque" href="{url}" target="_blank">View on Bédéthèque</a>
                </div>
            </div>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>BDneX Album Disambiguation Challenge</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                
                .container {{
                    max-width: 1400px;
                    width: 100%;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                
                .header h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                
                .header p {{
                    font-size: 16px;
                    opacity: 0.9;
                }}
                
                .content {{
                    padding: 40px;
                }}
                
                .local-section {{
                    margin-bottom: 40px;
                    text-align: center;
                }}
                
                .local-section h2 {{
                    margin-bottom: 20px;
                    color: #333;
                    font-size: 20px;
                }}
                
                .local-cover {{
                    display: inline-block;
                    max-width: 300px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    overflow: hidden;
                }}
                
                .local-cover img {{
                    width: 100%;
                    height: auto;
                    display: block;
                }}
                
                .candidates-section h2 {{
                    margin-bottom: 30px;
                    color: #333;
                    font-size: 20px;
                }}
                
                .candidates-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                    gap: 20px;
                }}
                
                .candidate-card {{
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    overflow: hidden;
                    transition: all 0.3s ease;
                    cursor: pointer;
                }}
                
                .candidate-card:hover {{
                    border-color: #667eea;
                    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
                    transform: translateY(-4px);
                }}
                
                .candidate-card.selected {{
                    border-color: #667eea;
                    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
                    background: #f8f9ff;
                }}
                
                .candidate-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px;
                    background: #f9f9f9;
                    border-bottom: 1px solid #e0e0e0;
                }}
                
                .candidate-header h3 {{
                    font-size: 16px;
                    color: #333;
                }}
                
                .score-badge {{
                    padding: 8px 16px;
                    border-radius: 20px;
                    color: white;
                    font-weight: bold;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 2px;
                }}
                
                .score-value {{
                    font-size: 18px;
                }}
                
                .score-label {{
                    font-size: 10px;
                    text-transform: uppercase;
                    opacity: 0.9;
                }}
                
                .candidate-image {{
                    padding: 15px;
                    background: #f5f5f5;
                    text-align: center;
                }}
                
                .candidate-image img {{
                    max-width: 100%;
                    height: auto;
                    max-height: 300px;
                    border-radius: 4px;
                }}
                
                .candidate-info {{
                    padding: 15px;
                }}
                
                .info-row {{
                    display: flex;
                    margin-bottom: 10px;
                    font-size: 14px;
                }}
                
                .info-row:last-child {{
                    margin-bottom: 0;
                }}
                
                .info-label {{
                    font-weight: 600;
                    color: #667eea;
                    width: 80px;
                    flex-shrink: 0;
                }}
                
                .info-value {{
                    color: #555;
                    flex: 1;
                    word-break: break-word;
                }}
                
                .candidate-actions {{
                    padding: 15px;
                    border-top: 1px solid #e0e0e0;
                    display: flex;
                    gap: 10px;
                }}
                
                .btn-select {{
                    flex: 1;
                    padding: 10px 16px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 600;
                    transition: background 0.3s ease;
                }}
                
                .btn-select:hover {{
                    background: #5568d3;
                }}
                
                .btn-bedetheque {{
                    flex: 1;
                    padding: 10px 16px;
                    background: #f0f0f0;
                    color: #333;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    text-decoration: none;
                    text-align: center;
                    font-size: 14px;
                    font-weight: 600;
                    transition: all 0.3s ease;
                }}
                
                .btn-bedetheque:hover {{
                    background: #e0e0e0;
                    border-color: #999;
                }}
                
                .footer {{
                    background: #f9f9f9;
                    padding: 20px;
                    text-align: center;
                    color: #777;
                    font-size: 14px;
                }}
                
                .selected-info {{
                    background: #e8f5e9;
                    color: #2e7d32;
                    padding: 15px;
                    border-radius: 4px;
                    margin-bottom: 20px;
                    display: none;
                }}
                
                .selected-info.visible {{
                    display: block;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 Album Disambiguation Challenge</h1>
                    <p>File: <strong>{filename}</strong></p>
                </div>
                
                <div class="content">
                    <div class="selected-info" id="selectedInfo">
                        ✓ Selected: <strong id="selectedTitle"></strong>
                    </div>
                    
                    <div class="local-section">
                        <h2>📖 Your Local Cover</h2>
                        <div class="local-cover">
                            <img src="{local_cover_b64}" alt="Local cover" />
                        </div>
                    </div>
                    
                    <div class="candidates-section">
                        <h2>🔍 Top Candidates from Bédéthèque</h2>
                        <div class="candidates-grid">
                            {candidates_html}
                        </div>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Select the correct album based on cover and metadata. Your selection will be saved.</p>
                </div>
            </div>
            
            <script>
                let selectedIdx = null;
                
                function selectCandidate(idx) {{
                    // Deselect previous
                    if (selectedIdx !== null) {{
                        document.querySelector(`[data-idx="${{selectedIdx}}"]`).classList.remove('selected');
                    }}
                    
                    // Select new
                    selectedIdx = idx;
                    const card = document.querySelector(`[data-idx="${{idx}}"]`);
                    card.classList.add('selected');
                    
                    // Show selection info
                    const title = card.querySelector('.info-row .info-value').textContent;
                    const info = document.getElementById('selectedInfo');
                    document.getElementById('selectedTitle').textContent = title;
                    info.classList.add('visible');
                    
                    // Send selection to Python via HTTP
                    fetch(`/select?idx=${{idx}}`)
                        .then(response => response.json())
                        .then(data => {{
                            if (data.status === 'ok') {{
                                console.log('Selection saved, you can close this window');
                                // Optional: close window after brief delay
                                setTimeout(() => window.close(), 1000);
                            }}
                        }})
                        .catch(err => console.error('Error sending selection:', err));
                    
                    // Auto-scroll to top
                    window.scrollTo({{ top: 0, behavior: 'smooth' }});
                }}
                
                // Keyboard shortcuts
                document.addEventListener('keydown', (e) => {{
                    const digit = parseInt(e.key);
                    if (digit >= 1 && digit <= 5) {{
                        selectCandidate(digit);
                    }}
                }});
            </script>
        </body>
        </html>
        """
        return html
    
    @staticmethod
    def get_score_color(score: float) -> str:
        """Get color for score badge based on score value."""
        if score >= 0.80:
            return "#4caf50"  # Green
        elif score >= 0.60:
            return "#ff9800"  # Orange
        elif score >= 0.40:
            return "#ff5722"  # Red-Orange
        else:
            return "#f44336"  # Red
    
    def show_challenge_interactive(
        self,
        local_cover_path: str,
        candidates: List[Tuple[Dict, float, str]],
        filename: str,
    ) -> Optional[int]:
        """
        Display challenge in browser and wait for user selection.
        Uses a simple HTTP server to communicate with the browser.
        
        Returns:
            Selected candidate index (0-based) or None if no selection
        """
        html_content = self.generate_html(local_cover_path, candidates, filename)
        
        # Store selection globally (will be set by browser via query param)
        selected = {'idx': None}
        
        # Create a simple HTTP request handler
        class ChallengeHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                parsed_path = urlparse(self.path)
                
                # Handle selection endpoint
                if parsed_path.path == '/select':
                    params = parse_qs(parsed_path.query)
                    if 'idx' in params:
                        try:
                            selected['idx'] = int(params['idx'][0]) - 1  # Convert to 0-based
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'status': 'ok'}).encode())
                            return
                        except (ValueError, IndexError):
                            pass
                
                # Handle HTML request
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_content.encode())
            
            def log_message(self, format, *args):
                # Suppress logging
                pass
        
        # Start temporary HTTP server
        port = self._find_free_port()
        handler = ChallengeHandler
        
        with socketserver.TCPServer(("", port), handler) as httpd:
            url = f"http://localhost:{port}/"
            self.logger.info(f"Challenge server running at {url}")
            
            try:
                webbrowser.open(url)
                
                # Wait for user selection or timeout
                import time
                start_time = time.time()
                timeout = 300  # 5 minutes
                
                while time.time() - start_time < timeout:
                    if selected['idx'] is not None:
                        self.logger.info(f"User selected candidate {selected['idx'] + 1}")
                        return selected['idx']
                    httpd.handle_request()  # Handle one request
                    time.sleep(0.1)
                
                self.logger.warning("Challenge timeout - no selection made")
                return None
                
            except KeyboardInterrupt:
                self.logger.info("Challenge cancelled by user")
                return None
    
    @staticmethod
    def _find_free_port() -> int:
        """Find a free port to use for the HTTP server."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
