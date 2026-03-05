#!/usr/bin/env bash
# Render build script: downloads the database and installs dependencies

set -e

echo "=== Installing Python dependencies ==="
pip install -r backend/requirements.txt

echo "=== Downloading enterprises.db from GitHub Releases ==="
mkdir -p backend
curl -L -o backend/enterprises.db \
  "https://github.com/Gopika-G2006/enterprise-explorer/releases/download/v1.0-data/enterprises.db"

echo "=== Build complete ==="
ls -lh backend/enterprises.db
