#!/usr/bin/env python3
"""Test if other Medthai pages have the same structure"""

import requests
from bs4 import BeautifulSoup

URLS = [
    "https://medthai.com/%E0%B8%A3%E0%B8%B2%E0%B8%A2%E0%B8%8A%E0%B8%B7%E0%B9%88%E0%B8%AD%E0%B8%A2%E0%B8%B2/",  # ยา (Drugs)
    "https://medthai.com/%e0%b8%a3%e0%b8%b2%e0%b8%a2%e0%b8%8a%e0%b8%b7%e0%b9%88%e0%b8%ad%e0%b8%aa%e0%b8%a1%e0%b8%b8%e0%b8%99%e0%b9%84%e0%b8%9e%e0%b8%a3/",  # สมุนไพร (Herbs)
    "https://medthai.com/%e0%b8%a3%e0%b8%b2%e0%b8%a2%e0%b8%8a%e0%b8%b7%e0%b9%88%e0%b8%ad%e0%b8%9c%e0%b8%b1%e0%b8%81/",  # ผัก (Vegetables)
    "https://medthai.com/%e0%b8%a3%e0%b8%b2%e0%b8%a2%e0%b8%8a%e0%b8%b7%e0%b9%88%e0%b8%ad%e0%b8%9c%e0%b8%a5%e0%b9%84%e0%b8%a1%e0%b9%89/",  # ผลไม้ (Fruits)
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

for url in URLS:
    print("=" * 60)
    print(f"Testing: {url}")
    print("=" * 60)
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for ul-custom-column (same structure as disease page)
        ul_custom = soup.find_all('ul', class_='ul-custom-column')
        
        # Count links
        all_links = soup.find_all('a', href=True)
        disease_like_links = [l for l in all_links if len(l.get_text(strip=True)) > 2]
        
        # Check page title
        title = soup.find('h1') or soup.find('title')
        
        print(f"✓ Page Title: {title.get_text(strip=True)[:80] if title else 'N/A'}")
        print(f"✓ ul-custom-column count: {len(ul_custom)}")
        print(f"✓ Total links: {len(all_links)}")
        
        # Sample some links
        sample_links = []
        for link in all_links[:50]:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if href and text and len(text) > 2 and href.startswith('../../') and '#' not in href:
                sample_links.append(f"  - {text} -> {href[:60]}")
        
        if sample_links:
            print(f"✓ Sample links ({len(sample_links)} found):")
            for s in sample_links[:5]:
                print(s)
        
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()
