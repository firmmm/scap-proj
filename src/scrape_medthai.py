#!/usr/bin/env python3
"""
Medthai.com Multi-Category Content Scraper
Scrapes content from multiple Medthai categories (diseases, drugs, herbs, etc.)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import configparser
from typing import Dict, List, Optional
from urllib.parse import urljoin


class MedthaiScraper:
    """Scraper for Medthai.com content."""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    }

    def __init__(self, delay: float = 2.0):
        """
        Initialize the scraper.

        Args:
            delay: Delay between requests in seconds (default: 2.0)
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return parsed BeautifulSoup object."""
        try:
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            time.sleep(self.delay)
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def scrape_urls_from_index(self, index_url: str) -> List[str]:
        """Scrape all URLs from an index page."""
        soup = self.fetch_page(index_url)
        if not soup:
            return []

        urls = set()

        for ul in soup.find_all('ul', class_='ul-custom-column'):
            for li in ul.find_all('li'):
                link = li.find('a')
                if link and link.get('href'):
                    href = link['href']
                    text = link.get_text(strip=True)

                    if len(text) < 2:
                        continue

                    # Normalize URL paths
                    if href.startswith('../../'):
                        href = href.replace('../../', '/')
                    elif href.startswith('../'):
                        href = href.replace('../', '/')

                    full_url = urljoin(self.BASE_URL, href)

                    if self.BASE_URL in full_url and '#' not in full_url:
                        urls.add(full_url)

        print(f"Found {len(urls)} URLs")
        return list(urls)

    def scrape_article(self, url: str) -> Optional[Dict]:
        """Scrape full content from an article page (text only)."""
        soup = self.fetch_page(url)
        if not soup:
            return None

        content_div = self._find_content_div(soup)

        return {
            "url": url,
            "title": self._extract_title(soup),
            "author": self._extract_author(soup),
            "publish_date": self._extract_date(soup),
            "sections": self._extract_sections(content_div),
            "references": self._extract_references(content_div),
            "related_articles": self._extract_related_articles(content_div),
        }

    def _find_content_div(self, soup) -> BeautifulSoup:
        """Find the main content div in the page."""
        for class_name in ['elementor-widget-theme-post-content',
                           'elementor-widget-text-editor', 'post-content']:
            content_div = soup.find(class_=class_name)
            if content_div:
                return content_div

        for div in soup.find_all('div'):
            text = div.get_text()
            if len(text) > 1000 and ('โรค' in text or 'ยา' in text or 'สมุนไพร' in text):
                return div

        return soup

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title."""
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else "Unknown"

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author name."""
        meta_author = soup.find('meta', attrs={'name': 'author'})
        if meta_author and meta_author.get('content'):
            return meta_author['content']

        for elem in soup.find_all(['span', 'div', 'p']):
            text = elem.get_text(strip=True)
            if text.startswith('โดย') and len(text) < 100:
                return text.replace('โดย', '').strip()

        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publish date."""
        for attr in ['article:modified_time', 'article:published_time']:
            meta = soup.find('meta', property=attr)
            if meta and meta.get('content'):
                return meta['content']

        for pattern in [{'class': 'elementor-post-date'},
                        {'class': 'post-date'}, {'class': 'entry-date'}]:
            elem = soup.find(**pattern)
            if elem:
                return elem.get_text(strip=True)

        return None

    def _extract_sections(self, content_div) -> List[Dict]:
        """Extract all content sections from the article."""
        sections = []
        current_section = {"heading": "บทนำ", "content": []}

        elements = content_div.find_all(
            ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'blockquote', 'li']
        )

        for elem in elements:
            tag_name = elem.name

            if tag_name == 'h1':
                continue

            if tag_name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                heading_text = elem.get_text(strip=True)

                skip_keywords = ['เรื่องที่เกี่ยวข้อง', 'เอกสารอ้างอิง', 'ภาพประกอบ',
                               'อ่านต่อ', 'แชร์', 'Related', 'Contents', 'สารบัญ']
                if any(skip in heading_text for skip in skip_keywords):
                    if current_section["content"]:
                        sections.append(current_section)
                    current_section = {"heading": heading_text, "content": []}
                    continue

                if current_section["content"]:
                    sections.append(current_section)
                current_section = {"heading": heading_text, "content": []}
                continue

            if tag_name == 'p':
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    skip_patterns = ['ภาพประกอบ', 'Disclaimer', 'Copyright', '©',
                                   'หน้าแรก', 'Medthai', 'เมดไทย']
                    if not any(pattern in text for pattern in skip_patterns):
                        current_section["content"].append(text)

            if tag_name in ['ul', 'ol']:
                list_items = []
                for li in elem.find_all('li', recursive=False):
                    item_text = li.get_text(strip=True)
                    if item_text and len(item_text) > 5:
                        list_items.append(item_text)

                    nested = li.find(['ul', 'ol'], recursive=False)
                    if nested:
                        nested_items = []
                        for nli in nested.find_all('li', recursive=False):
                            nt = nli.get_text(strip=True)
                            if nt:
                                nested_items.append(nt)
                        if nested_items:
                            list_items.append({"subitems": nested_items})

                if list_items:
                    current_section["content"].append({"list": list_items})

            if tag_name == 'blockquote':
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    current_section["content"].append({"quote": text})

        if current_section["content"]:
            sections.append(current_section)

        return sections

    def _extract_references(self, content_div) -> List[str]:
        """Extract references/bibliography section."""
        references = []

        for header in content_div.find_all(['h2', 'h3', 'h4']):
            text = header.get_text(strip=True)
            if 'เอกสารอ้างอิง' in text or 'อ้างอิง' in text:
                list_elem = header.find_next(['ul', 'ol'])
                if list_elem:
                    for li in list_elem.find_all('li'):
                        ref_text = li.get_text(strip=True)
                        if ref_text and len(ref_text) > 10:
                            references.append(ref_text)
                break

        return references

    def _extract_related_articles(self, content_div) -> List[Dict]:
        """Extract related articles section."""
        related = []

        for header in content_div.find_all(['h2', 'h3', 'h4']):
            text = header.get_text(strip=True)
            if 'เรื่องที่เกี่ยวข้อง' in text or 'Related' in text or 'อ่านต่อ' in text:
                list_elem = header.find_next(['ul', 'ol'])
                if list_elem:
                    for li in list_elem.find_all('li'):
                        link = li.find('a')
                        if link:
                            related.append({
                                "title": link.get_text(strip=True),
                                "url": urljoin(self.BASE_URL, link.get('href', ''))
                            })
                break

        return related

    def scrape_category(self, name: str, index_url: str, max_items: Optional[int] = None) -> List[Dict]:
        """
        Scrape all articles from a category.

        Args:
            name: Category name
            index_url: Index page URL
            max_items: Maximum number of articles to scrape (None for all)

        Returns:
            List of article dictionaries
        """
        print(f"\n{'=' * 60}")
        print(f"Scraping category: {name}")
        print(f"Index URL: {index_url}")
        print('=' * 60)

        self.BASE_URL = "https://medthai.com"
        urls = self.scrape_urls_from_index(index_url)

        if max_items:
            urls = urls[:max_items]

        all_articles = []
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Scraping...")
            article = self.scrape_article(url)
            if article:
                all_articles.append(article)
                print(f"  ✓ Scraped: {article['title'][:50]}...")
            else:
                print(f"  ✗ Failed: {url}")

        return all_articles

    def save_to_json(self, data: List[Dict], filepath: str):
        """Save scraped data to JSON file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nData saved to {filepath}")

    def get_summary(self, articles: List[Dict]) -> Dict:
        """Get summary statistics of scraped data."""
        total_sections = sum(len(a.get('sections', [])) for a in articles)
        total_references = sum(len(a.get('references', [])) for a in articles)

        return {
            "total_articles": len(articles),
            "total_sections": total_sections,
            "total_references": total_references,
        }


def load_config(config_path: str = "config.ini") -> dict:
    """Load configuration from config.ini file."""
    config = configparser.ConfigParser(interpolation=None)
    config.read(config_path, encoding='utf-8')

    categories = {}
    for section in config.sections():
        if section == 'scraper':
            continue
        if config.getboolean(section, 'enabled', fallback=False):
            categories[section] = {
                'url': config.get(section, 'url'),
                'output_file': config.get(section, 'output_file'),
            }

    scraper_config = {
        'delay': config.getfloat('scraper', 'delay', fallback=2.0),
        'output_dir': config.get('scraper', 'output_dir', fallback='output'),
    }

    return {'categories': categories, 'scraper': scraper_config}


def main():
    """Main function to run the scraper."""
    print("=" * 60)
    print("Medthai.com Multi-Category Content Scraper")
    print("=" * 60)

    # Load configuration
    config = load_config()
    categories = config['categories']
    scraper_config = config['scraper']

    if not categories:
        print("\nNo categories enabled in config.ini")
        print("Edit config.ini and set enabled = true for categories you want to scrape")
        return

    print(f"\nEnabled categories: {', '.join(categories.keys())}")
    print(f"Delay: {scraper_config['delay']}s")
    print(f"Output directory: {scraper_config['output_dir']}")

    scraper = MedthaiScraper(delay=scraper_config['delay'])
    output_dir = scraper_config['output_dir']

    for cat_name, cat_config in categories.items():
        articles = scraper.scrape_category(
            name=cat_name,
            index_url=cat_config['url'],
            max_items=None  # Set to a number to limit articles
        )

        if articles:
            summary = scraper.get_summary(articles)
            print(f"\n{'=' * 60}")
            print(f"Category: {cat_name}")
            print(f"Total Articles: {summary['total_articles']}")
            print(f"Total Sections: {summary['total_sections']}")

            output_file = os.path.join(output_dir, cat_config['output_file'])
            scraper.save_to_json(articles, output_file)

    print("\n" + "=" * 60)
    print("All scraping complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
