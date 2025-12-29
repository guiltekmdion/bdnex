# Contributing to BDneX

Merci de votre intérêt pour contribuer à BDneX ! Ce guide vous aidera à commencer.

## 🎯 Code of Conduct

- Soyez respectueux
- Écoutez les feedback
- Proposez des améliorations constructives

## 🚀 Getting Started

### 1. Setup Development Environment

```bash
# Clone votre fork
git clone https://github.com/YOUR_USERNAME/bdnex.git
cd bdnex

# Créer une branche feature
git checkout -b feature/ma-feature

# Installer en mode développement
pip install -e ".[dev]"

# Installer les dépendances de test
pip install pytest pytest-cov black flake8 mypy
```

### 2. Structure du Code

```
bdnex/
├── lib/                 # Core logic
│   ├── database.py      # Database operations
│   ├── bdgest.py        # Bédéthèque API
│   ├── cover.py         # Cover comparison
│   ├── batch_*.py       # Batch processing
│   └── ...
├── ui/                  # User interface
│   ├── __init__.py      # Main entry point
│   ├── challenge.py     # Interactive challenge UI
│   └── ...
├── conf/                # Configuration files
│   ├── bdnex.yaml       # Default config
│   ├── schema.sql       # Database schema
│   └── ...
└── plugins/             # Plugin system (future)
```

### 3. Code Style

Nous utilisons:
- **Black** pour le formatage (max 100 chars)
- **Flake8** pour le linting
- **MyPy** pour le type checking

```bash
# Format code
black bdnex/ test/

# Check style
flake8 bdnex/ test/

# Type checking
mypy bdnex/
```

### 4. Testing

```bash
# Run all tests
pytest test/

# Run with coverage
pytest --cov=bdnex test/

# Run specific test
pytest test/test_batch_processing.py::test_imports
```

**Règle**: Tout nouveau code doit avoir des tests. Visez 80%+ de coverage.

## 📝 Making Changes

### Good Commit Messages

```
feat: add database backend for tracking processed files

- Implement BDneXDB class with SQLite support
- Add SessionManager for resume functionality
- Include migration script for existing batch logs

Closes #123
```

Format:
```
<type>: <short description>

<longer description if needed>

Closes #issue_number
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Request Process

1. **Fork** le repo si ce n'est pas fait
2. **Créer** une branche feature: `git checkout -b feature/ma-feature`
3. **Commit** avec messages clairs
4. **Test** avec `pytest`
5. **Push** vers votre fork
6. **Créer** une Pull Request avec description détaillée

## 🔧 Working on Specific Areas

### Adding a New Plugin

1. Créer `bdnex/plugins/my_plugin.py`
2. Hériter de `BasePlugin`
3. Implémenter les méthodes requises
4. Ajouter des tests
5. Documenter dans `ROADMAP.md`

Exemple:
```python
from bdnex.lib.plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.priority = 100
    
    def initialize(self):
        """Called when plugin is loaded."""
        pass
    
    def shutdown(self):
        """Called when plugin is unloaded."""
        pass
```

### Modifying Database Schema

**⚠️ Important**: Never modify existing schema directly!

Au lieu de cela:
1. Créer un script de migration: `bdnex/migrations/001_add_feature.sql`
2. Enregistrer dans `MIGRATIONS` list
3. Implémenter la migration automatique au démarrage
4. Tester avec une base de données existante

### Adding Configuration Options

1. Ajouter à `SCHEMA` dans `bdnex/conf/schema.json`
2. Ajouter les defaults à `bdnex/conf/bdnex.yaml`
3. Documenter dans `BATCH_PROCESSING.md` ou `ROADMAP.md`
4. Tester la validation: `bdnex_config()`

### UI Changes

Pour les modifications d'interface:
1. Tester dans les deux modes: batch et interactif
2. Supporter le mode non-interactif (pas de prompts)
3. Ajouter des options CLI si nécessaire
4. Documenter les nouveaux flags

## 🐛 Bug Reporting

Trouver un bug? Merci de reporter!

**Avant de reporter**:
1. Vérifier si c'est pas déjà reporté
2. Vérifier la dernière version du code
3. Reproduire avec `--verbose` ou `--debug`

**Format du bug report**:
```markdown
### Description
[Courte description du bug]

### Steps to Reproduce
1. ...
2. ...

### Expected Behavior
[Ce qui devrait se passer]

### Actual Behavior
[Ce qui se passe réellement]

### Environment
- OS: [Windows/Linux/Mac]
- Python: 3.10.x
- BDneX version: commit hash or tag
```

## ⭐ Feature Requests

Vous avez une idée ? Excellent!

**Vérifier d'abord**:
- [ ] Pas déjà dans `ROADMAP.md`
- [ ] Pas déjà dans les issues GitHub

**Format de la request**:
```markdown
### Feature Description
[Description de la feature]

### Use Case
[Pourquoi avez-vous besoin de cette feature ?]

### Proposed Solution
[Optional: votre idée pour implémenter]

### Related Issues
[Lier aux issues connexes]
```

## 📚 Documentation

Documentation est très importante!

### Ajouter une page de documentation

1. Créer `.md` file dans le root
2. Inclure exemple d'utilisation
3. Ajouter des sections claires
4. Linker depuis `README.md`

### Documenter le code

```python
def process_files_parallel(
    self,
    file_list: List[str],
    interactive: bool = False,
) -> List[Dict[str, Any]]:
    """
    Process multiple BD files in parallel.
    
    Uses multiprocessing.Pool with configurable number of workers
    for distributed processing across CPU cores.
    
    Args:
        file_list: List of file paths to process
        interactive: Enable interactive challenge UI for ambiguous matches
    
    Returns:
        List of result dicts with 'filename', 'success', 'score', etc.
    
    Raises:
        KeyboardInterrupt: If user cancels during processing
        ValueError: If file_list is empty
    
    Example:
        >>> processor = AdvancedBatchProcessor(num_workers=4)
        >>> results = processor.process_files_parallel(files)
        >>> processor.print_summary(results)
    """
```

## 🎓 Learning Resources

### Architecture
- Lire `ARCHITECTURE_PHASE1.md` pour Phase 1
- Comprendre le flow: CLI → UI → Lib → API

### Code Inspection
```bash
# Voir la structure du projet
tree bdnex/ -I '__pycache__|*.pyc'

# Analyser les dépendances
grep -r "^from bdnex" bdnex/ | cut -d: -f2 | sort -u

# Trouver les TODOs/FIXMEs
grep -r "TODO\|FIXME" bdnex/
```

### Debugging

```python
# Utiliser le logger
import logging
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")

# Ou utiliser pdb
import pdb; pdb.set_trace()
```

## 🚢 Release Process

**Nous utilisons**: Semantic Versioning (MAJOR.MINOR.PATCH)

1. Mettre à jour version dans `setup.py`
2. Créer changelog
3. Tag: `git tag v1.2.3`
4. Push tag: `git push origin v1.2.3`
5. Build et publish (CI/CD automatique)

## 💬 Getting Help

### Questions?
- Ouvrir une GitHub discussion
- Regarder les issues existantes
- Vérifier la documentation

### Feedback?
- Créer une issue avec label `feedback`
- Proposer un changement avec une PR

## 🎉 Thank You!

Merci pour votre contribution! C'est grâce à des gens comme vous que BDneX peut s'améliorer.

---

## Quick Reference

```bash
# Setup
git clone https://github.com/YOUR_USERNAME/bdnex.git
cd bdnex
pip install -e ".[dev]"

# Feature branch
git checkout -b feature/description

# Make changes and test
black bdnex/
flake8 bdnex/
pytest test/

# Commit
git commit -m "feat: clear description"

# Push and PR
git push origin feature/description
# Create PR on GitHub
```

---

## Maintainers

- [@lbesnard](https://github.com/lbesnard) - Creator
- [@guiltekmdion](https://github.com/guiltekmdion) - Primary contributor

## License

BDneX is licensed under the MIT License.
