#!/usr/bin/env python3
"""
M3U8 URL Extractor - Extract m3u8 URLs from iframe embeds
"""

import requests
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Configuration
INPUT_FILE = "events.json"
OUTPUT_FILE = "events_with_m3u8.json"
TIMEOUT = 15
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def load_events(filename=INPUT_FILE):
    """Load events from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded events from {filename}")
        return data
    except Exception as e:
        print(f"✗ Error loading file: {e}")
        return None

def extract_m3u8_from_iframe(iframe_url):
    """
    Extract m3u8 URL from iframe embed page
    
    Args:
        iframe_url (str): The iframe URL to scrape
        
    Returns:
        str: The m3u8 URL or None if not found
    """
    try:
        print(f"  → Fetching: {iframe_url}")
        response = requests.get(iframe_url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        
        html_content = response.text
        
        # Common patterns for m3u8 URLs in embedded players
        patterns = [
            r'["\'](https?://[^"\']*\.m3u8[^"\']*)["\']',
            r'source:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'src:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'video_url:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'hls_url:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                m3u8_url = matches[0]
                # Make absolute URL if relative
                if not m3u8_url.startswith('http'):
                    m3u8_url = urljoin(iframe_url, m3u8_url)
                print(f"  ✓ Found m3u8: {m3u8_url[:80]}...")
                return m3u8_url
        
        print(f"  ✗ No m3u8 URL found")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error fetching iframe: {e}")
        return None
    except Exception as e:
        print(f"  ✗ Error extracting m3u8: {e}")
        return None

def process_events(data):
    """
    Process all events and extract m3u8 URLs
    
    Args:
        data (dict): The events data structure
        
    Returns:
        dict: Updated data with m3u8 URLs
    """
    if not data or 'events' not in data or 'streams' not in data['events']:
        print("✗ Invalid data structure")
        return None
    
    streams_data = data['events']['streams']
    total_events = 0
    processed = 0
    found = 0
    
    # Count total events
    for category in streams_data:
        for stream in category.get('streams', []):
            total_events += 1
    
    print(f"\n📊 Processing {total_events} events...")
    print("=" * 60)
    
    # Process each category
    for category in streams_data:
        category_name = category.get('category', 'Unknown')
        print(f"\n📁 Category: {category_name}")
        
        for stream in category.get('streams', []):
            processed += 1
            event_name = stream.get('name', 'Unknown')
            iframe_url = stream.get('iframe')
            
            print(f"\n[{processed}/{total_events}] {event_name}")
            
            if iframe_url:
                m3u8_url = extract_m3u8_from_iframe(iframe_url)
                if m3u8_url:
                    stream['m3u8_url'] = m3u8_url
                    stream['m3u8_extracted_at'] = datetime.now().isoformat()
                    found += 1
                else:
                    stream['m3u8_url'] = None
                    stream['m3u8_error'] = "Could not extract m3u8 URL"
            else:
                stream['m3u8_url'] = None
                stream['m3u8_error'] = "No iframe URL provided"
                print(f"  ⚠ No iframe URL")
    
    print("\n" + "=" * 60)
    print(f"✓ Processing complete: {found}/{total_events} m3u8 URLs extracted")
    
    # Update metadata
    if 'metadata' in data:
        data['metadata']['m3u8_extraction_date'] = datetime.now().isoformat()
        data['metadata']['total_m3u8_found'] = found
        data['metadata']['total_processed'] = total_events
    
    return data

def save_events(data, filename=OUTPUT_FILE):
    """Save processed events to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved to {filename}")
        return True
    except Exception as e:
        print(f"\n✗ Error saving file: {e}")
        return False

def main():
    """Main execution function"""
    print("=" * 60)
    print("M3U8 URL Extractor - Starting...")
    print("=" * 60)
    
    # Load events
    data = load_events()
    if not data:
        print("✗ Failed to load events")
        exit(1)
    
    # Process and extract m3u8 URLs
    processed_data = process_events(data)
    if not processed_data:
        print("✗ Failed to process events")
        exit(1)
    
    # Save results
    if save_events(processed_data):
        print("=" * 60)
        print("✓ M3U8 extraction completed successfully!")
        print("=" * 60)
    else:
        print("✗ Failed to save results")
        exit(1)

if __name__ == "__main__":
    main()
