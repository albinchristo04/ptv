import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def extract_channel_number(channel_str):
    """Extract the numeric part from channel string like 'CH146pt'"""
    match = re.search(r'CH(\d+)', channel_str)
    return match.group(1) if match else None

def parse_events(html_content):
    """Parse events from HTML content"""
    events = []
    
    # Split by newlines and process each line
    lines = html_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Pattern: 23-11-2025 (12:00) League : Team1 - Team2 (CH###xx) (CH###xx)
        pattern = r'(\d{2}-\d{2}-\d{4})\s+\((\d{2}:\d{2})\)\s+(.+?)\s*:\s+(.+?)\s+(-)\s+(.+?)\s+((?:\(CH\d+\w+\)\s*)+)'
        
        match = re.match(pattern, line)
        if match:
            date = match.group(1)
            time = match.group(2)
            league = match.group(3).strip()
            team1 = match.group(4).strip()
            team2 = match.group(6).strip()
            channels_str = match.group(7).strip()
            
            # Extract all channel numbers
            channels = re.findall(r'CH(\d+)(\w+)', channels_str)
            
            # Create iframes for each channel
            iframes = []
            for channel_num, lang_code in channels:
                iframes.append({
                    "player1": f"https://bolaloca.my/player/2/{channel_num}",
                    "player2": f"https://bolaloca.my/player/3/{channel_num}",
                    "player3": f"https://bolaloca.my/player/4/{channel_num}",
                    "channel": f"CH{channel_num}{lang_code}"
                })
            
            event = {
                "date": date,
                "time": time,
                "league": league,
                "team1": team1,
                "team2": team2,
                "channels": channels,
                "iframes": iframes
            }
            events.append(event)
    
    return events

def scrape_website(url):
    """Scrape the website and extract events"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get all text content
        text_content = soup.get_text()
        
        # Parse events from text
        events = parse_events(text_content)
        
        return events
    
    except Exception as e:
        print(f"Error scraping website: {e}")
        return None

def save_to_json(events, filename='reyevents.json'):
    """Save events to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"✓ Successfully saved {len(events)} events to {filename}")
        return True
    except Exception as e:
        print(f"Error saving to JSON: {e}")
        return False

def main():
    url = 'https://rereyano.ru/'
    
    print(f"Scraping {url}...")
    events = scrape_website(url)
    
    if events:
        print(f"Found {len(events)} events")
        
        # Display first event as preview
        if events:
            print("\nPreview of first event:")
            print(json.dumps(events[0], indent=2, ensure_ascii=False))
        
        # Save to JSON
        save_to_json(events)
    else:
        print("No events found or error occurred")

if __name__ == "__main__":
    main()
