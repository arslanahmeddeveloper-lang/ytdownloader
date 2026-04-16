# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# ffmpeg is highly recommended/required for yt-dlp processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy backend requirements file
COPY backend/requirements.txt ./backend/

# Install python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the rest of the application source code
COPY . .

# Ensure downloads directory exists with correct permissions
RUN mkdir -p backend/downloads && chmod 777 backend/downloads

# Expose the standard Railway port (or customizable via env)
EXPOSE $PORT

# Start application
# Railway provides the PORT environment variable natively.
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
