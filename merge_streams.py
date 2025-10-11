import json
import requests
from difflib import SequenceMatcher
from datetime import datetime

# URLs for the JSON files
STREAMBTW_URL = "https://raw.githubusercontent.com/albinchristo04/arda/refs/heads/main/streambtw_data.json"
PTV_URL = "https://raw.githubusercontent.com/albinchristo04/ptv/refs/heads/main/events_with_m3u8.json"

def similarity(a, b):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def normalize_title(title):
    """Normalize title for better matching"""
    # Remove common words and normalize
    common_words = ['vs', 'vs.', 'v', 'at', 'the']
    words = title.lower().split()
    normalized = ' '.join([w for w in words if w not in common_words])
    return normalized

def fetch_json(url):
    """Fetch JSON data from URL"""
    try:
        response = requests.get(url)
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
            events.append({
                'title': item.get('title', ''),
                'sport': item.get('sport', ''),
                'link': item.get('link', ''),
                'thumbnail': item.get('thumbnail', ''),
                'm3u8_url': item.get('playable_link', {}).get('m3u8_url', ''),
                'iframe_url': item.get('playable_link', {}).get('iframe_url', ''),
                'source': 'streambtw'
            })
    return events

def extract_ptv_events(data):
    """Extract events from events_with_m3u8.json"""
    events = []
    if data and 'events' in data and 'streams' in data['events']:
        for stream in data['events']['streams']:
            events.append({
                'title': stream.get('name', ''),
                'category': stream.get('category_name', ''),
                'tag': stream.get('tag', ''),
                'thumbnail': stream.get('poster', ''),
                'm3u8_url': stream.get('m3u8_url', ''),
                'iframe_url': stream.get('iframe', ''),
                'source': 'ptv'
            })
    return events

def merge_events(streambtw_events, ptv_events, threshold=0.7):
    """
    Merge events from both sources based on title similarity
    threshold: minimum similarity score to consider a match (0-1)
    """
    merged = []
    unmatched_streambtw = []
    unmatched_ptv = list(ptv_events)
    
    for sb_event in streambtw_events:
        best_match = None
        best_score = 0
        best_index = -1
        
        # Find best matching PTV event
        for i, ptv_event in enumerate(unmatched_ptv):
            score = similarity(
                normalize_title(sb_event['title']),
                normalize_title(ptv_event['title'])
            )
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = ptv_event
                best_index = i
        
        if best_match:
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
                        'iframe_url': sb_event.get('iframe_url', '')
                    },
                    'ptv': {
                        'thumbnail': best_match.get('thumbnail', ''),
                        'm3u8_url': best_match.get('m3u8_url', ''),
                        'iframe_url': best_match.get('iframe_url', ''),
                        'tag': best_match.get('tag', '')
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
            unmatched_streambtw.append(sb_event)
    
    return merged, unmatched_streambtw, unmatched_ptv

def main():
    print("Fetching StreamBTW data...")
    streambtw_data = fetch_json(STREAMBTW_URL)
    
    print("Fetching PTV data...")
    ptv_data = fetch_json(PTV_URL)
    
    if not streambtw_data or not ptv_data:
        print("Failed to fetch data")
        return
    
    print("Extracting events...")
    streambtw_events = extract_streambtw_events(streambtw_data)
    ptv_events = extract_ptv_events(ptv_data)
    
    print(f"Found {len(streambtw_events)} StreamBTW events")
    print(f"Found {len(ptv_events)} PTV events")
    
    print("\nMerging events...")
    merged, unmatched_sb, unmatched_ptv = merge_events(streambtw_events, ptv_events)
    
    print(f"\nMerged {len(merged)} events")
    print(f"Unmatched StreamBTW events: {len(unmatched_sb)}")
    print(f"Unmatched PTV events: {len(unmatched_ptv)}")
    
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
    
    print("\n✅ Merged data saved to merged_events.json")
    
    # Print some examples
    if merged:
        print("\n📊 Sample merged events:")
        for event in merged[:3]:
            print(f"\n  Title: {event['title']}")
            print(f"  Confidence: {event['match_confidence']}")
            print(f"  M3U8 URLs: {len(event['all_m3u8_urls'])}")
            print(f"  Iframes: {len(event['all_iframes'])}")

if __name__ == "__main__":
    main()
