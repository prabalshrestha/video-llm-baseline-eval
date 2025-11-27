"""
Community Note data model.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CommunityNote:
    """Represents a Community Note from X/Twitter."""

    note_id: str
    tweet_id: str
    classification: str
    summary: str
    created_at_millis: int
    is_media_note: bool = False
    is_misleading: bool = field(init=False)

    def __post_init__(self):
        self.is_misleading = (
            self.classification == "MISINFORMED_OR_POTENTIALLY_MISLEADING"
        )

    @property
    def created_at(self) -> datetime:
        """Convert milliseconds to datetime."""
        return datetime.fromtimestamp(self.created_at_millis / 1000)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "note_id": self.note_id,
            "tweet_id": self.tweet_id,
            "classification": self.classification,
            "summary": self.summary,
            "is_misleading": self.is_misleading,
            "created_at": self.created_at.isoformat(),
        }

