#!/usr/bin/env python3
"""
Events Extractor - Fetch and store events from ppv.to API
"""

import requests
import json
import os
from datetime import datetime

# Configuration
API_URL = "https://old.ppv.to/api/streams"
OUTPUT_FILE = "events.json"
TIMEOUT = 10

def fetch_events(api_url):
    try:
        print(f"Fetching data from {api_url}...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://ppv.to/",
            "Origin": "https://ppv.to",
            "Connection": "keep-alive",
        }

        session = requests.Session()
        response = session.get(api_url, headers=headers, timeout=TIMEOUT)

        response.raise_for_status()

        data = response.json()

        print(f"✓ Successfully fetched data")
        return data

    except Exception as e:
        print(f"✗ Error fetching data: {e}")
        return None
        
        

    except json.JSONDecodeError as e:
        print(f"✗ Error parsing JSON: {e}")
        return None

def save_to_json(data, filename=OUTPUT_FILE):
    """
    Save the events data to a JSON file
    
    Args:
        data (dict): The data to save
        filename (str): Output filename
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ Data saved to {filename}")
        return True
    except Exception as e:
        print(f"✗ Error saving to file: {e}")
        return False

def main():
    """Main execution function"""
    print("=" * 50)
    print("Events Extractor - Starting...")
    print("=" * 50)
    
    # Fetch events from API
    events_data = fetch_events(API_URL)
    
    if events_data:
        # Prepare output with metadata
        output_data = {
            "metadata": {
                "fetched_at": datetime.now().isoformat(),
                "source": API_URL,
                "total_events": len(events_data) if isinstance(events_data, list) else None
            },
            "events": events_data
        }
        
        # Save to JSON file
        if save_to_json(output_data):
            # Print summary
            if isinstance(events_data, list):
                print(f"\n📊 Summary: {len(events_data)} events extracted")
            elif isinstance(events_data, dict):
                print(f"\n📊 Data keys: {', '.join(events_data.keys())}")
            print("=" * 50)
            print("✓ Process completed successfully!")
        else:
            print("=" * 50)
            print("✗ Failed to save data")
            exit(1)
    else:
        print("=" * 50)
        print("✗ Failed to fetch events")
        exit(1)

if __name__ == "__main__":
    main()
