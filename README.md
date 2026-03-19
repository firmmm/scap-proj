# Medthai Scraper

Web scraper for extracting content from [Medthai.com](https://medthai.com/).

## Features

- Scrapes multiple categories: diseases, drugs, herbs, vegetables, fruits
- Extracts full text content (no images)
- Organizes content by sections
- Configurable via `config.ini`
- Saves output as clean JSON

## Project Structure

```
scap_med/
├── src/                    # Source code
│   └── scrape_medthai.py   # Main scraper script
├── output/                 # Scraped data output
│   └── *.json
├── scripts/                # Utility scripts
├── tests/                  # Test files
├── med-scap-env/           # Python virtual environment
├── config.ini              # Configuration file
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

### 1. Configure categories to scrape

Edit `config.ini` and enable the categories you want:

```ini
[diseases]
enabled = true   # Change to true to scrape diseases

[drugs]
enabled = true   # Change to true to scrape drugs/medicines

[herbs]
enabled = true   # Change to true to scrape herbs

[vegetables]
enabled = true   # Change to true to scrape vegetables

[fruits]
enabled = true   # Change to true to scrape fruits
```

### 2. Run the scraper

```bash
source med-scap-env/bin/activate
python src/scrape_medthai.py
```

Or use the run script:
```bash
./scripts/run.sh
```

### 3. Output files

Each category saves to a separate file in `output/`:
- `diseases.json`
- `drugs.json`
- `herbs.json`
- `vegetables.json`
- `fruits.json`

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
        "content": ["text...", "text..."]
      },
      {
        "heading": "สาเหตุ",
        "content": [
          {"list": ["item 1", "item 2"]}
        ]
      }
    ],
    "references": [],
    "related_articles": []
  }
]
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `delay` | Seconds between requests | 2.0 |
| `output_dir` | Output directory | output |
| `enabled` | Enable/disable category | false |
| `url` | Category index URL | - |
| `output_file` | Output JSON filename | - |

## Notes

- Each category takes ~5-10 minutes to scrape completely
- The scraper respects the server with configurable delay
- All content is in Thai language
- Press `Ctrl+C` to stop anytime (data saved progressively)
