#!/usr/bin/env python3
"""
M3U8 Stream Extractor - Extract m3u8 URLs from embednow.top with rate limiting handling
"""
import requests
import json
import re
import time
import base64
from datetime import datetime
from typing import Optional, Dict, List
import random

# Configuration
INPUT_FILE = "events.json"
OUTPUT_FILE = "events_with_m3u8.json"
BASE_DELAY = 2  # Base delay between requests in seconds
MAX_RETRIES = 3  # Maximum number of retries per request
TIMEOUT = 15  # Request timeout in seconds
JITTER_RANGE = (0.5, 1.5)  # Random jitter multiplier range

class RateLimitHandler:
    """Handles rate limiting with exponential backoff"""
    
    def __init__(self, base_delay=BASE_DELAY, max_retries=MAX_RETRIES):
        self.base_delay = base_delay
        self.max_retries = max_retries
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
        
    def calculate_delay(self, retry_count: int, is_rate_limited: bool = False) -> float:
        """
        Calculate delay with exponential backoff and jitter
        
        Args:
            retry_count: Current retry attempt number
            is_rate_limited: Whether this is due to rate limiting
            
        Returns:
            Delay in seconds
        """
        if is_rate_limited:
            # Longer delays for rate limiting
            base = self.base_delay * (3 ** retry_count)
        else:
            # Standard exponential backoff
            base = self.base_delay * (2 ** retry_count)
        
        # Add random jitter to avoid thundering herd
        jitter = random.uniform(*JITTER_RANGE)
        delay = base * jitter
        
        # Cap maximum delay at 60 seconds
        return min(delay, 60)
    
    def wait(self, retry_count: int = 0, is_rate_limited: bool = False):
        """Wait with calculated delay"""
        delay = self.calculate_delay(retry_count, is_rate_limited)
        if delay > 0:
            print(f"  ⏳ Waiting {delay:.2f}s before next request...")
            time.sleep(delay)

def fetch_iframe_with_retry(url: str, rate_handler: RateLimitHandler) -> Optional[str]:
    """
    Fetch iframe content with retry logic and rate limiting handling
    
    Args:
        url: URL to fetch
        rate_handler: RateLimitHandler instance
        
    Returns:
        Response text or None if all retries failed
    """
    rate_handler.request_count += 1
    
    for attempt in range(rate_handler.max_retries):
        try:
            # Add delay before request (except first attempt)
            if attempt > 0:
                is_rate_limited = attempt > 0  # Assume rate limited after first failure
                rate_handler.wait(attempt, is_rate_limited)
            elif rate_handler.request_count > 1:
                # Base delay between different URLs
                rate_handler.wait(0, False)
            
            print(f"  → Attempt {attempt + 1}/{rate_handler.max_retries}: Fetching {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            
            # Handle different status codes
            if response.status_code == 200:
                rate_handler.success_count += 1
                print(f"  ✓ Success (200 OK)")
                return response.text
                
            elif response.status_code == 429:
                # Rate limited - use longer backoff
                rate_handler.failure_count += 1
                print(f"  ⚠ Rate limited (429) - backing off...")
                if attempt < rate_handler.max_retries - 1:
                    rate_handler.wait(attempt + 1, is_rate_limited=True)
                continue
                
            elif response.status_code == 403:
                # Forbidden - might be blocked, no point retrying
                rate_handler.failure_count += 1
                print(f"  ✗ Access forbidden (403) - skipping retries")
                return None
                
            else:
                rate_handler.failure_count += 1
                print(f"  ✗ Unexpected status code: {response.status_code}")
                if attempt < rate_handler.max_retries - 1:
                    continue
                    
        except requests.exceptions.Timeout:
            print(f"  ✗ Request timeout")
            if attempt < rate_handler.max_retries - 1:
                rate_handler.wait(attempt, False)
                continue
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Request error: {e}")
            if attempt < rate_handler.max_retries - 1:
                rate_handler.wait(attempt, False)
                continue
    
    # All retries exhausted
    rate_handler.failure_count += 1
    print(f"  ✗ All {rate_handler.max_retries} attempts failed")
    return None

def extract_m3u8_from_html(html_content: str) -> Optional[str]:
    """
    Extract base64-encoded m3u8 URL from HTML content
    
    Args:
        html_content: HTML content to parse
        
    Returns:
        Decoded m3u8 URL or None if not found
    """
    try:
        # Look for base64 encoded m3u8 pattern
        pattern = r'atob\("([A-Za-z0-9+/=]+)"\)'
        matches = re.findall(pattern, html_content)
        
        for match in matches:
            try:
                decoded = base64.b64decode(match).decode('utf-8')
                if '.m3u8' in decoded and decoded.startswith('http'):
                    return decoded
            except Exception:
                continue
                
        # Alternative pattern - direct m3u8 URLs
        pattern2 = r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)'
        matches2 = re.findall(pattern2, html_content)
        if matches2:
            return matches2[0]
            
    except Exception as e:
        print(f"  ✗ Error parsing HTML: {e}")
    
    return None

def process_events(events: List[Dict], rate_handler: RateLimitHandler) -> List[Dict]:
    """
    Process all events and extract m3u8 URLs
    
    Args:
        events: List of event dictionaries
        rate_handler: RateLimitHandler instance
        
    Returns:
        Updated events list with m3u8 URLs
    """
    updated_events = []
    current_category = None
    
    for i, event in enumerate(events, 1):
        # Print category header when it changes
        if event.get('category') != current_category:
            current_category = event.get('category')
            print(f"\n📁 Category: {current_category}")
        
        print(f"[{i}/{len(events)}] {event.get('name', 'Unknown Event')}")
        
        # Create updated event copy
        updated_event = event.copy()
        
        # Skip if no embed URL
        if 'embed' not in event:
            print("  ⚠ No embed URL found - skipping")
            updated_events.append(updated_event)
            continue
        
        embed_url = event['embed']
        
        # Fetch iframe content with retry logic
        html_content = fetch_iframe_with_retry(embed_url, rate_handler)
        
        if html_content:
            # Extract m3u8 URL
            m3u8_url = extract_m3u8_from_html(html_content)
            
            if m3u8_url:
                print(f"  ✓ Found m3u8: {m3u8_url[:60]}...")
                updated_event['m3u8_url'] = m3u8_url
                updated_event['m3u8_extracted_at'] = datetime.now().isoformat()
            else:
                print(f"  ⚠ No m3u8 URL found in response")
        
        updated_events.append(updated_event)
    
    return updated_events

def main():
    """Main execution function"""
    print("=" * 60)
    print("M3U8 Stream Extractor - Starting...")
    print("=" * 60)
    
    # Load events from JSON
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Debug: Print data structure
        print(f"📋 Data type: {type(data).__name__}")
        
        # Handle different JSON structures
        events = None
        if isinstance(data, dict):
            # Check for 'events' key
            if 'events' in data:
                events = data['events']
                print(f"📋 Found 'events' key, type: {type(events).__name__}")
            else:
                # Maybe the dict itself contains the events
                print(f"📋 Available keys: {list(data.keys())[:10]}")
                # Check if data has category/name structure (it might be a single event dict)
                if 'category' in data or 'name' in data:
                    events = [data]  # Wrap single event in list
                else:
                    print(f"✗ No 'events' key found in JSON")
                    print(f"  Available keys: {', '.join(list(data.keys())[:10])}")
                    exit(1)
        elif isinstance(data, list):
            events = data
            print(f"📋 Data is a list with {len(data)} items")
        else:
            print(f"✗ Unexpected data format: {type(data).__name__}")
            exit(1)
        
        # Validate events structure
        if not events:
            print(f"✗ No events found in {INPUT_FILE}")
            exit(1)
        
        # Check if events is a list
        if not isinstance(events, list):
            print(f"✗ Events must be a list, got {type(events).__name__}")
            print(f"  Events value: {str(events)[:200]}...")
            exit(1)
        
        # Sample check for event structure
        if events:
            first_item = events[0]
            print(f"📋 First item type: {type(first_item).__name__}")
            if isinstance(first_item, str):
                print(f"✗ Events appear to be strings instead of objects")
                print(f"  First event: {first_item[:100]}...")
                print(f"  Please check the structure of {INPUT_FILE}")
                exit(1)
            elif isinstance(first_item, dict):
                print(f"📋 First event keys: {list(first_item.keys())[:5]}")
        
        print(f"✓ Loaded {len(events)} events from {INPUT_FILE}")
        
    except FileNotFoundError:
        print(f"✗ Error: {INPUT_FILE} not found!")
        print("  Please run extract_events.py first.")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Error parsing {INPUT_FILE}: {e}")
        exit(1)
    
    # Initialize rate limit handler
    rate_handler = RateLimitHandler(base_delay=BASE_DELAY, max_retries=MAX_RETRIES)
    
    # Process events
    print(f"\n🔍 Processing {len(events)} events...")
    print(f"⚙️  Settings: Base delay={BASE_DELAY}s, Max retries={MAX_RETRIES}\n")
    
    start_time = time.time()
    updated_events = process_events(events, rate_handler)
    elapsed_time = time.time() - start_time
    
    # Count successful extractions
    m3u8_count = sum(1 for e in updated_events if 'm3u8_url' in e)
    
    # Prepare output with metadata
    output_data = {
        "metadata": {
            "extracted_at": datetime.now().isoformat(),
            "source_file": INPUT_FILE,
            "total_events": len(updated_events),
            "events_with_m3u8": m3u8_count,
            "success_rate": f"{(m3u8_count / len(updated_events) * 100):.1f}%",
            "extraction_stats": {
                "total_requests": rate_handler.request_count,
                "successful_requests": rate_handler.success_count,
                "failed_requests": rate_handler.failure_count,
                "elapsed_time_seconds": round(elapsed_time, 2)
            }
        },
        "events": updated_events
    }
    
    # Save to JSON
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\n{'=' * 60}")
        print(f"✓ Saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"\n{'=' * 60}")
        print(f"✗ Error saving file: {e}")
        exit(1)
    
    # Print summary
    print(f"{'=' * 60}")
    print(f"✓ Processing complete: {m3u8_count}/{len(updated_events)} m3u8 URLs extracted")
    print(f"📊 Stats:")
    print(f"   • Total requests: {rate_handler.request_count}")
    print(f"   • Successful: {rate_handler.success_count}")
    print(f"   • Failed: {rate_handler.failure_count}")
    print(f"   • Success rate: {(m3u8_count / len(updated_events) * 100):.1f}%")
    print(f"   • Elapsed time: {elapsed_time:.1f}s")
    print(f"{'=' * 60}")
    print("✓ M3U8 extraction completed successfully!")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
