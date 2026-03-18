# Medthai Scraper

Web scraper for extracting disease content from [Medthai.com](https://medthai.com/).

## Features

- Scrapes all disease articles from the Medthai disease directory
- Extracts full text content (no images)
- Organizes content by sections (symptoms, causes, treatment, etc.)
- Saves output as clean JSON

## Project Structure

```
scap_med/
├── src/                    # Source code
│   └── scrape_medthai.py   # Main scraper script
├── output/                 # Scraped data output
│   └── medthai_content.json
├── scripts/                # Utility scripts
├── tests/                  # Test files
├── med-scap-env/           # Python virtual environment
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Installation

```bash
# Activate virtual environment
source med-scap-env/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt
```

## Usage

### Scrape all diseases
```bash
source med-scap-env/bin/activate
python src/scrape_medthai.py
```

### Output
The scraper saves data to `output/medthai_content.json`

## Output Format

```json
[
  {
    "url": "https://medthai.com/โรคกรดไหลย้อน/",
    "title": "โรคกรดไหลย้อน (GERD) อาการ, สาเหตุ, การรักษา...",
    "author": "เมดไทย",
    "publish_date": "2020-07-01T11:48:08+00:00",
    "sections": [
      {
        "heading": "บทนำ",
        "content": ["definition text...", "epidemiology text..."]
      },
      {
        "heading": "สาเหตุของโรคกรดไหลย้อน",
        "content": [
          {"list": ["cause 1", "cause 2", ...]}
        ]
      },
      {
        "heading": "อาการของโรคกรดไหลย้อน",
        "content": [
          {"list": ["symptom 1", "symptom 2", ...]}
        ]
      }
    ],
    "references": [],
    "related_articles": []
  }
]
```

## Configuration

Edit `src/scrape_medthai.py` to customize:

- `delay`: Request delay in seconds (default: 2.0)
- `max_diseases`: Limit number of articles to scrape

## Notes

- Scraping all ~195 articles takes approximately 7 minutes
- The scraper respects the server with a 2-second delay between requests
- Content is in Thai language
