import argparse
import contextlib
import json
import logging
import logging.config
import os
import shutil
import sys
import tempfile
import urllib.request

import yaml
from importlib.resources import files

from bdnex.lib.colargulog import ColorizedArgsFormatter

LOGGING_CONF = str(files('bdnex.conf').joinpath('logging.conf'))
DEFAULT_CONFIG_YAML = str(files('bdnex.conf').joinpath('bdnex.yaml'))
UNIX_DIR_VAR = 'XDG_CONFIG_HOME'
UNIX_DIR_FALLBACK = '~/.config'


def dump_json(json_path, json_data):
    with open(json_path, "w") as outfile:
        json.dump(json_data, outfile, indent=4,
                  sort_keys=True, ensure_ascii=False)


def load_json(json_path):
    logger = logging.getLogger(__name__)

    if os.path.exists(json_path):
        logger.debug(f"Loading JSON: {json_path}")

        with open(json_path) as f:
            return json.load(f)
    else:
        logger.error(f"{json_path} does not exist")
        return


def yesno(question):
    """Simple Yes/No Function."""
    prompt = f'{question} ? (y/n): '
    ans = input(prompt).strip().lower()
    if ans not in ['y', 'n']:
        print(f'{ans} is invalid, please try again...')
        return yesno(question)
    if ans == 'y':
        return True
    return False


def enter_album_url():

    prompt = "Please enter manually a valid bedetheque mobile url starting with https://m.bedetheque.com/ "
    ans = input(prompt).strip().lower()

    ans = ans.replace("https://www.bedetheque.com/", "https://m.bedetheque.com/")

    iter = 0
    while not ans.startswith('https://m.bedetheque.com/') and iter < 2:  # TODO: could modify this to replace www. with m.
        prompt = "Please enter manually a valid bedetheque mobile url"
        ans = input(prompt).strip().lower().replace("https://www.bedetheque.com/", "https://m.bedetheque.com/")
        iter += 1

    if 'ans' in locals():
        return ans
    else:
        logger = logging.getLogger(__name__)
        logger.error("No valid url was entered")

        return


def download_link(url, output_folder=None):
    if output_folder is None:
        output_folder = tempfile.mkdtemp()
    else:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

    urllib.request.urlretrieve(url, os.path.join(output_folder, os.path.basename(url)))

    return os.path.join(output_folder, os.path.basename(url))


def init_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    console_level = "DEBUG"
    console_handler = logging.StreamHandler(stream=sys.stdout)

    console_handler.setLevel(console_level)

    console_format = "%(asctime)s - %(levelname)-8s:L%(lineno)s - %(name)-5s - %(message)s"
    colored_formatter = ColorizedArgsFormatter(console_format)
    console_handler.setFormatter(colored_formatter)
    root_logger.addHandler(console_handler)


def _init_config():
    if UNIX_DIR_VAR in os.environ:
        bdnex_user_path = os.path.join(os.environ[UNIX_DIR_VAR],
                                       'bdnex')
    else:
        # On Windows, use APPDATA or USERPROFILE
        if os.name == 'nt':
            config_base = os.environ.get('APPDATA', os.environ.get('USERPROFILE', os.path.expanduser('~')))
        else:
            config_base = os.path.expanduser(UNIX_DIR_FALLBACK)
        bdnex_user_path = os.path.join(config_base, 'bdnex')
    
    user_config_path = os.path.join(bdnex_user_path,
                                   'bdnex.yaml')

    if os.path.exists(bdnex_user_path):
        if os.path.exists(user_config_path):
            return user_config_path
        else:
            shutil.copy(DEFAULT_CONFIG_YAML, user_config_path)
            return user_config_path
    else:
        os.makedirs(bdnex_user_path)
        shutil.copy(DEFAULT_CONFIG_YAML, user_config_path)
        return _init_config()


def bdnex_config():
    """
    Parse bdnex configuration
    Returns: dictionary containing configuration

    """
    config = yaml.safe_load(open(_init_config()))

    return config


def args():
    """
    Returns the script arguments

        Parameters:

        Returns:
            vargs (obj): input arguments
    """
    parser = argparse.ArgumentParser(description='BD metadata retriever',
                                    epilog='Use "bdnex catalog <command> --help" for catalog subcommands')
    
    # Create subparsers for catalog commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Catalog subcommand
    catalog_parser = subparsers.add_parser('catalog', help='Manage and explore your BD catalog')
    catalog_subparsers = catalog_parser.add_subparsers(dest='catalog_command', help='Catalog operations')
    
    # catalog list
    list_parser = catalog_subparsers.add_parser('list', help='List BDs by category')
    list_parser.add_argument('--by', dest='list_by', choices=['series', 'publisher', 'year'],
                            default='series', help='List by series, publisher, or year')
    list_parser.add_argument('--limit', type=int, default=100,
                            help='Maximum number of results (default: 100)')
    
    # catalog search
    search_parser = catalog_subparsers.add_parser('search', help='Search in your catalog')
    search_parser.add_argument('query', type=str, help='Search term')
    search_parser.add_argument('--publisher', type=str, default=None,
                              help='Filter by publisher')
    search_parser.add_argument('--year', type=int, default=None,
                              help='Filter by year')
    search_parser.add_argument('--limit', type=int, default=100,
                              help='Maximum number of results (default: 100)')
    
    # catalog stats
    stats_parser = catalog_subparsers.add_parser('stats', help='Show library statistics')
    
    # catalog export
    export_parser = catalog_subparsers.add_parser('export', help='Export catalog to file')
    export_parser.add_argument('--format', dest='export_format', choices=['csv', 'json'],
                              required=True, help='Export format')
    export_parser.add_argument('--output', dest='export_output', required=True,
                              help='Output file path')
    export_parser.add_argument('--publisher', type=str, default=None,
                              help='Filter by publisher')
    export_parser.add_argument('--year', type=int, default=None,
                              help='Filter by year')
    export_parser.add_argument('--series', type=str, default=None,
                              help='Filter by series')
    
    # Main processing arguments (original arguments)
    parser.add_argument('-f', '--input-file', dest='input_file', type=str, default=None,
                        help="BD file path",
                        required=False)

    parser.add_argument('-d', '--input-dir', dest='input_dir', type=str, default=None,
                        help="BD dir path to process",
                        required=False)

    parser.add_argument('-i', '--init', dest='init',
                        help="initialise or force bdnex to download sitemaps from bedetheque for album matching",
                        required=False)

    parser.add_argument('-v',
                        '--verbose',
                        default='info',
                        help='Provide logging level. default=info')
    
    parser.add_argument('-b', '--batch', dest='batch', action='store_true', default=False,
                        help="Batch mode: process multiple files and show consolidated challenge UI at end",
                        required=False)

    parser.add_argument('--no-progress', dest='no_progress', action='store_true', default=False,
                        help="Disable progress display",
                        required=False)
    
    parser.add_argument('-s', '--strict', dest='strict', action='store_true', default=False,
                        help="Strict mode: reject low-confidence matches instead of prompting",
                        required=False)
    
    # Phase 2A: CLI Integration - Database-related flags
    parser.add_argument('--resume', dest='resume_session', type=int, default=None,
                        help="Resume a previous batch processing session by ID",
                        required=False)
    
    parser.add_argument('--skip-processed', dest='skip_processed', action='store_true', default=False,
                        help="Skip files that have already been processed (requires database)",
                        required=False)
    
    parser.add_argument('--list-sessions', dest='list_sessions', action='store_true', default=False,
                        help="List all batch processing sessions stored in database",
                        required=False)
    
    parser.add_argument('--session-info', dest='session_info', type=int, default=None,
                        help="Show detailed statistics for a specific session ID",
                        required=False)
    
    parser.add_argument('--force', dest='force_reprocess', action='store_true', default=False,
                        help="Force reprocessing even if file is already in database",
                        required=False)
    
    # Renaming options
    parser.add_argument('--rename', dest='rename_template', type=str, default=None,
                        help="Rename files using template (e.g., '%%Series - Tome %%Number - %%Title')",
                        required=False)
    
    parser.add_argument('--rename-dry-run', dest='rename_dry_run', action='store_true', default=False,
                        help="Preview renaming without actually renaming files",
                        required=False)
    
    parser.add_argument('--no-backup', dest='no_backup', action='store_true', default=False,
                        help="Disable backup creation when renaming files",
                        required=False)

    init_logging()

    vargs = parser.parse_args()

    if 'vargs.input_file' in locals():
        if not os.path.exists(vargs.input_file):
           raise ValueError('{path} not a valid path'.format(path=vargs.input_file))

    if 'vargs.input_dir' in locals():
        if not os.path.exists(vargs.input_dir):
            raise ValueError('{path} not a valid path'.format(path=vargs.input_dir))

    return vargs


@contextlib.contextmanager
def temporary_directory(*args, **kwargs):
    d = tempfile.mkdtemp(*args, **kwargs)
    try:
        yield d
    finally:
        shutil.rmtree(d)
