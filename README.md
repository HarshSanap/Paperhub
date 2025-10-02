# Research Paper Platform

A Flask web application for uploading research papers and extracting key information using NLP.

## Features

- 📄 PDF upload and text extraction
- 🔍 Automatic title and author detection
- 🏷️ Keyword extraction using TextRank
- 📝 Automatic summary generation
- 🔎 Search functionality
- 📱 Responsive web interface

## Quick Start

### Using Docker (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or use the deployment script
chmod +x deploy.sh
./deploy.sh
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Run the application
python run.py
```

Visit http://localhost:5000

## API Endpoints

- `GET /` - Upload page
- `POST /upload` - Upload PDF file
- `GET /papers` - List all papers
- `GET /search?q=query` - Search papers
- `GET /api/papers` - JSON API for papers

## Deployment Options

### Docker
```bash
docker build -t research-paper-platform .
docker run -p 5000:5000 research-paper-platform
```

### Cloud Platforms
- **Heroku**: Use `Procfile` with `web: gunicorn app:app`
- **AWS**: Deploy using ECS or Elastic Beanstalk
- **Google Cloud**: Use Cloud Run or App Engine

## Technology Stack

- **Backend**: Flask, SQLite
- **NLP**: spaCy, NLTK, PyTextRank
- **Frontend**: HTML5, CSS3, JavaScript
- **Deployment**: Docker, Gunicorn