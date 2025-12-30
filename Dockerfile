FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    unrar \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir flask flask-cors

# Create directories for data
RUN mkdir -p /data/comics /data/output /root/.local/share/bdnex /root/.config/bdnex

# Expose port for web interface
EXPOSE 5000

# Default command
CMD ["python", "-m", "bdnex.web.app"]
