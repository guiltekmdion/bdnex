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
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from collections import deque

from bdnex.ui import add_metadata_from_bdgest
from bdnex.lib.bdgest import BdGestParse
from bdnex.lib.utils import bdnex_config

app = Flask(__name__)
CORS(app)

# Configuration - use environment variables with fallback to /data
UPLOAD_FOLDER = os.environ.get('BDNEX_UPLOAD_FOLDER', '/data/comics')
OUTPUT_FOLDER = os.environ.get('BDNEX_OUTPUT_FOLDER', '/data/output')
MAX_LOG_LINES = 1000

# Ensure directories exist (only if they can be created)
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
except (PermissionError, FileNotFoundError):
    # If we can't create directories (e.g., in testing), that's okay
    pass

# Global storage for jobs and logs
jobs = {}
log_buffer = deque(maxlen=MAX_LOG_LINES)
job_counter = 0


class LogHandler(logging.Handler):
    """Custom log handler to capture logs to buffer"""
    
    def emit(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': self.format(record),
            'logger': record.name
        }
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


def process_comic_task(job_id, filepath):
    """Background task to process a comic file"""
    global jobs
    
    try:
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['started_at'] = datetime.now().isoformat()
        
        logger = logging.getLogger(__name__)
        logger.info(f"Job {job_id}: Starting processing of {filepath}")
        
        # Process the comic
        add_metadata_from_bdgest(filepath)
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['completed_at'] = datetime.now().isoformat()
        logger.info(f"Job {job_id}: Completed successfully")
        
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['completed_at'] = datetime.now().isoformat()
        logger.error(f"Job {job_id}: Failed with error: {str(e)}")


def process_directory_task(job_id, dirpath):
    """Background task to process a directory of comics"""
    global jobs
    
    try:
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['started_at'] = datetime.now().isoformat()
        
        logger = logging.getLogger(__name__)
        logger.info(f"Job {job_id}: Starting directory processing of {dirpath}")
        
        # Find all comic files
        files = []
        for ext in ['*.cbz', '*.cbr']:
            for path in Path(dirpath).rglob(ext):
                files.append(path.absolute().as_posix())
        
        jobs[job_id]['total_files'] = len(files)
        jobs[job_id]['processed_files'] = 0
        
        # Process each file
        for file in files:
            try:
                logger.info(f"Job {job_id}: Processing file {file}")
                add_metadata_from_bdgest(file)
                jobs[job_id]['processed_files'] += 1
            except Exception as e:
                logger.error(f"Job {job_id}: Failed to process {file}: {str(e)}")
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['completed_at'] = datetime.now().isoformat()
        logger.info(f"Job {job_id}: Completed directory processing")
        
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['completed_at'] = datetime.now().isoformat()
        logger.error(f"Job {job_id}: Directory processing failed: {str(e)}")


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get application status"""
    return jsonify({
        'status': 'running',
        'version': '0.1',
        'jobs': len(jobs),
        'active_jobs': sum(1 for j in jobs.values() if j['status'] == 'processing')
    })


@app.route('/api/jobs', methods=['GET'])
def api_jobs():
    """Get list of all jobs"""
    return jsonify(list(jobs.values()))


@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def api_job_detail(job_id):
    """Get details of a specific job"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(jobs[job_id])


@app.route('/api/process/file', methods=['POST'])
def api_process_file():
    """Process a single comic file"""
    global job_counter, jobs
    
    data = request.json
    filepath = data.get('filepath')
    
    if not filepath:
        return jsonify({'error': 'No filepath provided'}), 400
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    job_counter += 1
    job_id = job_counter
    
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
    global job_counter, jobs
    
    data = request.json
    dirpath = data.get('dirpath')
    
    if not dirpath:
        return jsonify({'error': 'No directory path provided'}), 400
    
    if not os.path.exists(dirpath):
        return jsonify({'error': 'Directory not found'}), 404
    
    job_counter += 1
    job_id = job_counter
    
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
    global job_counter, jobs
    
    job_counter += 1
    job_id = job_counter
    
    jobs[job_id] = {
        'id': job_id,
        'type': 'init',
        'status': 'queued',
        'created_at': datetime.now().isoformat()
    }
    
    def init_task(job_id):
        try:
            jobs[job_id]['status'] = 'processing'
            jobs[job_id]['started_at'] = datetime.now().isoformat()
            
            logger = logging.getLogger(__name__)
            logger.info(f"Job {job_id}: Starting sitemap download")
            
            BdGestParse().download_sitemaps()
            
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
            logger.info(f"Job {job_id}: Sitemap download completed")
            
        except Exception as e:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = str(e)
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
            logger.error(f"Job {job_id}: Sitemap download failed: {str(e)}")
    
    thread = threading.Thread(target=init_task, args=(job_id,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202


@app.route('/api/logs', methods=['GET'])
def api_logs():
    """Get application logs"""
    level = request.args.get('level', None)
    limit = int(request.args.get('limit', 100))
    
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
        last_seen = len(log_buffer)
        while True:
            current_size = len(log_buffer)
            if current_size > last_seen:
                # New logs available
                new_logs = list(log_buffer)[last_seen:]
                for log in new_logs:
                    yield f"data: {jsonify(log).get_data(as_text=True)}\n\n"
                last_seen = current_size
            time.sleep(1)
    
    return app.response_class(generate(), mimetype='text/event-stream')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.info("Starting BDneX Web Interface")
    app.run(host='0.0.0.0', port=5000, debug=False)
