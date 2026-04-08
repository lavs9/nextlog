"""NextLog - Agentic Vault System

Process bookmarks from X/Twitter, YouTube, and other sources.
Synthesize raw content into structured, interconnected notes.
"""

__version__ = "0.1.0"
__author__ = "Mayank Lavania"

from .config import Config, load_config
from .processor import Processor
from .search import Search
from .synthesizer import Synthesizer

__all__ = [
    "Config",
    "load_config",
    "Processor",
    "Synthesizer",
    "Search",
]
