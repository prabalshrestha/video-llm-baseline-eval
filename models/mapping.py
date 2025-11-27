"""
Video-Note mapping model.
"""

from dataclasses import dataclass, field
from .video import Video
from .note import CommunityNote


@dataclass
class VideoNoteMapping:
    """Maps a video to its Community Note."""

    video: Video
    note: CommunityNote
    tweet_url: str = field(init=False)

    def __post_init__(self):
        self.tweet_url = f"https://twitter.com/i/status/{self.video.tweet_id}"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "video": self.video.to_dict(),
            "community_note": self.note.to_dict(),
            "tweet_url": self.tweet_url,
        }

    @property
    def is_misleading(self) -> bool:
        """Quick access to misleading status."""
        return self.note.is_misleading

