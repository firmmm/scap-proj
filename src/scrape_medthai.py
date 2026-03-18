#!/usr/bin/env python3
"""
Medthai.com Disease Content Scraper
Scrapes full article content from disease pages (text only, no images).
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin


class MedthaiScraper:
    """Scraper for Medthai.com disease articles."""

    BASE_URL = "https://medthai.com"
    DISEASE_INDEX_URL = "https://medthai.com/%e0%b8%a3%e0%b8%b2%e0%b8%a2%e0%b8%8a%e0%b8%b7%e0%b9%88%e0%b8%ad%e0%b9%82%e0%b8%a3%e0%b8%84/"

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

    def scrape_disease_urls_from_index(self) -> List[str]:
        """Scrape all disease URLs from the main disease index page."""
        soup = self.fetch_page(self.DISEASE_INDEX_URL)
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

        print(f"Found {len(urls)} disease URLs")
        return list(urls)

    def scrape_disease_article(self, url: str) -> Optional[Dict]:
        """Scrape full content from a disease article page (text only)."""
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

        # Fallback: find largest content div with disease-related text
        for div in soup.find_all('div'):
            text = div.get_text()
            if len(text) > 1000 and 'โรค' in text:
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

        for elem in soup.find_all(['span', 'div']):
            text = elem.get_text(strip=True)
            if re.search(r'\d{1,2}\s+\w+\s+2\d{3}', text):
                return text

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

    def scrape_all_diseases(self, max_diseases: Optional[int] = None) -> List[Dict]:
        """
        Scrape all disease articles.

        Args:
            max_diseases: Maximum number of diseases to scrape (None for all)

        Returns:
            List of article dictionaries
        """
        urls = self.scrape_disease_urls_from_index()

        if max_diseases:
            urls = urls[:max_diseases]

        all_articles = []
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Scraping...")
            article = self.scrape_disease_article(url)
            if article:
                all_articles.append(article)
                print(f"  ✓ Scraped: {article['title'][:50]}...")
            else:
                print(f"  ✗ Failed: {url}")

        return all_articles

    def save_to_json(self, data: List[Dict], output_dir: str = "output"):
        """Save scraped data to JSON file."""
        import os
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, "medthai_content.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nData saved to {filepath}")
        return filepath

    def get_summary(self, articles: List[Dict]) -> Dict:
        """Get summary statistics of scraped data."""
        total_sections = sum(len(a.get('sections', [])) for a in articles)
        total_references = sum(len(a.get('references', [])) for a in articles)

        return {
            "total_articles": len(articles),
            "total_sections": total_sections,
            "total_references": total_references,
        }


def main():
    """Main function to run the scraper."""
    print("=" * 60)
    print("Medthai.com Disease Content Scraper")
    print("=" * 60)

    scraper = MedthaiScraper(delay=2.0)

    print("\nScraping ALL disease articles...")
    print("Note: This will take several minutes. Press Ctrl+C to stop anytime.\n")

    articles = scraper.scrape_all_diseases(max_diseases=None)

    if articles:
        print("\n" + "=" * 60)
        print("Scraping Complete!")
        print("=" * 60)

        summary = scraper.get_summary(articles)
        print(f"\nTotal Articles: {summary['total_articles']}")
        print(f"Total Sections: {summary['total_sections']}")
        print(f"Total References: {summary['total_references']}")

        scraper.save_to_json(articles)

        print("\n" + "=" * 60)
        print("Sample Articles:")
        print("=" * 60)
        for i, article in enumerate(articles[:5], 1):
            print(f"\n{i}. {article['title']}")
            print(f"   URL: {article['url']}")
            print(f"   Author: {article.get('author', 'N/A')}")
            print(f"   Sections: {len(article.get('sections', []))}")

        if len(articles) > 5:
            print(f"\n... and {len(articles) - 5} more articles")
    else:
        print("No articles scraped")


if __name__ == "__main__":
    main()
