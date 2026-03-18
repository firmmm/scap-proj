#!/bin/bash
# Run the Medthai scraper

cd "$(dirname "$0")/.."

# Activate virtual environment
source med-scap-env/bin/activate

# Run scraper
python src/scrape_medthai.py
