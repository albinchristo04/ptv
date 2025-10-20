import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import time

class EventScraper:
    def __init__(self):
        self.base_url = "https://rereyano.ru"
        self.player_sources = {
            "Cartel": f"{self.base_url}/player/1/1",
            "hoca": f"{self.base_url}/player/2/1",
            "Caster": f"{self.base_url}/player/3/1",
            "WIGI": f"{self.base_url}/player/4/1"
        }
        
    def extract_events(self, page):
        """Extract event details from main page"""
        try:
            page.goto(self.base_url, wait_until="networkidle", timeout=30000)
            content = page.content()
            
            events = []
            lines = content.split('\n')
            
            for line in lines:
                # Match event pattern: date (time) competition : teams (channels)
                pattern = r'(\d{2}-\d{2}-\d{4})\s*\((\d{2}:\d{2})\)\s*([^:]+):\s*([^(]+)\(([^)]+)\)'
                match = re.search(pattern, line)
                
                if match:
                    date_str, time_str, competition, teams, channels = match.groups()
                    
                    # Extract channel codes
                    channel_codes = re.findall(r'CH\d+\w+', channels)
                    
                    event = {
                        "date": date_str.strip(),
                        "time": time_str.strip(),
                        "competition": competition.strip(),
                        "teams": teams.strip(),
                        "channels": channel_codes,
                        "timestamp": f"{date_str} {time_str}",
                        "extracted_at": datetime.now().isoformat()
                    }
                    events.append(event)
            
            return events
        except Exception as e:
            print(f"Error extracting events: {e}")
            return []
    
    def extract_m3u8_from_iframe(self, page, iframe_url):
        """Extract m3u8 URL from iframe using network monitoring"""
        m3u8_urls = []
        
        def handle_response(response):
            """Capture m3u8 URLs from network responses"""
            url = response.url
            if '.m3u8' in url or 'm3u8' in url:
                m3u8_urls.append(url)
        
        try:
            # Listen to network responses
            page.on("response", handle_response)
            
            # Navigate to iframe URL
            page.goto(iframe_url, wait_until="networkidle", timeout=30000)
            
            # Wait for video player to load and start streaming
            time.sleep(5)
            
            # Try to find m3u8 in page content as fallback
            content = page.content()
            m3u8_matches = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', content)
            m3u8_urls.extend(m3u8_matches)
            
            # Remove duplicates
            m3u8_urls = list(set(m3u8_urls))
            
            return m3u8_urls
        except Exception as e:
            print(f"Error extracting m3u8 from {iframe_url}: {e}")
            return []
    
    def scrape_all(self):
        """Main scraping function"""
        result = {
            "scrape_time": datetime.now().isoformat(),
            "events": [],
            "player_sources": {}
        }
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            
            # Extract events
            print("Extracting events...")
            events = self.extract_events(page)
            result["events"] = events
            print(f"Found {len(events)} events")
            
            # Extract m3u8 from each player source
            print("\nExtracting m3u8 URLs from player sources...")
            for source_name, iframe_url in self.player_sources.items():
                print(f"Processing {source_name}...")
                m3u8_urls = self.extract_m3u8_from_iframe(page, iframe_url)
                
                result["player_sources"][source_name] = {
                    "iframe_url": iframe_url,
                    "m3u8_urls": m3u8_urls,
                    "extracted_at": datetime.now().isoformat()
                }
                print(f"  Found {len(m3u8_urls)} m3u8 URL(s)")
            
            browser.close()
        
        return result
    
    def save_to_json(self, data, filename="events_data.json"):
        """Save scraped data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nData saved to {filename}")

def main():
    scraper = EventScraper()
    data = scraper.scrape_all()
    scraper.save_to_json(data)
    
    # Print summary
    print("\n" + "="*50)
    print("SCRAPING SUMMARY")
    print("="*50)
    print(f"Events found: {len(data['events'])}")
    print(f"Player sources processed: {len(data['player_sources'])}")
    
    for source, info in data['player_sources'].items():
        print(f"\n{source}:")
        print(f"  Iframe: {info['iframe_url']}")
        print(f"  M3U8 URLs found: {len(info['m3u8_urls'])}")
        for url in info['m3u8_urls']:
            print(f"    - {url}")

if __name__ == "__main__":
    main()
