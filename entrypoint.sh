#!/bin/sh
set -e

echo "==> Seeding database..."
python -m src.seed

echo "==> Generating sitemap..."
python -m src.sitemap || echo "sitemap generation failed; continuing"

echo "==> Starting Flask app..."
exec python app.py
