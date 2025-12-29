# BDneX

![BDneX](https://github.com/lbesnard/bdnex/actions/workflows/test.yml/badge.svg)
[![codecov](https://codecov.io/gh/lbesnard/bdnex/branch/main/graph/badge.svg?token=V9WJWRCTK5)](https://codecov.io/gh/lbesnard/bdnex)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**BDneX** is a French comics (BD) metadata tagger and library manager. It automatically retrieves metadata from [bedetheque.com](https://bedetheque.com) and embeds it into your comic files using the ComicRack standard format.

📖 [Version française](README_FR.md) | 🗺️ [Roadmap](ROADMAP.md)

## Table of Contents
- [Motivation](#motivation)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Testing](#testing)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Motivation

Contrary to music tagging, there is no agreed standard vocabulary for comics
tagging in general. However, the ComicRack standard is used by most library
managers such as [Komga](https://komga.org/).

While tools like [ComicTagger](https://github.com/comictagger/comictagger) exist for American comics (using the [Comic Vine](https://comicvine.gamespot.com) API), French comics (bandes dessinées) are largely underrepresented in these databases.

**BDneX fills this gap** by:
- Providing comprehensive metadata for French comics from bedetheque.com
- Using intelligent fuzzy matching to identify your comics
- Automatically embedding metadata in **CBZ** and **CBR** files
- Making it easy to organize large comic libraries by genre, author, rating, and more
- Enabling sharing of reading lists based on metadata rather than obscure filenames

Inspired by the excellent [beets](https://github.com/beetbox/beets) music manager.


## Features

### Current Features
- 🔍 **Smart Search**: Retrieves sitemaps from bedetheque.com for comprehensive album matching
- 🎯 **Fuzzy Matching**: Levenshtein distance algorithm for finding album names even with typos
- 🌐 **Web Scraping**: Parses webpage content with BeautifulSoup
- 📋 **ComicRack Format**: Converts parsed metadata to ComicInfo.xml (ComicRack standard)
- 🖼️ **Cover Verification**: Image comparison between online cover and archive cover for confidence scoring
- 💾 **Multiple Formats**: Supports both CBZ and CBR archive formats
- 🔄 **Batch Processing**: Process entire directories of comics at once
- ⚙️ **Configurable**: Customizable settings via YAML configuration file

### Supported Metadata
- Title, Series, Volume Number
- Writers, Pencillers, Colorists, Inkers
- Publisher, Publication Year
- Synopsis/Summary
- Genre and Tags
- Community Rating
- Page Count
- Language
- ISBN

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- (Optional) Conda for environment management

### Option 1: Using Conda (Recommended)

Create and activate a virtual environment:

```bash
# Create environment from the provided file
conda env create --file=environment.yml

# Activate the environment
conda activate bdnex
```

### Option 2: Using venv

```bash
# Create a virtual environment
python3 -m venv bdnex-env

# Activate it (Linux/Mac)
source bdnex-env/bin/activate

# Activate it (Windows)
bdnex-env\Scripts\activate
```

### Installation Modes

**User Installation** (for general use):
```bash
pip install .
```

**Development Installation** (for contributing):
```bash
pip install -e .[dev]
```

This installs additional development tools like `pytest` and `ipdb`.

### First-Time Setup

After installation, initialize BDneX to download bedetheque.com sitemaps:

```bash
bdnex --init
```

This downloads and caches sitemap data for faster comic matching (may take a few minutes on first run).

## Quick Start

Process a single comic file:
```bash
bdnex -f /path/to/comic.cbz
```

Process an entire directory:
```bash
bdnex -d /path/to/comics/folder
```

The tool will:
1. Extract the comic filename and attempt to match it with bedetheque.com entries
2. Download metadata and cover image
3. Compare covers to verify the match
4. Embed metadata as ComicInfo.xml inside the archive
5. Save the updated comic file

## Usage

### Command Line Options

```bash
bdnex [OPTIONS]
```

**Options:**
- `-f, --input-file <path>`: Process a single comic file
- `-d, --input-dir <path>`: Process all comics in a directory (recursively searches for .cbz and .cbr files)
- `-i, --init`: Initialize or force re-download of bedetheque.com sitemaps
- `-v, --verbose <level>`: Set logging verbosity (default: info)

### Examples

**Process a single file:**
```bash
bdnex -f "/comics/Asterix Tome 1 - Asterix le Gaulois.cbz"
```

**Process entire directory:**
```bash
bdnex -d /comics/collection
```

**Force sitemap update:**
```bash
bdnex --init
```

**Combine options:**
```bash
bdnex -d /comics/new-additions -v debug
```

### Example Output

When processing a comic, you'll see output like:

```
2024-12-29 15:30:00,123 - INFO     - bdnex.ui - Processing /comics/Nains Tome 1.cbz
2024-12-29 15:30:00,234 - INFO     - bdnex.lib.bdgest - Searching for "Nains Tome 1" in bedetheque.com sitemap files
2024-12-29 15:30:00,345 - DEBUG    - bdnex.lib.bdgest - Match album name succeeded
2024-12-29 15:30:00,456 - DEBUG    - bdnex.lib.bdgest - Levenshtein score: 87.5
2024-12-29 15:30:00,567 - DEBUG    - bdnex.lib.bdgest - Matched url: https://m.bedetheque.com/BD-Nains-Tome-1-Redwin-de-la-Forge-245127.html
2024-12-29 15:30:01,678 - INFO     - bdnex.lib.bdgest - Converting parsed metadata to ComicRack template
2024-12-29 15:30:01,789 - INFO     - bdnex.lib.cover - Checking Cover from input file with online cover
2024-12-29 15:30:02,890 - INFO     - bdnex.lib.cover - Cover matching percentage: 92.5
2024-12-29 15:30:02,901 - INFO     - bdnex.lib.comicrack - Add ComicInfo.xml to /comics/Nains Tome 1.cbz
2024-12-29 15:30:03,012 - INFO     - bdnex.ui - Processing album done
```

### Interactive Mode

If automatic matching fails or confidence is low, BDneX will prompt you:
- To manually enter a bedetheque.com URL
- To search interactively for the correct album
- To confirm whether to proceed with metadata embedding

## Configuration

BDneX uses a YAML configuration file located at:
- **Linux/Mac**: `~/.config/bdnex/bdnex.yaml`
- **Windows**: `%USERPROFILE%\.config\bdnex\bdnex.yaml`

The configuration file is created automatically on first run from the default template.

### Configuration Options

```yaml
bdnex:
  config_path: ~/.config/bdnex       # Configuration directory
  share_path: ~/.local/share/bdnex   # Data/cache directory

directory: /path/to/comics/library    # Default library directory

import:
  copy: no          # Copy files during import
  move: yes         # Move files during import
  replace: yes      # Replace existing files
  autotag: no       # Automatically tag without confirmation
  rename: yes       # Rename files based on metadata

library: ~/.local/share/bdnex/bdnex.sqlite  # Future feature: database

paths:
  # Naming conventions for organized libraries
  default: '%language/%type/%title (%author) [%year]/%title - %volume (%author) [%year]'
  oneshot: '%language/oneShots/%title (%author) [%year]/%title (%author) [%year]'
  series: '%language/series/%title (%author)/%title - %volume'

cover:
  match_percentage: 40  # Minimum cover similarity percentage for auto-confirmation
```

### Data Storage

BDneX stores cached data in `~/.local/share/bdnex/`:
- `bedetheque/sitemaps/`: Cached sitemap files
- `bedetheque/albums_html/`: Downloaded album pages
- `bedetheque/albums_json/`: Parsed metadata in JSON format
- `bedetheque/covers/`: Downloaded cover images

## Testing

### Running Tests

BDneX uses pytest for testing. To run the test suite:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test/test_utils.py

# Run specific test
pytest test/test_cover.py::TestCover::test_front_cover_similarity_good_match
```

### Test Coverage

Check code coverage:

```bash
# Install coverage tool (if not installed with dev dependencies)
pip install coverage

# Run tests with coverage
coverage run -m pytest

# View coverage report
coverage report

# Generate HTML coverage report
coverage html
# Open htmlcov/index.html in your browser
```

Current test coverage:
- **Overall**: ~74%
- `archive_tools.py`: 100%
- `cover.py`: 92%
- `bdgest.py`: 82%
- `utils.py`: 62%

### Test Structure

Tests are organized in the `test/` directory:
- `test_archive_tools.py`: Archive extraction and manipulation
- `test_bdgest.py`: BedeTheque scraping and metadata parsing
- `test_cover.py`: Cover image comparison and download
- `test_utils.py`: Utility functions (config, JSON, file operations)
- `test_comicrack.py`: ComicInfo.xml generation and embedding

## Architecture

### Project Structure

```
bdnex/
├── bdnex/                  # Main package
│   ├── conf/              # Configuration files and schemas
│   │   ├── ComicInfo.xsd  # ComicRack XML schema
│   │   ├── bdnex.yaml     # Default configuration
│   │   └── logging.conf   # Logging configuration
│   ├── lib/               # Core library modules
│   │   ├── archive_tools.py   # CBZ/CBR file handling
│   │   ├── bdgest.py          # BedeTheque scraper
│   │   ├── comicrack.py       # ComicInfo.xml generation
│   │   ├── cover.py           # Cover image operations
│   │   └── utils.py           # Utility functions
│   └── ui/                # User interface
│       └── __init__.py    # CLI implementation
├── test/                  # Test suite
├── README.md
├── setup.py
└── environment.yml

```

### Key Components

1. **bdgest.py**: 
   - Downloads and processes bedetheque.com sitemaps
   - Performs fuzzy string matching using Levenshtein distance
   - Scrapes and parses album metadata
   - Converts to ComicRack format

2. **cover.py**:
   - Downloads cover images from bedetheque.com
   - Uses SIFT feature detection for image comparison
   - Calculates similarity percentage

3. **comicrack.py**:
   - Generates ComicInfo.xml from metadata
   - Validates against ComicInfo.xsd schema
   - Embeds XML into comic archives
   - Handles existing ComicInfo.xml (with diff display)

4. **archive_tools.py**:
   - Extracts front covers from archives
   - Supports both ZIP (CBZ) and RAR (CBR) formats

### Workflow

```
Comic File → Extract Filename → Fuzzy Match → Scrape Metadata
                                     ↓
                            Download Cover Image
                                     ↓
                            Compare Covers (SIFT)
                                     ↓
                            Generate ComicInfo.xml
                                     ↓
                            Embed in Archive → Updated Comic File
```

## Contributing

Contributions are welcome! Here's how to get started:

### Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/yourusername/bdnex.git
cd bdnex
```

2. Install in development mode:
```bash
pip install -e .[dev]
```

3. Make your changes and add tests

4. Run the test suite:
```bash
pytest
```

5. Check code coverage:
```bash
coverage run -m pytest
coverage report
```

### Code Style

- Follow PEP 8 style guidelines
- Use descriptive variable and function names
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Add type hints where appropriate

### Adding Tests

When adding new features:
1. Create tests in the appropriate `test/test_*.py` file
2. Use `unittest.mock` for external dependencies
3. Aim for high code coverage (>80%)
4. Test edge cases and error conditions

### Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes with clear commit messages
3. Ensure all tests pass
4. Update documentation if needed
5. Submit a pull request with a clear description

## Roadmap

Planned features for future releases:

- [ ] **SQLite Database**: Keep records of already processed comics
- [ ] **Interactive Mode**: Enhanced CLI with selection menus
- [ ] **Catalog Manager**: Browse and manage your tagged collection
- [ ] **Renaming Convention**: Auto-rename files based on metadata and user config
- [ ] **Additional Sources**: Support for bdfugue.com and other French comic databases
- [ ] **Resume Support**: Pick up where you left off in batch processing
- [ ] **GUI Application**: Desktop application with visual interface
- [ ] **Plugin System**: Extensible architecture for custom metadata sources
- [ ] **Duplicate Detection**: Find and manage duplicate comics
- [ ] **Reading Lists**: Create and manage reading lists
- [ ] **Web Interface**: Browser-based management interface

Inspired by [beets music manager](https://github.com/beetbox/beets).

## Troubleshooting

### Common Issues

**Problem: "Cover matching percentage is low"**
- The automatic match may be incorrect
- You'll be prompted to manually enter the bedetheque.com URL
- You can adjust `cover.match_percentage` in config to be more/less strict

**Problem: "Album not found in sitemap"**
- Run `bdnex --init` to update sitemaps
- Try simplifying the filename (remove special characters, edition info)
- Use interactive mode to search manually

**Problem: "Import Error: No module named 'cv2'"**
- OpenCV is not installed correctly
- Run: `pip install opencv-contrib-python-headless`

**Problem: "RAR files not extracting"**
- Install unrar: `sudo apt-get install unrar` (Linux) or download from [rarlab.com](https://www.rarlab.com/)

**Problem: Tests failing with "No source for code: config-3.py"**
- This is a coverage tool artifact and can be ignored
- Tests should still pass successfully

### Debug Mode

Run with verbose debug output:
```bash
bdnex -d /comics -v debug
```

### Getting Help

- Check existing [GitHub Issues](https://github.com/lbesnard/bdnex/issues)
- Open a new issue with:
  - Your OS and Python version
  - Command you ran
  - Full error message
  - Example filename causing issues

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [bedetheque.com](https://bedetheque.com) for comprehensive French comics database
- [beets](https://github.com/beetbox/beets) for inspiration on music library management
- [ComicRack](http://comicrack.cyolito.com/) for the metadata standard
- All contributors who help improve BDneX

---

**Note**: BDneX is currently in active development. Some features mentioned in the roadmap are planned but not yet implemented. The tool is functional for its core purpose of tagging French comics.
