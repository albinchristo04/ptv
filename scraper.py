import json
import re
from datetime import datetime
import requests
from urllib.parse import unquote, urljoin
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
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': self.base_url
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
    
    def extract_m3u8_from_url(self, url):
        """Extract m3u8 URLs from player page"""
        m3u8_urls = []
        
        try:
            print(f"    Fetching: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            content = response.text
            
            # Multiple patterns to catch m3u8 URLs
            patterns = [
                r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                r'source["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'file["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'url["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
                r'atob\(["\']([^"\']+)["\']\)',  # Base64 encoded URLs
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Handle base64 encoded URLs
                    if 'atob' in pattern:
                        try:
                            import base64
                            decoded = base64.b64decode(match).decode('utf-8')
                            if '.m3u8' in decoded:
                                match = decoded
                        except:
                            continue
                    
                    # Clean and validate URL
                    match = unquote(match)
                    if match and '.m3u8' in match.lower():
                        # Make absolute URL if relative
                        if not match.startswith('http'):
                            match = urljoin(url, match)
                        
                        if match not in m3u8_urls:
                            m3u8_urls.append(match)
                            print(f"    ✓ Found M3U8: {match[:100]}...")
            
            # Look for embedded iframes that might contain the actual player
            iframe_patterns = [
                r'<iframe[^>]+src=["\']([^"\']+)["\']',
                r'iframe["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            ]
            
            for pattern in iframe_patterns:
                iframe_matches = re.findall(pattern, content, re.IGNORECASE)
                for iframe_url in iframe_matches:
                    if iframe_url and not iframe_url.startswith('#'):
                        # Make absolute URL
                        if not iframe_url.startswith('http'):
                            iframe_url = urljoin(url, iframe_url)
                        
                        # Recursively check iframe
                        if iframe_url != url:  # Avoid infinite loop
                            print(f"    → Found iframe: {iframe_url[:80]}...")
                            nested_m3u8 = self.extract_m3u8_from_url(iframe_url)
                            m3u8_urls.extend(nested_m3u8)
            
            return list(set(m3u8_urls))  # Remove duplicates
            
        except requests.Timeout:
            print(f"    ⚠ Timeout fetching {url}")
            return []
        except Exception as e:
            print(f"    ✗ Error: {e}")
            return []
    
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
                time.sleep(0.5)
            
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
        print(f"\n✓ Successfully extracted M3U8 URLs!")
    else:
        print(f"\n⚠ No M3U8 URLs found - checking sample event...")
        if data['events']:
            sample = data['events'][0]
            if 'player_urls' in sample:
                print(f"\nSample URLs to check manually:")
                for player, url in sample['player_urls'].items():
                    print(f"  {player}: {url}")

if __name__ == "__main__":
    main()
