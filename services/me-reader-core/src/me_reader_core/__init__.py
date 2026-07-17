"""ME-Reader Core: evidence-oriented literature reading infrastructure."""

from .models import PaperValidationError, ZoteroPaper
from .obsidian import PaperNoteResult, create_or_find_paper_note

__all__ = [
    "PaperNoteResult",
    "PaperValidationError",
    "ZoteroPaper",
    "create_or_find_paper_note",
]
