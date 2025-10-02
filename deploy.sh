#!/bin/bash

echo "Building and deploying Research Paper Platform..."

# Build Docker image
docker build -t research-paper-platform .

# Stop existing container if running
docker stop research-paper-platform 2>/dev/null || true
docker rm research-paper-platform 2>/dev/null || true

# Run new container
docker run -d \
  --name research-paper-platform \
  -p 5000:5000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/papers.db:/app/papers.db \
  research-paper-platform

echo "Application deployed at http://localhost:5000"