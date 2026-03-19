#!/bin/bash
# Run the Medthai scraper

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"

cd "$PROJECT_DIR"

# Activate virtual environment
. med-scap-env/bin/activate

# Run scraper
python src/scrape_medthai.py
