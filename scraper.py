import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time

class EventScraper:
    def __init__(self):
        self.base_url = "https://rereyano.ru"
        self.player_types = {
            "Cartel": 1,
            "hoca": 2,
            "Caster": 3,
            "WIGI": 4
        }
        
    def extract_events(self, page):
        """Extract event details from main page"""
        try:
            print("Loading main page...")
            page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            content = page.content()
            
            events = []
            lines = content.split('\n')
            
            for line in lines:
                # Match event pattern: date (time) competition : teams (channels)
                pattern = r'(\d{2}-\d{2}-\d{4})\s*\((\d{2}:\d{2})\)\s*([^:]+):\s*([^(]+)\(([^)]+)\)'
                match = re.search(pattern, line)
                
                if match:
                    date_str, time_str, competition, teams, channels_str = match.groups()
                    
                    # Extract channel codes with numbers
                    channel_matches = re.findall(r'CH(\d+)(\w+)', channels_str)
                    channels = []
                    for ch_num, ch_lang in channel_matches:
                        channels.append({
                            "code": f"CH{ch_num}{ch_lang}",
                            "number": ch_num,
                            "language": ch_lang
                        })
                    
                    event = {
                        "date": date_str.strip(),
                        "time": time_str.strip(),
                        "competition": competition.strip(),
                        "teams": teams.strip(),
                        "channels": channels,
                        "timestamp": f"{date_str} {time_str}",
                        "extracted_at": datetime.now().isoformat(),
                        "player_urls": {}
                    }
                    
                    # Generate player URLs for each channel
                    if channels:
                        main_channel = channels[0]["number"]
                        for player_name, player_id in self.player_types.items():
                            event["player_urls"][player_name] = f"{self.base_url}/player/{player_id}/{main_channel}"
                    
                    events.append(event)
            
            return events
        except Exception as e:
            print(f"Error extracting events: {e}")
            return []
    
    def extract_m3u8_from_iframe(self, page, iframe_url, event_info=""):
        """Extract m3u8 URL from iframe using network monitoring"""
        m3u8_urls = []
        
        def handle_request(request):
            """Capture m3u8 URLs from network requests"""
            url = request.url
            if '.m3u8' in url.lower():
                if url not in m3u8_urls:
                    m3u8_urls.append(url)
                    print(f"    ✓ Found M3U8: {url[:80]}...")
        
        def handle_response(response):
            """Capture m3u8 URLs from network responses"""
            url = response.url
            if '.m3u8' in url.lower():
                if url not in m3u8_urls:
                    m3u8_urls.append(url)
                    print(f"    ✓ Found M3U8: {url[:80]}...")
        
        try:
            print(f"  Loading: {iframe_url}")
            
            # Listen to both requests and responses
            page.on("request", handle_request)
            page.on("response", handle_response)
            
            # Navigate to iframe URL
            page.goto(iframe_url, wait_until="networkidle", timeout=30000)
            
            # Wait for video player to load
            time.sleep(8)
            
            # Try to find video element and trigger play
            try:
                page.evaluate("""
                    () => {
                        const videos = document.querySelectorAll('video');
                        videos.forEach(v => {
                            v.play().catch(() => {});
                        });
                    }
                """)
                time.sleep(2)
            except:
                pass
            
            # Search in page content and scripts
            content = page.content()
            scripts = page.evaluate("() => Array.from(document.scripts).map(s => s.textContent)")
            all_text = content + "\n" + "\n".join(scripts)
            
            # Find m3u8 URLs in content
            m3u8_patterns = [
                r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
                r'"(https?://[^"]+\.m3u8[^"]*)"',
                r"'(https?://[^']+\.m3u8[^']*)'",
                r'src[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'source[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'file[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                for match in matches:
                    if match and match not in m3u8_urls:
                        m3u8_urls.append(match)
                        print(f"    ✓ Found M3U8 in content: {match[:80]}...")
            
            # Remove listeners
            page.remove_listener("request", handle_request)
            page.remove_listener("response", handle_response)
            
            return m3u8_urls
        except PlaywrightTimeout:
            print(f"    ⚠ Timeout loading {iframe_url}")
            return m3u8_urls
        except Exception as e:
            print(f"    ✗ Error: {e}")
            return m3u8_urls
    
    def scrape_all(self):
        """Main scraping function"""
        result = {
            "scrape_time": datetime.now().isoformat(),
            "events": []
        }
        
        with sync_playwright() as p:
            print("Launching browser...")
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                java_script_enabled=True
            )
            
            page = context.new_page()
            
            # Extract events
            print("\n" + "="*60)
            print("EXTRACTING EVENTS")
            print("="*60)
            events = self.extract_events(page)
            print(f"Found {len(events)} events\n")
            
            # Process each event and extract m3u8 for its channels
            print("="*60)
            print("EXTRACTING M3U8 URLs")
            print("="*60)
            
            for idx, event in enumerate(events, 1):
                print(f"\n[{idx}/{len(events)}] {event['teams']} ({event['time']})")
                
                if not event['channels']:
                    print("  ⚠ No channels found for this event")
                    continue
                
                event["streams"] = {}
                
                # Extract m3u8 for each player type
                for player_name, player_url in event["player_urls"].items():
                    print(f"\n  {player_name}:")
                    m3u8_urls = self.extract_m3u8_from_iframe(
                        page, 
                        player_url,
                        f"{event['teams']} - {player_name}"
                    )
                    
                    event["streams"][player_name] = {
                        "iframe_url": player_url,
                        "m3u8_urls": m3u8_urls,
                        "extracted_at": datetime.now().isoformat()
                    }
                    
                    if m3u8_urls:
                        print(f"    → Total M3U8s found: {len(m3u8_urls)}")
                    else:
                        print(f"    ⚠ No M3U8 found")
                    
                    # Small delay between requests
                    time.sleep(2)
                
                result["events"].append(event)
            
            browser.close()
        
        return result
    
    def save_to_json(self, data, filename="events_data.json"):
        """Save scraped data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n{'='*60}")
        print(f"Data saved to {filename}")
        print(f"{'='*60}")

def main():
    scraper = EventScraper()
    data = scraper.scrape_all()
    scraper.save_to_json(data)
    
    # Print summary
    print("\n" + "="*60)
    print("SCRAPING SUMMARY")
    print("="*60)
    print(f"Total events: {len(data['events'])}")
    
    total_streams = 0
    total_m3u8 = 0
    
    for event in data['events']:
        if 'streams' in event:
            for player, stream_info in event['streams'].items():
                total_streams += 1
                total_m3u8 += len(stream_info['m3u8_urls'])
    
    print(f"Total streams checked: {total_streams}")
    print(f"Total M3U8 URLs found: {total_m3u8}")
    
    if total_m3u8 > 0:
        print(f"\n✓ Successfully extracted M3U8 URLs!")
    else:
        print(f"\n⚠ No M3U8 URLs found - the streams might be protected or unavailable")

if __name__ == "__main__":
    main()
