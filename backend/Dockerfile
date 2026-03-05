FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Download the database from GitHub Releases
RUN curl -L -o enterprises.db \
    "https://github.com/Gopika-G2006/enterprise-explorer/releases/download/v1.0-data/enterprises.db"

# Run the app
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
