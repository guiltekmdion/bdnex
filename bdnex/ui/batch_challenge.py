"""
Batch challenge UI - displays all low-confidence files for bulk review and correction.
"""
import os
import webbrowser
import base64
import logging
import http.server
import socketserver
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs


class BatchChallengeUI:
    """Interactive UI for reviewing and fixing multiple low-confidence matches at once."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def image_to_base64(image_path: str) -> str:
        """Convert image file to base64 data URL."""
        try:
            with open(image_path, 'rb') as img_file:
                data = base64.b64encode(img_file.read()).decode()
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
            logging.getLogger(__name__).error(f"Erreur de conversion d'image: {e}")
            return ""
    
    def generate_html(
        self,
        low_confidence_results: List[Dict],
    ) -> str:
        """
        Generate HTML for batch challenge UI.
        
        Args:
            low_confidence_results: List of dicts with 'filename', 'score', 'candidates', 'cover_path'
        
        Returns:
            HTML content as string
        """
        files_html = ""
        
        for idx, result in enumerate(low_confidence_results, 1):
            filename = result.get('filename', f'Fichier {idx}')
            score = result.get('score', 0)
            cover_path = result.get('cover_path')
            candidates = result.get('candidates', [])
            
            cover_b64 = self.image_to_base64(cover_path) if cover_path else ""
            score_percent = int(score * 100)
            score_color = self._get_score_color(score)
            
            # Build candidates dropdown for this file
            candidates_options = '<option value="">-- Chercher manuellement --</option>'
            for c_idx, (metadata, c_score, c_path) in enumerate(candidates):
                title = metadata.get('title', 'Unknown')
                c_score_percent = int(c_score * 100)
                candidates_options += f'<option value="{idx}-{c_idx}">{title} ({c_score_percent}%)</option>'
            
            files_html += f"""
            <div class="file-card" id="file-{idx}">
                <div class="file-header">
                    <div class="file-info">
                        <h3>📄 {filename}</h3>
                        <p class="file-score">Score: 
                            <span class="score-badge" style="background-color: {score_color};">
                                {score_percent}%
                            </span>
                        </p>
                    </div>
                    <div class="file-cover" style="width: 100px; height: 150px; overflow: hidden; border-radius: 4px;">
                        <img src="{cover_b64}" alt="Couverture" style="width: 100%; height: 100%; object-fit: cover;">
                    </div>
                </div>
                
                <div class="file-action">
                    <label for="select-{idx}">Sélectionner le bon album:</label>
                    <select id="select-{idx}" class="file-select" data-file-idx="{idx}">
                        {candidates_options}
                    </select>
                    <button class="btn-apply" onclick="applySelection({idx})">Appliquer</button>
                </div>
            </div>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Révision par Lot - BDneX</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
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
                    padding: 30px;
                    max-height: 80vh;
                    overflow-y: auto;
                }}
                
                .instructions {{
                    background: #e8f5e9;
                    border-left: 4px solid #4caf50;
                    padding: 15px;
                    margin-bottom: 30px;
                    border-radius: 4px;
                }}
                
                .instructions h3 {{
                    color: #2e7d32;
                    margin-bottom: 10px;
                }}
                
                .instructions ul {{
                    margin-left: 20px;
                    color: #555;
                }}
                
                .files-grid {{
                    display: grid;
                    gap: 20px;
                }}
                
                .file-card {{
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 20px;
                    background: #f9f9f9;
                    transition: all 0.3s ease;
                }}
                
                .file-card:hover {{
                    border-color: #667eea;
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
                }}
                
                .file-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 15px;
                    gap: 20px;
                }}
                
                .file-info h3 {{
                    color: #333;
                    margin-bottom: 5px;
                    word-break: break-word;
                }}
                
                .file-score {{
                    font-size: 14px;
                    color: #666;
                }}
                
                .score-badge {{
                    display: inline-block;
                    padding: 6px 12px;
                    border-radius: 20px;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                    margin-left: 10px;
                }}
                
                .file-action {{
                    display: flex;
                    gap: 10px;
                    align-items: center;
                }}
                
                .file-action label {{
                    font-weight: 600;
                    color: #333;
                    white-space: nowrap;
                }}
                
                .file-select {{
                    flex: 1;
                    padding: 8px 12px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    font-size: 14px;
                }}
                
                .file-select:focus {{
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }}
                
                .btn-apply {{
                    padding: 8px 16px;
                    background: #4caf50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 600;
                    white-space: nowrap;
                    transition: background 0.3s ease;
                }}
                
                .btn-apply:hover {{
                    background: #388e3c;
                }}
                
                .footer {{
                    background: #f9f9f9;
                    padding: 20px;
                    text-align: center;
                    border-top: 1px solid #e0e0e0;
                    color: #777;
                }}
                
                .footer-buttons {{
                    display: flex;
                    gap: 10px;
                    justify-content: center;
                    margin-top: 15px;
                }}
                
                .btn-finish {{
                    padding: 12px 24px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 600;
                    font-size: 16px;
                    transition: background 0.3s ease;
                }}
                
                .btn-finish:hover {{
                    background: #5568d3;
                }}
                
                .btn-ignore {{
                    padding: 12px 24px;
                    background: #f44336;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 600;
                    font-size: 16px;
                    transition: background 0.3s ease;
                }}
                
                .btn-ignore:hover {{
                    background: #d32f2f;
                }}
                
                .status-message {{
                    display: none;
                    padding: 15px;
                    margin-bottom: 20px;
                    border-radius: 4px;
                    text-align: center;
                    font-weight: 600;
                }}
                
                .status-message.visible {{
                    display: block;
                }}
                
                .status-message.success {{
                    background: #e8f5e9;
                    color: #2e7d32;
                    border: 1px solid #c8e6c9;
                }}
                
                .status-message.error {{
                    background: #ffebee;
                    color: #c62828;
                    border: 1px solid #ffcdd2;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Révision par Lot</h1>
                    <p>Corrigez les fichiers avec faible confiance</p>
                </div>
                
                <div class="content">
                    <div class="instructions">
                        <h3>ℹ️ Instructions</h3>
                        <ul>
                            <li>Pour chaque fichier, sélectionnez le bon album dans la liste déroulante</li>
                            <li>Cliquez "Appliquer" pour confirmer la sélection</li>
                            <li>Laissez vide pour ignorer le fichier</li>
                            <li>Cliquez "Terminer" en bas quand vous avez fini</li>
                        </ul>
                    </div>
                    
                    <div id="statusMessage" class="status-message"></div>
                    
                    <div class="files-grid">
                        {files_html}
                    </div>
                </div>
                
                <div class="footer">
                    <div class="footer-buttons">
                        <button class="btn-finish" onclick="finishBatch()">Terminer</button>
                        <button class="btn-ignore" onclick="ignoreBatch()">Ignorer Tous</button>
                    </div>
                </div>
            </div>
            
            <script>
                let selections = {{}};
                
                function applySelection(fileIdx) {{
                    const select = document.getElementById(`select-${{fileIdx}}`);
                    const value = select.value;
                    
                    if (value) {{
                        selections[fileIdx] = value;
                        showStatus(`Sélection enregistrée pour le fichier ${{fileIdx}}`, 'success');
                    }} else {{
                        delete selections[fileIdx];
                        showStatus(`Fichier ${{fileIdx}} ignor\u00e9`, 'error');
                    }}
                }}
                
                function showStatus(message, type) {{
                    const statusDiv = document.getElementById('statusMessage');
                    statusDiv.textContent = message;
                    statusDiv.className = `status-message visible ${{type}}`;
                    setTimeout(() => statusDiv.classList.remove('visible'), 3000);
                }}
                
                function finishBatch() {{
                    fetch('/finish', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{selections: selections}})
                    }})
                    .then(r => r.json())
                    .then(d => {{
                        if (d.status === 'ok') {{
                            showStatus('Modifications enregistr\u00e9es', 'success');
                            setTimeout(() => window.close(), 1000);
                        }}
                    }});
                }}
                
                function ignoreBatch() {{
                    fetch('/finish', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{selections: {{}}}})
                    }})
                    .then(r => r.json())
                    .then(d => {{
                        if (d.status === 'ok') {{
                            setTimeout(() => window.close(), 500);
                        }}
                    }});
                }}
            </script>
        </body>
        </html>
        """
        return html
    
    @staticmethod
    def _get_score_color(score: float) -> str:
        """Get color for score badge."""
        if score >= 0.60:
            return "#ff9800"  # Orange
        else:
            return "#f44336"  # Red
    
    def show_batch_challenge(
        self,
        low_confidence_results: List[Dict],
    ) -> Dict[int, str]:
        """
        Show batch challenge UI in browser.
        
        Args:
            low_confidence_results: List of result dicts
        
        Returns:
            Dict mapping file index to selected candidate (e.g. {1: "1-0", 2: "2-1"})
        """
        if not low_confidence_results:
            return {}
        
        html_content = self.generate_html(low_confidence_results)
        
        # Store selections globally
        selections = {'done': False, 'data': {}}
        
        class BatchHandler(http.server.SimpleHTTPRequestHandler):
            def do_POST(self):
                if self.path == '/finish':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length)
                    data = json.loads(body.decode())
                    
                    selections['data'] = data.get('selections', {})
                    selections['done'] = True
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'ok'}).encode())
                    return
            
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
            
            def log_message(self, format, *args):
                pass
        
        port = self._find_free_port()
        
        try:
            with socketserver.TCPServer(("", port), BatchHandler) as httpd:
                # Prevent handle_request() from blocking forever when no request arrives.
                httpd.timeout = 0.5
                url = f"http://localhost:{port}/"
                self.logger.info(f"Ouverture de l'interface de révision par lot sur {url}")
                
                try:
                    webbrowser.open(url)
                except Exception as e:
                    self.logger.warning(f"Impossible d'ouvrir le navigateur: {e}")
                    return {}
                
                # Wait for user to finish (with timeout)
                import time
                start_time = time.time()
                timeout = 600  # 10 minutes
                
                while time.time() - start_time < timeout:
                    httpd.handle_request()
                    if selections.get('done'):
                        self.logger.info("Révision par lot terminée par l'utilisateur")
                        data = selections.get('data') or {}
                        if isinstance(data, dict):
                            return {int(k): v for k, v in data.items()}
                        return {}
                    time.sleep(0.1)
                
                self.logger.warning("Délai d'attente de révision par lot dépassé")
                return {}
        
        except Exception as e:
            self.logger.warning(f"Erreur dans l'interface de révision par lot: {e}")
            return {}
    
    @staticmethod
    def _find_free_port() -> int:
        """Find a free port for the HTTP server."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
