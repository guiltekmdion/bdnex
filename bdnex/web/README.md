# BDneX Web Interface

The BDneX web interface provides a user-friendly way to manage and monitor your comic metadata tagging operations.

## Features

- **Dashboard**: Real-time statistics on jobs processed, active, completed, and failed
- **Process Management**: Submit single files or entire directories for processing
- **Job Tracking**: Monitor the status and progress of all processing jobs
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

# Run the web server
python -m bdnex.web.app
```

Then access the interface at `http://localhost:5000`.

## API Endpoints

### Status and Monitoring

- `GET /api/status` - Get application status
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/<id>` - Get specific job details
- `GET /api/logs` - Get application logs (supports `?level=INFO` and `?limit=100`)
- `GET /health` - Health check endpoint

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

## Environment Variables

- `BDNEX_UPLOAD_FOLDER` - Directory for input comic files (default: `/data/comics`)
- `BDNEX_OUTPUT_FOLDER` - Directory for processed files (default: `/data/output`)
- `FLASK_ENV` - Flask environment (default: `production`)

## Security Notes

The web interface is designed for local use or use within a private network. If you plan to expose it to the internet, consider:

- Adding authentication/authorization
- Using HTTPS
- Implementing rate limiting
- Validating file paths to prevent directory traversal attacks
