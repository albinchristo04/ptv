import json
import re
from datetime import datetime
import requests
from urllib.parse import unquote, urljoin
import time
import subprocess
import sys

class EventScraper:
    def __init__(self):
        self.base_url = "https://rereyano.ru"
        self.player_types = {
            "Cartel": 1,
            "hoca": 2,
            "Caster": 3,
            "WIGI": 4
        }
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
    def extract_events(self):
        """Extract event details from main page"""
        try:
            print("Fetching main page...")
            response = self.session.get(self.base_url, timeout=15)
            response.raise_for_status()
            content = response.text
            
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
            
            print(f"Found {len(events)} events\n")
            return events
        except Exception as e:
            print(f"Error extracting events: {e}")
            return []
    
    def extract_m3u8_with_playwright(self, url):
        """Extract m3u8 using Playwright for JavaScript execution"""
        m3u8_urls = []
        
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()
                
                # Track network requests
                def handle_route(route, request):
                    url = request.url
                    if '.m3u8' in url.lower():
                        m3u8_urls.append(url)
                    route.continue_()
                
                page.route("**/*", handle_route)
                
                # Navigate and wait
                page.goto(url, wait_until="networkidle", timeout=20000)
                time.sleep(3)
                
                # Try to trigger video play
                try:
                    page.evaluate("document.querySelectorAll('video').forEach(v => v.play().catch(()=>{}))")
                    time.sleep(2)
                except:
                    pass
                
                # Check page content
                content = page.content()
                m3u8_patterns = [
                    r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
                ]
                for pattern in m3u8_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    m3u8_urls.extend(matches)
                
                browser.close()
                
        except ImportError:
            print("    ⚠ Playwright not available, using requests fallback")
            return self.extract_m3u8_with_requests(url)
        except Exception as e:
            print(f"    ⚠ Playwright error: {e}")
            return []
        
        return list(set(m3u8_urls))
    
    def extract_m3u8_with_requests(self, url):
        """Extract m3u8 URLs using requests (faster fallback)"""
        m3u8_urls = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.base_url,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            content = response.text
            
            # Extract embedded iframe
            iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
            iframe_matches = re.findall(iframe_pattern, content, re.IGNORECASE)
            
            if iframe_matches:
                iframe_url = iframe_matches[0]
                if not iframe_url.startswith('http'):
                    iframe_url = urljoin(url, iframe_url)
                print(f"    → Found iframe: {iframe_url[:80]}...")
                
                # Fetch iframe with proper referer
                iframe_headers = headers.copy()
                iframe_headers['Referer'] = url
                iframe_response = self.session.get(iframe_url, headers=iframe_headers, timeout=15)
                content = iframe_response.text
            
            # Multiple patterns to catch m3u8 URLs
            patterns = [
                r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                r'source["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'file["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    match = unquote(match)
                    if match and '.m3u8' in match.lower():
                        if not match.startswith('http'):
                            match = urljoin(iframe_url if iframe_matches else url, match)
                        
                        if match not in m3u8_urls:
                            m3u8_urls.append(match)
            
            return m3u8_urls
            
        except Exception as e:
            print(f"    ✗ Error: {e}")
            return []
    
    def extract_m3u8_from_url(self, url):
        """Main extraction method - tries Playwright first, falls back to requests"""
        print(f"    Fetching: {url}")
        
        # Try with Playwright if available (handles JS)
        try:
            import playwright
            m3u8_urls = self.extract_m3u8_with_playwright(url)
            if m3u8_urls:
                for m3u8 in m3u8_urls:
                    print(f"    ✓ Found M3U8: {m3u8[:100]}...")
                return m3u8_urls
        except ImportError:
            pass
        
        # Fallback to requests
        m3u8_urls = self.extract_m3u8_with_requests(url)
        if m3u8_urls:
            for m3u8 in m3u8_urls:
                print(f"    ✓ Found M3U8: {m3u8[:100]}...")
        
        return m3u8_urls
    
    def scrape_all(self):
        """Main scraping function"""
        result = {
            "scrape_time": datetime.now().isoformat(),
            "events": []
        }
        
        print("="*60)
        print("EXTRACTING EVENTS")
        print("="*60)
        events = self.extract_events()
        
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
                m3u8_urls = self.extract_m3u8_from_url(player_url)
                
                event["streams"][player_name] = {
                    "iframe_url": player_url,
                    "m3u8_urls": m3u8_urls,
                    "extracted_at": datetime.now().isoformat()
                }
                
                if m3u8_urls:
                    print(f"    → Total M3U8s: {len(m3u8_urls)}")
                else:
                    print(f"    ⚠ No M3U8 found")
                
                # Small delay between requests
                time.sleep(1)
            
            result["events"].append(event)
        
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
        print(f"\n✓ Successfully extracted {total_m3u8} M3U8 URLs!")
    else:
        print(f"\n⚠ No M3U8 URLs found")

if __name__ == "__main__":
    main()
