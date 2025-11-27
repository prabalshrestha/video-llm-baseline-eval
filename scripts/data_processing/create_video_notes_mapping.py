"""
Create mapping between downloaded videos and their Community Notes.
This makes it easy to match videos with their human-written notes for evaluation.
"""

import pandas as pd
import json
from pathlib import Path

def create_mapping():
    """Create a CSV mapping videos to their Community Notes."""
    
    # Load downloaded videos metadata
    videos_dir = Path("data/videos")
    metadata_file = videos_dir / "downloaded_videos.json"
    
    with open(metadata_file, 'r') as f:
        videos = json.load(f)
    
    # Load Community Notes
    notes_file = Path("data/filtered/likely_video_notes.csv")
    notes_df = pd.read_csv(notes_file)
    
    # Create mapping
    mapping = []
    
    for video in videos:
        if video['downloaded']:
            tweet_id = video['tweet_id']
            
            # Find the corresponding note
            note = notes_df[notes_df['tweetId'] == tweet_id]
            
            if not note.empty:
                note = note.iloc[0]
                
                mapping.append({
                    'video_file': video['filename'],
                    'video_index': video['index'],
                    'tweet_id': tweet_id,
                    'video_duration': video.get('duration', 0),
                    'video_title': video.get('title', ''),
                    'note_id': note['noteId'],
                    'classification': note['classification'],
                    'community_note_summary': note['summary'],
                    'tweet_url': f"https://twitter.com/i/status/{tweet_id}"
                })
    
    # Create DataFrame and save
    mapping_df = pd.DataFrame(mapping)
    output_file = videos_dir / "video_notes_mapping.csv"
    mapping_df.to_csv(output_file, index=False)
    
    print(f"✓ Created mapping for {len(mapping)} videos")
    print(f"✓ Saved to: {output_file}")
    
    # Also save a simplified version
    simple_df = mapping_df[['video_file', 'video_duration', 'classification', 'community_note_summary']]
    simple_file = videos_dir / "video_notes_simple.csv"
    simple_df.to_csv(simple_file, index=False)
    print(f"✓ Simplified version: {simple_file}")
    
    # Print sample
    print("\nSample mapping:")
    print("=" * 80)
    for i, row in mapping_df.head(5).iterrows():
        print(f"\n{i+1}. {row['video_file']}")
        print(f"   Duration: {row['video_duration']:.1f}s")
        print(f"   Classification: {row['classification']}")
        print(f"   Note: {row['community_note_summary'][:100]}...")

if __name__ == "__main__":
    create_mapping()

