"""
Video data model.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Video:
    """Represents a downloaded video."""

    filename: str
    tweet_id: str
    duration_seconds: float
    title: str = ""
    path: str = ""

    @property
    def duration_formatted(self) -> str:
        """Format duration as MM:SS."""
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def file_path(self) -> Path:
        """Get Path object for the video file."""
        return Path(self.path) if self.path else Path("data/videos") / self.filename

    @property
    def exists(self) -> bool:
        """Check if video file exists."""
        return self.file_path.exists()

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "tweet_id": self.tweet_id,
            "duration_seconds": self.duration_seconds,
            "duration_formatted": self.duration_formatted,
            "title": self.title,
            "path": str(self.file_path),
            "exists": self.exists,
        }

