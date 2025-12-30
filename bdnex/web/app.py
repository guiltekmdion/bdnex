#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BDneX Web Interface
Provides a web-based interface to manage and monitor BDneX operations.
"""

import os
import logging
import threading
import time
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from collections import deque
from threading import Lock

from bdnex.ui import add_metadata_from_bdgest
from bdnex.lib.bdgest import BdGestParse

app = Flask(__name__)
CORS(app)

# Configuration - use environment variables with fallback to /data
UPLOAD_FOLDER = os.environ.get('BDNEX_UPLOAD_FOLDER', '/data/comics')
OUTPUT_FOLDER = os.environ.get('BDNEX_OUTPUT_FOLDER', '/data/output')
WATCH_FOLDER = os.environ.get('BDNEX_WATCH_FOLDER', '/data/watch')
MAX_LOG_LINES = 1000
MAX_CONCURRENT_JOBS = 5
AUTO_WATCH_ENABLED = os.environ.get('BDNEX_AUTO_WATCH', 'false').lower() == 'true'
AUTO_WATCH_INTERVAL = int(os.environ.get('BDNEX_WATCH_INTERVAL', '300'))  # 5 minutes default

# Ensure directories exist (only if they can be created)
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(WATCH_FOLDER, exist_ok=True)
except (PermissionError, FileNotFoundError):
    # If we can't create directories (e.g., in testing), that's okay
    pass

# Global storage for jobs and logs with thread safety
jobs = {}
log_buffer = deque(maxlen=MAX_LOG_LINES)
job_counter = 0
jobs_lock = Lock()
logs_lock = Lock()
active_threads = 0
threads_lock = Lock()
job_counter_lock = Lock()

# Storage for processed files and uncertain matches
processed_files = set()
uncertain_matches = []
processed_files_lock = Lock()
uncertain_matches_lock = Lock()

# Watcher control
watcher_enabled = AUTO_WATCH_ENABLED
watcher_interval = AUTO_WATCH_INTERVAL
watcher_thread = None
watcher_lock = Lock()


class LogHandler(logging.Handler):
    """Custom log handler to capture logs to buffer"""
    
    def emit(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': self.format(record),
            'logger': record.name
        }
        with logs_lock:
            log_buffer.append(log_entry)


# Setup logging
log_handler = LogHandler()
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(name)s - %(message)s')
log_handler.setFormatter(formatter)

# Add handler to root logger
root_logger = logging.getLogger()
root_logger.addHandler(log_handler)
root_logger.setLevel(logging.INFO)


def process_comic_task(job_id, filepath, track_processed=True):
    """Background task to process a comic file"""
    global active_threads
    
    try:
        with threads_lock:
            active_threads += 1
        
        with jobs_lock:
            jobs[job_id]['status'] = 'processing'
            jobs[job_id]['started_at'] = datetime.now().isoformat()
        
        logger = logging.getLogger(__name__)
        logger.info(f"Job {job_id}: Starting processing of {filepath}")
        
        # Process the comic
        # Note: Currently, uncertain matches are detected based on exception messages
        # since add_metadata_from_bdgest doesn't return confidence scores.
        # A future improvement would be to modify add_metadata_from_bdgest to return
        # match confidence and use that for more accurate uncertain match detection.
        try:
            add_metadata_from_bdgest(filepath)
            
            # Mark as processed
            if track_processed:
                with processed_files_lock:
                    processed_files.add(filepath)
            
            with jobs_lock:
                jobs[job_id]['status'] = 'completed'
                jobs[job_id]['completed_at'] = datetime.now().isoformat()
            logger.info(f"Job {job_id}: Completed successfully")
        except Exception as e:
            # Check if it's a low confidence match (simplified detection)
            error_msg = str(e)
            if 'confidence' in error_msg.lower() or 'matching' in error_msg.lower():
                with uncertain_matches_lock:
                    uncertain_matches.append({
                        'filepath': filepath,
                        'timestamp': datetime.now().isoformat(),
                        'error': error_msg,
                        'job_id': job_id
                    })
                logger.warning(f"Job {job_id}: Uncertain match for {filepath}")
            raise
        
    except Exception as e:
        with jobs_lock:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = str(e)
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
        logger.error(f"Job {job_id}: Failed with error: {str(e)}")
    finally:
        with threads_lock:
            active_threads -= 1


def process_directory_task(job_id, dirpath):
    """Background task to process a directory of comics"""
    global active_threads
    
    try:
        with threads_lock:
            active_threads += 1
            
        with jobs_lock:
            jobs[job_id]['status'] = 'processing'
            jobs[job_id]['started_at'] = datetime.now().isoformat()
        
        logger = logging.getLogger(__name__)
        logger.info(f"Job {job_id}: Starting directory processing of {dirpath}")
        
        # Find all comic files
        files = []
        for ext in ['*.cbz', '*.cbr']:
            for path in Path(dirpath).rglob(ext):
                files.append(path.absolute().as_posix())
        
        with jobs_lock:
            jobs[job_id]['total_files'] = len(files)
            jobs[job_id]['processed_files'] = 0
        
        # Process each file
        for file in files:
            try:
                logger.info(f"Job {job_id}: Processing file {file}")
                add_metadata_from_bdgest(file)
                with jobs_lock:
                    jobs[job_id]['processed_files'] += 1
            except Exception as e:
                logger.error(f"Job {job_id}: Failed to process {file}: {str(e)}")
        
        with jobs_lock:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
        logger.info(f"Job {job_id}: Completed directory processing")
        
    except Exception as e:
        with jobs_lock:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = str(e)
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
        logger.error(f"Job {job_id}: Directory processing failed: {str(e)}")
    finally:
        with threads_lock:
            active_threads -= 1


def get_unprocessed_files(watch_dir):
    """Find all comic files in watch directory that haven't been processed"""
    unprocessed = []
    
    if not os.path.exists(watch_dir):
        return unprocessed
    
    for ext in ['*.cbz', '*.cbr']:
        for path in Path(watch_dir).rglob(ext):
            filepath = path.absolute().as_posix()
            with processed_files_lock:
                if filepath not in processed_files:
                    unprocessed.append(filepath)
    
    return unprocessed


def folder_watcher_task():
    """Background task that watches for new comics and processes them"""
    global watcher_enabled, watcher_interval
    
    logger = logging.getLogger(__name__)
    logger.info("Folder watcher started")
    
    while True:
        try:
            with watcher_lock:
                if not watcher_enabled:
                    logger.info("Folder watcher disabled, sleeping...")
                    time.sleep(10)
                    continue
                
                interval = watcher_interval
            
            # Find unprocessed files
            unprocessed = get_unprocessed_files(WATCH_FOLDER)
            
            if unprocessed:
                logger.info(f"Found {len(unprocessed)} unprocessed files in watch folder")
                
                # Check if we can process more jobs
                with threads_lock:
                    available_slots = MAX_CONCURRENT_JOBS - active_threads
                
                if available_slots > 0:
                    # Process up to available slots
                    for filepath in unprocessed[:available_slots]:
                        logger.info(f"Auto-processing: {filepath}")
                        
                        with job_counter_lock:
                            global job_counter
                            job_counter += 1
                            job_id = job_counter
                        
                        with jobs_lock:
                            jobs[job_id] = {
                                'id': job_id,
                                'type': 'auto-watch',
                                'filepath': filepath,
                                'status': 'queued',
                                'created_at': datetime.now().isoformat()
                            }
                        
                        # Start processing
                        thread = threading.Thread(
                            target=process_comic_task, 
                            args=(job_id, filepath, True)
                        )
                        thread.daemon = True
                        thread.start()
                else:
                    logger.debug("No available job slots, waiting...")
            
            # Sleep for the configured interval
            time.sleep(interval)
            
        except Exception as e:
            logger.error(f"Folder watcher error: {str(e)}")
            time.sleep(60)  # Sleep for a minute on error


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get application status"""
    with watcher_lock:
        watcher_status = {
            'enabled': watcher_enabled,
            'interval': watcher_interval
        }
    
    with uncertain_matches_lock:
        uncertain_count = len(uncertain_matches)
    
    with processed_files_lock:
        processed_count = len(processed_files)
    
    return jsonify({
        'status': 'running',
        'version': '0.1',
        'jobs': len(jobs),
        'active_jobs': sum(1 for j in jobs.values() if j['status'] == 'processing'),
        'watcher': watcher_status,
        'uncertain_matches': uncertain_count,
        'processed_files': processed_count
    })


@app.route('/api/jobs', methods=['GET'])
def api_jobs():
    """Get list of all jobs"""
    with jobs_lock:
        return jsonify(list(jobs.values()))


@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def api_job_detail(job_id):
    """Get details of a specific job"""
    with jobs_lock:
        if job_id not in jobs:
            return jsonify({'error': 'Job not found'}), 404
        return jsonify(jobs[job_id])


@app.route('/api/process/file', methods=['POST'])
def api_process_file():
    """Process a single comic file"""
    global job_counter, active_threads
    
    # Check if we've reached max concurrent jobs
    with threads_lock:
        if active_threads >= MAX_CONCURRENT_JOBS:
            return jsonify({'error': 'Maximum concurrent jobs reached. Please wait.'}), 429
    
    data = request.json
    filepath = data.get('filepath')
    
    if not filepath:
        return jsonify({'error': 'No filepath provided'}), 400
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    with job_counter_lock:
        job_counter += 1
        job_id = job_counter
    
    with jobs_lock:
        jobs[job_id] = {
            'id': job_id,
            'type': 'file',
            'filepath': filepath,
            'status': 'queued',
            'created_at': datetime.now().isoformat()
        }
    
    # Start background task
    thread = threading.Thread(target=process_comic_task, args=(job_id, filepath))
    thread.daemon = True
    thread.start()
    
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202


@app.route('/api/process/directory', methods=['POST'])
def api_process_directory():
    """Process all comics in a directory"""
    global job_counter, active_threads
    
    # Check if we've reached max concurrent jobs
    with threads_lock:
        if active_threads >= MAX_CONCURRENT_JOBS:
            return jsonify({'error': 'Maximum concurrent jobs reached. Please wait.'}), 429
    
    data = request.json
    dirpath = data.get('dirpath')
    
    if not dirpath:
        return jsonify({'error': 'No directory path provided'}), 400
    
    if not os.path.exists(dirpath):
        return jsonify({'error': 'Directory not found'}), 404
    
    with job_counter_lock:
        job_counter += 1
        job_id = job_counter
    
    with jobs_lock:
        jobs[job_id] = {
            'id': job_id,
            'type': 'directory',
            'dirpath': dirpath,
            'status': 'queued',
            'created_at': datetime.now().isoformat()
        }
    
    # Start background task
    thread = threading.Thread(target=process_directory_task, args=(job_id, dirpath))
    thread.daemon = True
    thread.start()
    
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202


@app.route('/api/init', methods=['POST'])
def api_init():
    """Initialize/update bedetheque sitemaps"""
    global job_counter, active_threads
    
    # Check if we've reached max concurrent jobs
    with threads_lock:
        if active_threads >= MAX_CONCURRENT_JOBS:
            return jsonify({'error': 'Maximum concurrent jobs reached. Please wait.'}), 429
    
    with job_counter_lock:
        job_counter += 1
        job_id = job_counter
    
    with jobs_lock:
        jobs[job_id] = {
            'id': job_id,
            'type': 'init',
            'status': 'queued',
            'created_at': datetime.now().isoformat()
        }
    
    def init_task(job_id):
        global active_threads
        try:
            with threads_lock:
                active_threads += 1
                
            with jobs_lock:
                jobs[job_id]['status'] = 'processing'
                jobs[job_id]['started_at'] = datetime.now().isoformat()
            
            logger = logging.getLogger(__name__)
            logger.info(f"Job {job_id}: Starting sitemap download")
            
            BdGestParse().download_sitemaps()
            
            with jobs_lock:
                jobs[job_id]['status'] = 'completed'
                jobs[job_id]['completed_at'] = datetime.now().isoformat()
            logger.info(f"Job {job_id}: Sitemap download completed")
            
        except Exception as e:
            with jobs_lock:
                jobs[job_id]['status'] = 'failed'
                jobs[job_id]['error'] = str(e)
                jobs[job_id]['completed_at'] = datetime.now().isoformat()
            logger.error(f"Job {job_id}: Sitemap download failed: {str(e)}")
        finally:
            with threads_lock:
                active_threads -= 1
    
    thread = threading.Thread(target=init_task, args=(job_id,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202


@app.route('/api/watcher/status', methods=['GET'])
def api_watcher_status():
    """Get folder watcher status"""
    with watcher_lock:
        status = {
            'enabled': watcher_enabled,
            'interval': watcher_interval,
            'watch_folder': WATCH_FOLDER
        }
    
    unprocessed = get_unprocessed_files(WATCH_FOLDER)
    status['unprocessed_count'] = len(unprocessed)
    
    return jsonify(status)


@app.route('/api/watcher/enable', methods=['POST'])
def api_watcher_enable():
    """Enable folder watcher"""
    global watcher_enabled, watcher_interval
    
    data = request.json or {}
    new_interval = data.get('interval', watcher_interval)
    
    try:
        new_interval = int(new_interval)
        if new_interval < 60:
            return jsonify({'error': 'Interval must be at least 60 seconds'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid interval value'}), 400
    
    with watcher_lock:
        watcher_enabled = True
        watcher_interval = new_interval
    
    logger = logging.getLogger(__name__)
    logger.info(f"Folder watcher enabled with interval {new_interval}s")
    
    return jsonify({'status': 'enabled', 'interval': new_interval})


@app.route('/api/watcher/disable', methods=['POST'])
def api_watcher_disable():
    """Disable folder watcher"""
    global watcher_enabled
    
    with watcher_lock:
        watcher_enabled = False
    
    logger = logging.getLogger(__name__)
    logger.info("Folder watcher disabled")
    
    return jsonify({'status': 'disabled'})


@app.route('/api/uncertain-matches', methods=['GET'])
def api_uncertain_matches():
    """Get list of uncertain matches"""
    with uncertain_matches_lock:
        return jsonify(uncertain_matches)


@app.route('/api/uncertain-matches/<int:index>/resolve', methods=['POST'])
def api_resolve_uncertain_match(index):
    """Mark an uncertain match as resolved or retry processing"""
    data = request.json or {}
    action = data.get('action', 'retry')  # retry or dismiss
    
    with uncertain_matches_lock:
        if index < 0 or index >= len(uncertain_matches):
            return jsonify({'error': 'Invalid match index'}), 404
        
        match = uncertain_matches[index]
    
    if action == 'retry':
        # Retry processing this file
        filepath = match['filepath']
        
        with job_counter_lock:
            global job_counter
            job_counter += 1
            job_id = job_counter
        
        with jobs_lock:
            jobs[job_id] = {
                'id': job_id,
                'type': 'retry-uncertain',
                'filepath': filepath,
                'status': 'queued',
                'created_at': datetime.now().isoformat()
            }
        
        thread = threading.Thread(target=process_comic_task, args=(job_id, filepath, False))
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'retrying', 'job_id': job_id})
    
    elif action == 'dismiss':
        # Remove from uncertain matches list
        with uncertain_matches_lock:
            uncertain_matches.pop(index)
        
        return jsonify({'status': 'dismissed'})
    
    else:
        return jsonify({'error': 'Invalid action'}), 400


@app.route('/api/logs', methods=['GET'])
def api_logs():
    """Get application logs"""
    level = request.args.get('level', None)
    try:
        limit = int(request.args.get('limit', 100))
        # Cap the limit to prevent memory issues
        limit = min(limit, 1000)
    except (ValueError, TypeError):
        limit = 100
    
    with logs_lock:
        logs = list(log_buffer)
    
    if level:
        logs = [log for log in logs if log['level'] == level.upper()]
    
    # Return most recent logs first
    logs.reverse()
    logs = logs[:limit]
    
    return jsonify(logs)


@app.route('/api/logs/stream')
def api_logs_stream():
    """Stream logs in real-time (SSE)"""
    def generate():
        with logs_lock:
            last_seen = len(log_buffer)
        while True:
            with logs_lock:
                current_size = len(log_buffer)
                if current_size > last_seen:
                    # New logs available
                    new_logs = list(log_buffer)[last_seen:]
                    for log in new_logs:
                        yield f"data: {json.dumps(log)}\n\n"
                    last_seen = current_size
            time.sleep(1)
    
    return app.response_class(generate(), mimetype='text/event-stream')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


def start_watcher():
    """Start the folder watcher thread"""
    global watcher_thread
    
    if watcher_thread is None or not watcher_thread.is_alive():
        watcher_thread = threading.Thread(target=folder_watcher_task)
        watcher_thread.daemon = True
        watcher_thread.start()
        
        logger = logging.getLogger(__name__)
        logger.info(f"Folder watcher thread started (enabled: {watcher_enabled})")


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.info("Starting BDneX Web Interface")
    
    # Start the folder watcher thread
    start_watcher()
    
    app.run(host='0.0.0.0', port=5000, debug=False)
