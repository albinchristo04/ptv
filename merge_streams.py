import json
import requests
from difflib import SequenceMatcher
from datetime import datetime
import re

# URLs for the JSON files
STREAMBTW_URL = "https://raw.githubusercontent.com/albinchristo04/arda/refs/heads/main/streambtw_data.json"
PTV_URL = "https://raw.githubusercontent.com/albinchristo04/ptv/refs/heads/main/events_with_m3u8.json"

def normalize_team_name(name):
    """Normalize team names for better matching"""
    # Remove common suffixes and variations
    replacements = {
        'republic': '',
        'rep.': '',
        'türkiye': 'turkey',
        'türki̇ye': 'turkey',
    }
    
    name = name.lower()
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    # Remove extra spaces
    name = ' '.join(name.split())
    return name.strip()

def extract_teams(title):
    """Extract team names from event title"""
    # Common patterns: "Team1 vs Team2", "Team1 vs. Team2", "Team1 at Team2"
    separators = [' vs. ', ' vs ', ' at ', ' v ']
    
    title_lower = title.lower()
    for sep in separators:
        if sep in title_lower:
            parts = title_lower.split(sep)
            if len(parts) == 2:
                team1 = normalize_team_name(parts[0].strip())
                team2 = normalize_team_name(parts[1].strip())
                return team1, team2
    
    return None, None

def teams_match(title1, title2):
    """Check if two titles refer to the same match"""
    teams1 = extract_teams(title1)
    teams2 = extract_teams(title2)
    
    if teams1[0] is None or teams2[0] is None:
        return False, 0.0
    
    # Check if teams match in same order
    if teams1 == teams2:
        return True, 1.0
    
    # Check if teams match in reverse order (home/away swap)
    if teams1 == (teams2[1], teams2[0]):
        return True, 0.95
    
    # Check if first team matches (partial match)
    team1_match = SequenceMatcher(None, teams1[0], teams2[0]).ratio()
    team2_match = SequenceMatcher(None, teams1[1], teams2[1]).ratio()
    
    # Check reverse
    team1_reverse = SequenceMatcher(None, teams1[0], teams2[1]).ratio()
    team2_reverse = SequenceMatcher(None, teams1[1], teams2[0]).ratio()
    
    forward_score = (team1_match + team2_match) / 2
    reverse_score = (team1_reverse + team2_reverse) / 2
    
    best_score = max(forward_score, reverse_score)
    
    # Consider it a match if both teams are at least 70% similar
    if best_score >= 0.7:
        return True, best_score
    
    # Check if at least one team name matches very well (90%+)
    if team1_match >= 0.9 or team2_match >= 0.9 or team1_reverse >= 0.9 or team2_reverse >= 0.9:
        return True, best_score
    
    return False, best_score

def fetch_json(url):
    """Fetch JSON data from URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_streambtw_events(data):
    """Extract events from streambtw_data.json"""
    events = []
    if data and 'items' in data:
        for item in data['items']:
            title = item.get('title', '')
            if title:  # Only add if title exists
                events.append({
                    'title': title,
                    'sport': item.get('sport', ''),
                    'link': item.get('link', ''),
                    'thumbnail': item.get('thumbnail', ''),
                    'm3u8_url': item.get('playable_link', {}).get('m3u8_url', ''),
                    'iframe_url': item.get('playable_link', {}).get('iframe_url', ''),
                    'headers': item.get('playable_link', {}).get('headers', {}),
                    'source': 'streambtw'
                })
    return events

def extract_ptv_events(data):
    """Extract events from events_with_m3u8.json"""
    events = []
    if data and 'events' in data and 'streams' in data['events']:
        for stream in data['events']['streams']:
            # Skip if it's a list (category with multiple streams)
            if isinstance(stream, dict) and 'streams' in stream:
                # This is a category, extract from nested streams
                for sub_stream in stream.get('streams', []):
                    title = sub_stream.get('name', '')
                    if title:  # Only add if title exists
                        events.append({
                            'title': title,
                            'category': stream.get('category', ''),
                            'tag': sub_stream.get('tag', ''),
                            'thumbnail': sub_stream.get('poster', ''),
                            'm3u8_url': sub_stream.get('m3u8_url', ''),
                            'iframe_url': sub_stream.get('iframe', ''),
                            'starts_at': sub_stream.get('starts_at', ''),
                            'ends_at': sub_stream.get('ends_at', ''),
                            'source': 'ptv'
                        })
            else:
                # Direct stream object
                title = stream.get('name', '')
                if title:
                    events.append({
                        'title': title,
                        'category': stream.get('category_name', ''),
                        'tag': stream.get('tag', ''),
                        'thumbnail': stream.get('poster', ''),
                        'm3u8_url': stream.get('m3u8_url', ''),
                        'iframe_url': stream.get('iframe', ''),
                        'starts_at': stream.get('starts_at', ''),
                        'ends_at': stream.get('ends_at', ''),
                        'source': 'ptv'
                    })
    return events

def merge_events(streambtw_events, ptv_events):
    """Merge events from both sources based on title similarity"""
    merged = []
    unmatched_streambtw = []
    unmatched_ptv = list(ptv_events)
    
    print("\n🔍 Starting matching process...")
    
    for sb_event in streambtw_events:
        best_match = None
        best_score = 0
        best_index = -1
        
        # Find best matching PTV event
        for i, ptv_event in enumerate(unmatched_ptv):
            is_match, score = teams_match(sb_event['title'], ptv_event['title'])
            
            if is_match and score > best_score:
                best_score = score
                best_match = ptv_event
                best_index = i
        
        if best_match:
            print(f"✓ Matched: '{sb_event['title']}' ↔ '{best_match['title']}' (score: {best_score:.2f})")
            
            # Merge the events
            merged_event = {
                'title': sb_event['title'],
                'alternative_title': best_match['title'],
                'match_confidence': round(best_score, 2),
                'sport': sb_event.get('sport', ''),
                'category': best_match.get('category', ''),
                'sources': {
                    'streambtw': {
                        'thumbnail': sb_event.get('thumbnail', ''),
                        'm3u8_url': sb_event.get('m3u8_url', ''),
                        'iframe_url': sb_event.get('iframe_url', ''),
                        'headers': sb_event.get('headers', {})
                    },
                    'ptv': {
                        'thumbnail': best_match.get('thumbnail', ''),
                        'm3u8_url': best_match.get('m3u8_url', ''),
                        'iframe_url': best_match.get('iframe_url', ''),
                        'tag': best_match.get('tag', ''),
                        'starts_at': best_match.get('starts_at', ''),
                        'ends_at': best_match.get('ends_at', '')
                    }
                },
                'all_m3u8_urls': [
                    url for url in [sb_event.get('m3u8_url'), best_match.get('m3u8_url')] 
                    if url
                ],
                'all_iframes': [
                    url for url in [sb_event.get('iframe_url'), best_match.get('iframe_url')] 
                    if url
                ]
            }
            merged.append(merged_event)
            unmatched_ptv.pop(best_index)
        else:
            print(f"✗ No match: '{sb_event['title']}'")
            unmatched_streambtw.append(sb_event)
    
    return merged, unmatched_streambtw, unmatched_ptv

def main():
    print("=" * 60)
    print("🔄 Stream Events Merger")
    print("=" * 60)
    
    print("\n📥 Fetching StreamBTW data...")
    streambtw_data = fetch_json(STREAMBTW_URL)
    
    print("📥 Fetching PTV data...")
    ptv_data = fetch_json(PTV_URL)
    
    if not streambtw_data or not ptv_data:
        print("❌ Failed to fetch data")
        return
    
    print("\n📊 Extracting events...")
    streambtw_events = extract_streambtw_events(streambtw_data)
    ptv_events = extract_ptv_events(ptv_data)
    
    print(f"   StreamBTW: {len(streambtw_events)} events")
    print(f"   PTV: {len(ptv_events)} events")
    
    print("\n🔀 Merging events...")
    merged, unmatched_sb, unmatched_ptv = merge_events(streambtw_events, ptv_events)
    
    print("\n" + "=" * 60)
    print(f"✅ Merged: {len(merged)} events")
    print(f"📌 Unmatched StreamBTW: {len(unmatched_sb)} events")
    print(f"📌 Unmatched PTV: {len(unmatched_ptv)} events")
    print("=" * 60)
    
    # Create output
    output = {
        'metadata': {
            'generated_at': datetime.utcnow().isoformat(),
            'total_merged': len(merged),
            'total_unmatched_streambtw': len(unmatched_sb),
            'total_unmatched_ptv': len(unmatched_ptv),
            'streambtw_source': STREAMBTW_URL,
            'ptv_source': PTV_URL
        },
        'merged_events': merged,
        'unmatched_streambtw': unmatched_sb,
        'unmatched_ptv': unmatched_ptv
    }
    
    # Save to file
    with open('merged_events.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n💾 Output saved to: merged_events.json")
    
    # Print sample merged events
    if merged:
        print("\n📋 Sample Merged Events:")
        for i, event in enumerate(merged[:5], 1):
            print(f"\n  {i}. {event['title']}")
            print(f"     Alternative: {event['alternative_title']}")
            print(f"     Confidence: {event['match_confidence']}")
            print(f"     M3U8 URLs: {len(event['all_m3u8_urls'])}")
            print(f"     Iframes: {len(event['all_iframes'])}")

if __name__ == "__main__":
    main()
