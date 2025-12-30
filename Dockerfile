FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    unrar-free \
    libgl1 \
    libglib2.0-0 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

# Set working directory
WORKDIR /app

# Copy application files
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -e .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org flask flask-cors

# Create directories for data
RUN mkdir -p /data/comics /data/output /root/.local/share/bdnex /root/.config/bdnex

# Expose port for web interface
EXPOSE 5000

# Default command
CMD ["python", "-m", "bdnex.web.app"]
