# BDneX Web Interface

The BDneX web interface provides a user-friendly way to manage and monitor your comic metadata tagging operations with automatic processing capabilities.

## Features

- **Dashboard**: Real-time statistics on jobs processed, active, completed, and failed
- **Process Management**: Submit single files or entire directories for processing
- **Folder Watcher**: Automatically monitor and process new comics in a watch folder
- **Job Tracking**: Monitor the status and progress of all processing jobs
- **Uncertain Matches**: Review and resolve comics with low confidence matches
- **Log Viewer**: View application logs in real-time with filtering by log level
- **Sitemap Management**: Initialize and update bedetheque.com sitemaps

## Running with Docker

The easiest way to use the web interface is through Docker:

```bash
# Start the application
docker-compose up -d

# Access the web interface
open http://localhost:5000
```

## Running Locally

You can also run the web interface without Docker:

```bash
# Install dependencies
pip install flask flask-cors

# Set environment variables (optional)
export BDNEX_UPLOAD_FOLDER=/path/to/comics
export BDNEX_OUTPUT_FOLDER=/path/to/output
export BDNEX_WATCH_FOLDER=/path/to/watch
export BDNEX_AUTO_WATCH=true
export BDNEX_WATCH_INTERVAL=300

# Run the web server
python -m bdnex.web.app
```

Then access the interface at `http://localhost:5000`.

## API Endpoints

### Status and Monitoring

- `GET /api/status` - Get application status (includes watcher status and uncertain matches count)
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/<id>` - Get specific job details
- `GET /api/logs` - Get application logs (supports `?level=INFO` and `?limit=100`)
- `GET /health` - Health check endpoint

### Folder Watcher (NEW)

- `GET /api/watcher/status` - Get folder watcher status and unprocessed file count
- `POST /api/watcher/enable` - Enable folder watcher
  - Body: `{"interval": 300}` (interval in seconds, minimum 60)
- `POST /api/watcher/disable` - Disable folder watcher

### Uncertain Matches (NEW)

- `GET /api/uncertain-matches` - Get list of comics with uncertain matches
- `POST /api/uncertain-matches/<index>/resolve` - Resolve an uncertain match
  - Body: `{"action": "retry"}` or `{"action": "dismiss"}`

### Operations

- `POST /api/process/file` - Process a single comic file
  - Body: `{"filepath": "/path/to/comic.cbz"}`
  
- `POST /api/process/directory` - Process a directory of comics
  - Body: `{"dirpath": "/path/to/comics"}`
  
- `POST /api/init` - Initialize/update bedetheque.com sitemaps

## Job Status

Jobs can have the following statuses:

- `queued` - Job is queued and waiting to be processed
- `processing` - Job is currently being processed
- `completed` - Job completed successfully
- `failed` - Job failed with an error

Job types include:
- `file` - Single file processing
- `directory` - Directory batch processing
- `auto-watch` - Automatically triggered by folder watcher
- `retry-uncertain` - Retry of an uncertain match
- `init` - Sitemap initialization

## Environment Variables

- `BDNEX_UPLOAD_FOLDER` - Directory for input comic files (default: `/data/comics`)
- `BDNEX_OUTPUT_FOLDER` - Directory for processed files (default: `/data/output`)
- `BDNEX_WATCH_FOLDER` - Directory to monitor for automatic processing (default: `/data/watch`)
- `BDNEX_AUTO_WATCH` - Enable automatic folder watching on startup (default: `false`)
- `BDNEX_WATCH_INTERVAL` - Scan interval in seconds for folder watcher (default: `300`, minimum: `60`)
- `FLASK_ENV` - Flask environment (default: `production`)

## Automatic Processing

The folder watcher feature enables BDneX to run as a continuous service:

1. **Enable the watcher** via the web interface or set `BDNEX_AUTO_WATCH=true`
2. **Place comics** in the watch folder (`/data/watch` by default)
3. **BDneX automatically detects** new files based on the configured interval
4. **Processing happens automatically** respecting concurrent job limits
5. **Track processed files** to avoid reprocessing

This is perfect for:
- Network attached storage (NAS) setups
- Automated comic library management
- Scheduled batch processing
- Continuous monitoring scenarios

## Uncertain Matches

When BDneX encounters comics it cannot match with high confidence, they are added to the "Uncertain Matches" section where you can:

- **Review** the comic details and matching error
- **Retry** processing with updated metadata
- **Dismiss** if the comic doesn't need processing

This ensures metadata accuracy and prevents incorrect tagging.

## Security Notes

The web interface is designed for local use or use within a private network. If you plan to expose it to the internet, consider:

- Adding authentication/authorization
- Using HTTPS
- Implementing rate limiting
- Validating file paths to prevent directory traversal attacks
- Restricting network access with firewalls
