"""
Data Exploration Script for Community Notes
This script helps explore the downloaded Community Notes data to understand its structure.
"""

import pandas as pd
from pathlib import Path
import json

def explore_notes_data(filepath):
    """Explore and display information about the notes data."""
    print("=" * 70)
    print("COMMUNITY NOTES DATA EXPLORATION")
    print("=" * 70)
    
    try:
        # Try reading as TSV first
        if filepath.suffix == '.tsv':
            df = pd.read_csv(filepath, sep='\t', low_memory=False)
        else:
            df = pd.read_csv(filepath, low_memory=False)
        
        print(f"\n✓ Successfully loaded: {filepath.name}")
        print(f"  Total rows: {len(df):,}")
        print(f"  Total columns: {len(df.columns)}")
        
        print("\n" + "-" * 70)
        print("COLUMNS:")
        print("-" * 70)
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        print("\n" + "-" * 70)
        print("SAMPLE DATA (first 3 rows):")
        print("-" * 70)
        print(df.head(3).to_string())
        
        print("\n" + "-" * 70)
        print("DATA TYPES:")
        print("-" * 70)
        print(df.dtypes)
        
        print("\n" + "-" * 70)
        print("MISSING VALUES:")
        print("-" * 70)
        missing = df.isnull().sum()
        missing = missing[missing > 0].sort_values(ascending=False)
        if len(missing) > 0:
            print(missing)
        else:
            print("  No missing values!")
        
        # Check for video-related columns or content
        print("\n" + "-" * 70)
        print("VIDEO-RELATED ANALYSIS:")
        print("-" * 70)
        
        video_keywords = ['video', 'footage', 'clip', 'recording', 'filmed', 
                         'AI-generated', 'deepfake', 'fake video', 'edited video',
                         'manipulated', 'CGI', 'animation']
        
        # Check each text column for video keywords
        text_columns = df.select_dtypes(include=['object']).columns
        
        for col in text_columns:
            if col in ['summary', 'text', 'content', 'note']:
                keyword_matches = 0
                for keyword in video_keywords:
                    matches = df[col].fillna('').str.contains(keyword, case=False, na=False).sum()
                    if matches > 0:
                        keyword_matches += matches
                        print(f"  '{keyword}' found in '{col}': {matches} times")
                
                if keyword_matches > 0:
                    print(f"  Total video-related mentions in '{col}': {keyword_matches}")
        
        # Check for URLs or tweetIds
        if 'tweetId' in df.columns:
            print(f"\n  Total unique tweets with notes: {df['tweetId'].nunique():,}")
        
        # Classification analysis
        if 'classification' in df.columns:
            print("\n" + "-" * 70)
            print("CLASSIFICATION DISTRIBUTION:")
            print("-" * 70)
            print(df['classification'].value_counts())
        
        print("\n" + "=" * 70)
        print("EXPLORATION COMPLETE")
        print("=" * 70)
        
        return df
        
    except Exception as e:
        print(f"\n✗ Error loading data: {e}")
        return None


def main():
    """Main entry point."""
    data_dir = Path('data')
    
    # Check for raw data
    raw_dir = data_dir / 'raw'
    if raw_dir.exists():
        print("\nChecking raw data directory...")
        raw_files = list(raw_dir.glob('*.tsv')) + list(raw_dir.glob('*.csv'))
        
        if raw_files:
            print(f"Found {len(raw_files)} data files:")
            for f in raw_files:
                print(f"  - {f.name}")
            
            # Explore the notes file
            notes_file = None
            for f in raw_files:
                if 'notes' in f.name.lower() and 'status' not in f.name.lower():
                    notes_file = f
                    break
            
            if notes_file:
                print(f"\n📊 Exploring: {notes_file.name}")
                explore_notes_data(notes_file)
            else:
                print("\n⚠️  No 'notes' file found in raw data")
        else:
            print("⚠️  No data files found in raw directory")
    else:
        print("⚠️  Raw data directory does not exist yet")
        print("    Run 'python download_filter_community_notes.py' first")
    
    # Check for filtered data
    filtered_dir = data_dir / 'filtered'
    if filtered_dir.exists():
        print("\n\nChecking filtered data directory...")
        filtered_files = list(filtered_dir.glob('*.csv')) + list(filtered_dir.glob('*.tsv'))
        
        if filtered_files:
            print(f"Found {len(filtered_files)} filtered files:")
            for f in filtered_files:
                print(f"  - {f.name}")
                
            # Explore video notes file
            video_file = None
            for f in filtered_files:
                if 'video' in f.name.lower():
                    video_file = f
                    break
            
            if video_file:
                print(f"\n📊 Exploring: {video_file.name}")
                explore_notes_data(video_file)
        else:
            print("⚠️  No filtered data files found")
    else:
        print("\n⚠️  Filtered data directory does not exist yet")


if __name__ == "__main__":
    main()

