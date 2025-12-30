# BDneX Docker Quick Start Guide

This guide will help you get started with BDneX using Docker in just a few minutes.

## Prerequisites

- Docker installed on your system
- Docker Compose installed on your system

## Quick Start Steps

### 1. Clone the repository

```bash
git clone https://github.com/lbesnard/bdnex.git
cd bdnex
```

### 2. Create data directories

```bash
mkdir -p data/comics data/output
```

### 3. Place your comics

Copy your comic files (CBZ or CBR format) into the `data/comics` directory:

```bash
cp /path/to/your/comics/*.cbz data/comics/
```

### 4. Start BDneX

```bash
docker-compose up -d
```

This command will:
- Build the Docker image
- Start the BDneX container
- Expose the web interface on port 5000

### 5. Access the web interface

Open your browser and navigate to:

```
http://localhost:5000
```

### 6. Initialize sitemaps (first time only)

1. In the web interface, scroll to the "Process Comics" section
2. Click the "Download Sitemaps" button
3. Wait for the initialization to complete (check the Jobs section)

This downloads the bedetheque.com sitemap data needed for comic matching.

### 7. Process your comics

**Option A: Process a single file**
1. Enter the file path: `/data/comics/your-comic.cbz`
2. Click "Process File"

**Option B: Process entire directory**
1. Enter the directory path: `/data/comics`
2. Click "Process Directory"

### 8. Monitor progress

- View job status in the "Jobs" section
- Check logs in the "Logs" section at the bottom
- Filter logs by level (INFO, WARNING, ERROR, DEBUG)

### 9. View processed comics

Processed comics will be in the `data/output` directory with embedded metadata.

## Stopping BDneX

```bash
docker-compose down
```

## Viewing Logs

```bash
docker-compose logs -f
```

## Updating BDneX

```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Container won't start
Check logs: `docker-compose logs`

### Can't access web interface
Verify the container is running: `docker-compose ps`

### Permission issues
Ensure data directories are writable:
```bash
chmod -R 755 data/
```

### Sitemap download fails
Check your internet connection and try again from the web interface.

## Additional Resources

- [Main README](README.md)
- [Web Interface Documentation](bdnex/web/README.md)
- [GitHub Issues](https://github.com/lbesnard/bdnex/issues)

## Support

For help and support, please:
1. Check the troubleshooting section above
2. Review existing GitHub issues
3. Create a new issue with detailed information about your problem
