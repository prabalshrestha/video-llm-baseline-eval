"""
Create a nicely formatted JSON mapping of videos and their Community Notes.
Much easier to read than CSV!
"""

import pandas as pd
import json
from pathlib import Path


def create_json_mapping():
    """Create a readable JSON mapping."""

    # Load the CSV mapping
    videos_dir = Path("data/videos")
    mapping_file = videos_dir / "video_notes_mapping.csv"

    df = pd.read_csv(mapping_file)

    # Convert to list of dictionaries with better structure
    videos_data = []

    for i, row in df.iterrows():
        video_data = {
            "video": {
                "filename": row["video_file"],
                "index": int(row["video_index"]),
                "duration_seconds": float(row["video_duration"]),
                "title": row["video_title"],
                "path": f"data/videos/{row['video_file']}",
            },
            "tweet": {"id": str(row["tweet_id"]), "url": row["tweet_url"]},
            "community_note": {
                "note_id": str(row["note_id"]),
                "classification": row["classification"],
                "summary": row["community_note_summary"],
                "is_misleading": row["classification"]
                == "MISINFORMED_OR_POTENTIALLY_MISLEADING",
            },
        }
        videos_data.append(video_data)

    # Create the full mapping object
    mapping = {
        "dataset": {
            "name": "Video LLM Baseline Evaluation Dataset",
            "description": "Sample videos from Twitter with Community Notes for misinformation detection",
            "total_videos": len(videos_data),
            "created": "2025-11-27",
        },
        "statistics": {
            "total_videos": len(videos_data),
            "misleading": sum(
                1 for v in videos_data if v["community_note"]["is_misleading"]
            ),
            "not_misleading": sum(
                1 for v in videos_data if not v["community_note"]["is_misleading"]
            ),
            "total_duration_seconds": sum(
                v["video"]["duration_seconds"] for v in videos_data
            ),
            "average_duration_seconds": sum(
                v["video"]["duration_seconds"] for v in videos_data
            )
            / len(videos_data),
        },
        "videos": videos_data,
    }

    # Save as formatted JSON
    output_file = videos_dir / "video_notes_mapping.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print(f"✓ Created JSON mapping with {len(videos_data)} videos")
    print(f"✓ Saved to: {output_file}")
    print(f"\nStatistics:")
    print(f"  Total videos: {mapping['statistics']['total_videos']}")
    print(f"  Misleading: {mapping['statistics']['misleading']}")
    print(f"  Not misleading: {mapping['statistics']['not_misleading']}")
    print(f"  Total duration: {mapping['statistics']['total_duration_seconds']:.1f}s")
    print(
        f"  Average duration: {mapping['statistics']['average_duration_seconds']:.1f}s"
    )

    # Create a simplified version with just the essentials
    simple_mapping = [
        {
            "video_file": v["video"]["filename"],
            "duration": f"{v['video']['duration_seconds']:.1f}s",
            "classification": v["community_note"]["classification"],
            "note": v["community_note"]["summary"],
        }
        for v in videos_data
    ]

    simple_file = videos_dir / "video_notes_simple.json"
    with open(simple_file, "w", encoding="utf-8") as f:
        json.dump(simple_mapping, f, indent=2, ensure_ascii=False)

    print(f"✓ Simplified version: {simple_file}")

    # Print sample
    print("\n" + "=" * 80)
    print("SAMPLE - First 2 videos:")
    print("=" * 80)
    print(json.dumps(videos_data[:2], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    create_json_mapping()
