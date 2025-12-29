# BDneX - Roadmap & Feature Planning

## Vision

Transformer BDneX en **gestionnaire de bibliothèque BD complet**, s'inspirant de l'architecture modulaire et extensible de [beets](https://beets.io/).

---

## Phase 1: Foundation (Janvier 2026) 🏗️

### 1.1 SQLite Database for State Tracking ⭐
**Priorité**: HAUTE

Maintenir un registre des BD traitées pour éviter les re-traitements.

```sql
CREATE TABLE processed_files (
    id INTEGER PRIMARY KEY,
    file_path TEXT UNIQUE,
    file_hash TEXT,           -- SHA256 pour détecter modifs
    processed_date TIMESTAMP,
    bdgest_url TEXT,
    title TEXT,
    score REAL,               -- Score de confiance
    status TEXT,              -- 'success', 'manual', 'skipped'
    metadata JSON,
    error_msg TEXT
);

CREATE TABLE albums (
    id INTEGER PRIMARY KEY,
    bdgest_id INTEGER UNIQUE,
    title TEXT,
    series TEXT,
    volume INTEGER,
    editor TEXT,
    year INTEGER,
    cover_url TEXT,
    cached_metadata JSON
);

CREATE TABLE processing_sessions (
    id INTEGER PRIMARY KEY,
    session_date TIMESTAMP,
    directory TEXT,
    num_files INTEGER,
    num_processed INTEGER,
    status TEXT,
    batch_log_path TEXT
);
```

**Bénéfices**:
- `--resume` : Continuer un batch interrompu
- `--skip-processed` : Éviter de retraiter les mêmes BD
- `--force` : Forcer le retraitement
- Historique complet
- Analyse: quels fichiers prennent le plus de temps

**API simple**:
```python
from bdnex.lib.database import BDneXDB

db = BDneXDB()
if db.is_processed(file_path, file_hash):
    logger.info("Already processed, skipping")
    continue

# Process file...

db.record_processed(file_path, result)
```

### 1.2 Resume Functionality
**Priorité**: HAUTE

```bash
# Reprendre une session interrompue
python -m bdnex -d "dossier/BD" --resume session_id

# Afficher les sessions en cours
python -m bdnex --list-sessions

# Voir l'état d'une session
python -m bdnex --session-info session_id

# Nettoyer une session complétée
python -m bdnex --cleanup-session session_id
```

**Implémentation**:
- Sauvegarder le session ID au début du batch
- Charger l'état de la session
- Continuer à partir du dernier fichier traité
- Mettre à jour le registre existant au lieu de créer un nouveau

---

## Phase 2: Configuration & Renaming (Février 2026) 🎨

### 2.1 Enhanced Configuration System

**Fichier**: `~/.config/bdnex/bdnex.yaml` (existant) + `bdnex.conf` (nouveau)

```yaml
# bdnex.yaml

# Logging
logging:
  level: info
  format: json  # ou console
  output_dir: ~/.local/share/bdnex/logs

# Database
database:
  backend: sqlite  # future: postgresql
  path: ~/.local/share/bdnex/bdnex.db

# Processing
processing:
  batch_workers: 4
  max_retries: 3
  challenge_threshold: 0.70
  
# Renaming convention
renaming:
  enabled: true
  pattern: "{series}/{volume:02d} - {title}"  # exemple
  backup_original: true
  dry_run: false  # Preview sans changer les fichiers

# Search strategies (priorité)
search:
  strategies:
    - bdgest    # Bédéthèque (défaut)
    - bdfuge    # Future: BDFuge
    - local_db  # Cache local
  timeout: 30

# Output formats
output:
  formats: [json, csv]
  include_covers: false
  compress: false
```

### 2.2 Renaming Convention

```bash
# Templates disponibles
{series}           # "Tintin"
{volume}           # "1"
{volume:02d}       # "01" (padded)
{title}            # "Le Sceptre d'Ottokar"
{editor}           # "Casterman"
{year}             # "1939"
{pages}            # "62"
{isbn}             # "ISBN-13"
{original_name}    # Garder original

# Exemples
Pattern: "{series}/{volume:02d} - {title}"
Result:  "Tintin/01 - Le Sceptre d'Ottokar"

Pattern: "{editor}/{series} - {volume:02d} ({year})"
Result:  "Casterman/Tintin - 01 (1939)"
```

**Commandes**:
```bash
# Preview renaming
python -m bdnex -d "dossier/BD" --dry-run

# Apply renaming (après ComicInfo insertion)
python -m bdnex -d "dossier/BD" --rename

# Custom pattern
python -m bdnex -d "dossier/BD" --rename --pattern "{editor}/{series}/{volume:02d}"
```

---

## Phase 3: Catalog Management (Mars 2026) 📚

### 3.1 Interactive Catalog Explorer

```bash
# Mode interactif
python -m bdnex --catalog

# Commandes interactives disponibles:
> list                  # Lister toutes les BD
> search "Tintin"       # Chercher
> info 1066             # Détails d'une BD
> edit 1066             # Éditer les métadonnées
> update-cover 1066     # Retélécharger la couverture
> stats                 # Statistiques
> export                # Exporter en CSV/JSON
> import file.csv       # Importer depuis CSV
```

### 3.2 Library Statistics

```bash
python -m bdnex --stats

# Output:
# Total: 2,450 BD
# Series: 890
# Editors: 245
# Years: 1950-2025
# Avg pages: 156
# Missing covers: 23
# Low confidence: 5
```

### 3.3 Duplicate Detection

```bash
# Détecter les doublons
python -m bdnex --find-duplicates

# Résultats:
# - Cover similarity > 95%
# - Title similarity > 90%
# - ISBN matching
```

---

## Phase 4: Plugin Architecture (Avril 2026) 🔌

S'inspirer de beets avec un système de plugins.

### 4.1 Plugin System

```
bdnex/plugins/
├── __init__.py
├── base.py              # BasePlugin class
├── bdgest_plugin.py     # Bédéthèque (built-in)
├── bdfuge_plugin.py     # BDFuge (future)
├── database_plugin.py   # Database (built-in)
├── cover_plugin.py      # Cover manager
└── user_plugins/        # User-defined
    ├── my_renamer.py
    ├── my_tagger.py
    └── ...
```

### 4.2 Plugin Interface

```python
class BDSearchPlugin(BasePlugin):
    """Base class for BD search plugins."""
    
    def __init__(self):
        super().__init__()
        self.priority = 100  # Higher = tried first
    
    def search(self, album_name: str, top_k: int = 5) -> List[Dict]:
        """Search for album candidates.
        
        Returns:
            [{'title': ..., 'url': ..., 'metadata': ...}, ...]
        """
        raise NotImplementedError
    
    def get_metadata(self, url: str) -> Dict:
        """Fetch full metadata from search result."""
        raise NotImplementedError
```

### 4.3 Built-in Plugins

**BdgestPlugin** (existant, refactorisé)
```python
class BdgestPlugin(BDSearchPlugin):
    def __init__(self):
        super().__init__()
        self.priority = 100  # Default
    
    def search(self, album_name: str, top_k: int = 5) -> List[Dict]:
        # Existing search_album_candidates_fast()
        ...
```

**BdfugePlugin** (future)
```python
class BdfugePlugin(BDSearchPlugin):
    def __init__(self):
        super().__init__()
        self.priority = 90   # Secondary search
    
    def search(self, album_name: str, top_k: int = 5) -> List[Dict]:
        # Search BDFuge API
        ...
```

**CoverPlugin**
```python
class CoverPlugin(BasePlugin):
    def compare_covers(self, local, remote) -> float:
        # SIFT comparison
        ...
    
    def find_covers(self, metadata) -> List[str]:
        # Multiple sources: Covers, Unixgnu, etc.
        ...
```

### 4.4 Plugin Configuration

```yaml
# ~/.config/bdnex/bdnex.yaml

plugins:
  enabled:
    - bdgest
    - bdfuge
    - cover
  
  # Plugin-specific settings
  bdgest:
    cache_ttl: 86400
    timeout: 30
  
  bdfuge:
    enabled: true
    priority: 90
    api_key: ${BDFUGE_API_KEY}
  
  cover:
    similarity_threshold: 0.60
    sources: [covers, unixgnu, bdfuge]
```

---

## Phase 5: Advanced Features (Mai-Juin 2026) 🚀

### 5.1 Multi-Source Search

Essayer plusieurs sources dans l'ordre de priorité.

```python
class MultiSourceSearcher:
    def search(self, album_name: str):
        """Try plugins in priority order."""
        for plugin in self.plugins_by_priority():
            candidates = plugin.search(album_name)
            if candidates:
                return candidates
        
        raise NoResultsError(f"No results for {album_name}")
```

### 5.2 Series Manager

Gérer les séries compètes.

```bash
python -m bdnex --series "Tintin"
# Output:
# Total: 24 BD
# Missing: 3 (ID: 123, 456, 789)
# Gaps: Volume 5 missing
# Duplicates: Volume 1 (2 copies)
```

### 5.3 Batch Import/Export

```bash
# Importer une liste de BD depuis un fichier
python -m bdnex --import collection.csv

# Exporter statistiques
python -m bdnex --export stats.json

# Sync avec un autre dossier
python -m bdnex --sync source_dir target_dir
```

### 5.4 Watch Mode

```bash
# Surveiller un dossier pour nouvelles BD
python -m bdnex --watch "dossier/BD" --mode batch

# Nouvelles BD ajoutées = traitement automatique
```

---

## Architecture Proposée (Inspirée de beets)

```
bdnex/
├── lib/
│   ├── core.py                    # Core BD handling
│   ├── database.py                # SQLite interface ⭐
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── base.py                # BasePlugin
│   │   ├── bdgest.py              # Refactored
│   │   ├── bdfuge.py              # Future
│   │   └── ...
│   ├── search/
│   │   ├── multi_source.py        # MultiSourceSearcher ⭐
│   │   └── strategies.py
│   ├── rename/
│   │   ├── conventions.py         # Pattern parsing ⭐
│   │   └── operations.py
│   └── ...
├── config/
│   ├── defaults.yaml
│   └── schema.json                # Config validation
├── commands/
│   ├── __init__.py
│   ├── process.py                 # Batch processing
│   ├── catalog.py                 # Interactive catalog
│   ├── rename.py                  # Renaming
│   └── stats.py                   # Statistics
└── ui/
    ├── cli.py                     # CLI interface
    ├── interactive.py             # Interactive mode ⭐
    └── challenge.py               # Existing
```

---

## Inspiration de beets 🎵 → 🎨

### Similarities to Implement
1. **Plugin system** ← Modules flexibles et extensibles
2. **Configuration flexibility** ← beets.yaml style
3. **Library database** ← Track everything
4. **Multiple sources** ← Search fallback hierarchy
5. **Customizable output** ← Templates
6. **Interactive mode** ← Browse/edit library
7. **Automation** ← Batch operations with logging

### Differences (BD vs Music)
- No "auto-tag" equivalent (BD have unique metadata)
- Cover is more important (visual medium)
- Volume/series relationships (albums have tracks)
- Manual search more common (ambiguous metadata)

---

## Timeline & Priorities

### 🔴 Must Have (Q1 2026)
- [x] Batch processing ✓ (done)
- [ ] SQLite database
- [ ] Resume functionality
- [ ] Basic catalog commands

### 🟡 Should Have (Q2 2026)
- [ ] Renaming conventions
- [ ] Plugin system
- [ ] Interactive catalog explorer
- [ ] BDFuge integration

### 🟢 Nice to Have (Q3-Q4 2026)
- [ ] Watch mode
- [ ] Series manager
- [ ] Import/export
- [ ] Statistics dashboard

### 💜 Ambitious (2027+)
- [ ] Web UI dashboard
- [ ] Mobile companion app
- [ ] Streaming integration
- [ ] AI-powered tagging

---

## Next Steps

1. **Immediate** (This week):
   - ✅ Finalize batch processing
   - Push to fork
   - Create GitHub issues for roadmap items

2. **Short-term** (Next 2-4 weeks):
   - Start Phase 1: Database + Resume
   - Design database schema with tests
   - Implement resume workflow

3. **Medium-term** (January-February):
   - Phase 2: Renaming system
   - Configuration validation
   - CLI improvements

---

## Questions for you 🤔

1. **Database backend**:
   - SQLite (simple, local) ← Recommended
   - PostgreSQL (advanced, client-server)
   - Other?

2. **Renaming strategy**:
   - Apply automatically after metadata insertion?
   - Require explicit `--rename` command?
   - Dry-run by default?

3. **Plugin priorities**:
   - BDFuge API integration (cost?)
   - Other sources (which ones)?
   - User custom scripts?

4. **Interactive mode**:
   - TUI (Terminal UI) with curses/rich?
   - Web dashboard?
   - CLI prompts?

---

## Contributing

This roadmap is open to suggestions! Areas for contribution:
- Database schema design
- Plugin system architecture
- Configuration validation
- BDFuge integration research
- Testing framework

Feel free to open issues or PRs against the roadmap!
