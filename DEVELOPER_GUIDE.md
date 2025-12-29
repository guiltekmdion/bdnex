# BDneX Developer Guide

Guide technique pour les développeurs travaillant sur BDneX. Ce document couvre l'architecture, les patterns utilisés, et les conventions du code.

---

## 📐 Architecture Overview

### Application Flow

```
CLI Input (utils.py)
    ↓
Main Entry (ui/__init__.py)
    ├─→ [--batch] AdvancedBatchProcessor
    │           ↓
    │       BatchWorker × N (parallel)
    │           ↓
    │       BdGestParse (cache-aware)
    │           ↓
    │       DatabaseOps (future)
    │           ↓
    │       Challenge UI (batch mode)
    │
    ├─→ [--strict] Direct search
    │
    └─→ [interactive] ChallengeUI
            ↓
        User interaction
```

### Module Responsibilities

| Module | Responsibility | Key Classes |
|--------|---|---|
| `utils.py` | CLI argument parsing, config loading | `bdnex_config()` |
| `bdgest.py` | Bédéthèque API access, album search | `BdGestParse`, `SitemapCache` |
| `cover.py` | Cover image downloading and comparison | `CoverRoulette` |
| `archive_tools.py` | RAR/ZIP extraction and metadata | `archive_reader()` |
| `batch_config.py` | Batch processing configuration | `BatchConfig`, `SitemapCache` |
| `batch_worker.py` | Single file processing worker | `process_single_file()` |
| `advanced_batch_processor.py` | Parallel orchestration | `AdvancedBatchProcessor` |
| `challenge.py` | Interactive disambiguation UI | `ChallengeUI` |
| `database.py` | Database operations (Phase 1) | `BDneXDB`, `SessionManager` |

---

## 🔑 Key Design Patterns

### 1. Singleton Caching

**Pattern**: Global singleton instances for expensive operations

```python
# bdnex/lib/batch_config.py
_SITEMAP_CACHE = None

def get_sitemap_cache():
    global _SITEMAP_CACHE
    if _SITEMAP_CACHE is None:
        _SITEMAP_CACHE = SitemapCache()
    return _SITEMAP_CACHE

# Usage
cache = get_sitemap_cache()
```

**Why**: Avoids recomputing expensive resources (sitemaps) across multiple function calls/processes.

**When to use**: Cache-aware objects, expensive I/O operations, shared resources.

### 2. Mode-Based Branching

**Pattern**: Application behavior determined by flags, not parameter sprawl

```python
# bdnex/ui/__init__.py
if vargs.batch:
    processor = AdvancedBatchProcessor(...)
    results = processor.process_files_parallel(files)
    # Challenge UI called at end, not during processing
elif vargs.strict:
    # Direct search, fallback to challenge if needed
else:
    # Interactive mode, challenge per file
```

**Why**: Cleaner than many optional parameters, easier to reason about.

**When to use**: Different execution flows, CLI-driven features, test modes.

### 3. Worker Functions for Multiprocessing

**Pattern**: Isolated function for parallel pool workers

```python
# bdnex/lib/batch_worker.py
def process_single_file(file_path, max_retries=3):
    """Must be picklable and importable at module level."""
    # No class methods, no closures
    # Returns simple types (dict, tuple)
```

**Why**: Functions are picklable, avoiding serialization issues with class methods.

**Rules**:
- Must be at module level (not nested)
- All imports inside function or at top of module
- Return simple types (dict, list, tuple, str)
- No exception re-raising across process boundary

### 4. Configuration Management

**Pattern**: Centralized YAML config with env var overrides

```python
# bdnex/lib/utils.py
config = bdnex_config()  # Loaded once, cached

# Override via environment
os.environ['BDNEX_NUM_WORKERS'] = '8'
config = bdnex_config(force_reload=True)
```

**Config files**:
- `bdnex/conf/bdnex.yaml` - Default config
- `~/.bdnex/config.yaml` - User overrides
- `BDNEX_*` env vars - Runtime overrides

### 5. Logging for Debugging

**Pattern**: Structured logging with JSON serialization

```python
# bdnex/lib/batch_config.py - BatchLogger
logger = BatchLogger('batch_session_1')
logger.record_file_processing(
    filename='bd.cbz',
    success=True,
    score=95,
    source='bdgest'
)
logger.save_json()  # batch_results/batch_session_1.json
```

**When to use**: Track decisions, performance metrics, user debugging.

---

## 🧪 Testing Strategy

### Test Levels

```
Unit Tests (test_*.py)
├── Test individual functions
├── Mock external APIs
└── ~80% coverage target

Integration Tests
├── Test module interactions
├── Use fixture files (test/bd.cbr, test/bd.cbz)
└── Verify real behavior

End-to-End Tests
├── Test full workflows
├── Run with actual CLI
└── Validate output formats
```

### Test Files and Coverage

```
test/
├── test_archive_tools.py      # Archive extraction
├── test_bdgest.py             # API parsing
├── test_cover.py              # Cover operations
├── test_utils.py              # Configuration
├── test_batch_processing.py    # Batch components
├── test_database.py           # Database ops (Phase 1)
└── fixtures/
    ├── bd.cbz                 # Real comic archive
    ├── sample_bdgest.html     # Sample API response
    └── invalid_archive.zip    # Error cases
```

### Running Tests

```bash
# All tests
pytest test/

# With coverage report
pytest --cov=bdnex --cov-report=html test/

# Specific test file
pytest test/test_batch_processing.py

# Specific test function
pytest test/test_batch_processing.py::test_imports -v

# Stop on first failure
pytest -x test/

# Show print statements
pytest -s test/
```

---

## 🔄 Development Workflows

### Adding a New Feature

**Step 1**: Create feature branch
```bash
git checkout -b feature/my-feature
```

**Step 2**: Write failing test (TDD approach)
```python
# test/test_my_feature.py
def test_my_feature():
    result = my_feature_function(input_data)
    assert result == expected_value
```

**Step 3**: Implement feature
```python
# bdnex/lib/my_module.py
def my_feature_function(input_data):
    return process(input_data)
```

**Step 4**: Test
```bash
pytest test/test_my_feature.py -v
```

**Step 5**: Format and lint
```bash
black bdnex/
flake8 bdnex/
mypy bdnex/
```

**Step 6**: Commit with good message
```bash
git commit -m "feat: implement my feature

- Added my_feature_function to process data
- Added comprehensive test coverage
- Updated documentation
"
```

### Debugging a Bug

**Step 1**: Reproduce with minimal test
```python
def test_bug_reproduction():
    # Minimal code that triggers the bug
    result = buggy_function()
    assert False, f"Got: {result}"
```

**Step 2**: Add debug output
```bash
# Run with verbose logging
bdnex --verbose --input file.cbz
```

**Step 3**: Use debugger
```python
import pdb; pdb.set_trace()  # In code
```

**Step 4**: Fix bug
```python
# Fix the root cause
def buggy_function():
    return fixed_implementation()
```

**Step 5**: Verify fix
```bash
pytest test/test_bug.py -v
```

### Performance Profiling

```python
# bdnex/lib/profiling.py
import cProfile
import pstats
import io

def profile_batch_processing():
    pr = cProfile.Profile()
    pr.enable()
    
    # Code to profile
    processor = AdvancedBatchProcessor()
    processor.process_files_parallel(files)
    
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    print(s.getvalue())
```

---

## 💾 Database Integration (Phase 1)

### Schema Overview

```sql
-- Processed files tracking
CREATE TABLE processed_files (
    id INTEGER PRIMARY KEY,
    file_hash TEXT UNIQUE,
    file_path TEXT,
    processed_at TIMESTAMP,
    session_id INTEGER FOREIGN KEY
);

-- BDGest album matches
CREATE TABLE bdgest_albums (
    id INTEGER PRIMARY KEY,
    file_hash TEXT UNIQUE,
    album_id INTEGER,
    album_title TEXT,
    match_score INTEGER,
    matched_at TIMESTAMP
);
```

### Usage Example

```python
from bdnex.lib.database import BDneXDB

db = BDneXDB()

# Check if file already processed
if db.is_processed('bd.cbz'):
    print("Already processed!")
else:
    # Process file
    result = process_file('bd.cbz')
    db.record_processing(
        file_path='bd.cbz',
        album_id=12345,
        match_score=95
    )

# List processing sessions
for session in db.get_sessions():
    print(f"Session {session.id}: {session.file_count} files")
```

### Integration Points

```python
# bdnex/lib/advanced_batch_processor.py
class AdvancedBatchProcessor:
    def __init__(self, ...):
        self.db = BDneXDB()
        self.session = self.db.start_session()
    
    def process_files_parallel(self, file_list):
        # Skip already processed
        todo = [f for f in file_list if not self.db.is_processed(f)]
        
        # Process
        results = self.pool.imap_unordered(...)
        
        # Record in database
        for result in results:
            self.db.record_processing(...)
        
        self.db.commit_session(self.session)
```

---

## 🔌 Plugin System (Phase 4)

### Plugin Architecture

```python
# bdnex/lib/plugins/base.py
class BasePlugin:
    def __init__(self):
        self.priority = 100  # Lower = earlier
        self.config = {}
    
    def initialize(self):
        """Called when plugin is loaded."""
        pass
    
    def shutdown(self):
        """Called when plugin is unloaded."""
        pass

# Example plugin
class MyPlugin(BasePlugin):
    def initialize(self):
        # Register handlers, load resources, etc
        pass
```

### Plugin Hooks

```
Phase 1: on_file_detected(file_path)
Phase 2: on_search_start(album_title)
Phase 3: on_match_found(album_data)
Phase 4: on_cover_downloaded(cover_path)
Phase 5: on_metadata_saved(metadata)
```

---

## 📊 Code Quality Standards

### Coverage Targets

```
Target: 80%+ coverage
Lines:  85%+
Branches: 75%+
```

### Code Metrics

```bash
# Check complexity
radon cc bdnex/ -a -s

# Show maintainability index
radon mi bdnex/ -s
```

### Performance Benchmarks

```
Batch processing 100 BD files:
- Without cache: 16-32 minutes
- With cache: 5-10 minutes (4x speedup)
- Parallel (4 workers): ~2.5 minutes

Sitemap parsing:
- First run: 5-10 seconds
- With cache: <1 second
```

---

## 🚀 Performance Optimization Tips

### 1. Cache HTTP Requests

```python
# Good
cache = get_sitemap_cache()
if not cache.is_valid():
    sitemaps = fetch_from_bdgest()
    cache.save(sitemaps)
else:
    sitemaps = cache.load()

# Bad
for i in range(100):
    sitemaps = fetch_from_bdgest()  # Network call × 100!
```

### 2. Use Generators for Large Data

```python
# Good
def process_large_file():
    with open('huge.txt') as f:
        for line in f:  # Generators don't load all in memory
            yield process_line(line)

# Bad
def process_large_file():
    with open('huge.txt') as f:
        lines = f.readlines()  # Loads entire file in memory
        return [process_line(line) for line in lines]
```

### 3. Multiprocessing for CPU-Bound Work

```python
# Good - for cover image processing
from multiprocessing import Pool
with Pool(4) as pool:
    results = pool.map(resize_cover, covers)

# Bad - sequential processing
results = [resize_cover(c) for c in covers]  # Takes 4x longer
```

### 4. Lazy Loading

```python
# Good - only load if needed
class CoverComparison:
    @property
    def reference_image(self):
        if self._ref_image is None:
            self._ref_image = load_image(self.reference_path)
        return self._ref_image

# Bad - always load
class CoverComparison:
    def __init__(self, ...):
        self.reference_image = load_image(reference_path)
```

---

## 🐛 Common Pitfalls

### 1. Circular Imports

```python
# Bad
# bdnex/lib/module_a.py
from bdnex.lib.module_b import ClassB

# bdnex/lib/module_b.py
from bdnex.lib.module_a import ClassA  # Circular!

# Good - use type hints with string literals
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bdnex.lib.module_a import ClassA
```

### 2. Modifying Shared State in Threads

```python
# Bad
results = []
def worker():
    result = compute()
    results.append(result)  # Race condition!

# Good - use thread-safe Queue
from queue import Queue
results = Queue()
def worker():
    result = compute()
    results.put(result)
```

### 3. Not Handling Exceptions in Workers

```python
# Bad
def worker(item):
    return dangerous_operation(item)  # Exception kills worker silently

# Good
def worker(item):
    try:
        return dangerous_operation(item)
    except Exception as e:
        logger.error(f"Error processing {item}: {e}")
        return {'error': str(e), 'item': item}
```

### 4. Forgetting to Close Resources

```python
# Bad
def process():
    file = open('data.txt')
    return process_file(file)  # File never closed!

# Good
def process():
    with open('data.txt') as file:
        return process_file(file)  # Auto-closed
```

---

## 📚 Resources

### Internal Documentation
- `README.md` - Project overview
- `ROADMAP.md` - Future features
- `ARCHITECTURE_PHASE1.md` - Database design
- `BATCH_PROCESSING.md` - Batch mode guide
- `IMPLEMENTATION_SUMMARY.md` - Technical changes

### External Resources
- [beets - Music tagger](https://github.com/beetbox/beets) - Inspiration for plugin system
- [Python multiprocessing](https://docs.python.org/3/library/multiprocessing.html) - Parallel processing
- [SQLite documentation](https://www.sqlite.org/docs.html) - Database reference
- [pytest documentation](https://docs.pytest.org/) - Testing framework

---

## 📞 Getting Help

### Debug Checklist

- [ ] Reproduced with minimal test case?
- [ ] Checked recent commits for related changes?
- [ ] Searched existing issues?
- [ ] Read relevant documentation section?
- [ ] Added logging/debug output?
- [ ] Checked environment (Python version, dependencies)?

### Common Commands

```bash
# Update dependencies
pip install -r requirements.txt

# Validate syntax
python -m py_compile bdnex/**/*.py

# Run quick tests
pytest test/ -x -v

# Generate coverage report
pytest --cov=bdnex --cov-report=html test/

# Check code style
black --check bdnex/
flake8 bdnex/
```

---

**Last Updated**: 2024
**Maintainers**: [@lbesnard](https://github.com/lbesnard), [@guiltekmdion](https://github.com/guiltekmdion)
