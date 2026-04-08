"""X/Twitter bookmark fetcher using bird CLI."""

import json
import os
import subprocess
from datetime import datetime

from .config import Config


class Fetcher:
    """Fetch bookmarks from X/Twitter using bird CLI."""

    def __init__(self, config: Config):
        self.config = config

    def is_bird_available(self) -> bool:
        """Check if bird CLI is available."""
        try:
            result = subprocess.run(
                [self.config.bird_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def fetch_bookmarks(self, limit: int = 20, all_bookmarks: bool = False) -> int:
        """Fetch X bookmarks using bird CLI.

        Args:
            limit: Number of bookmarks to fetch
            all_bookmarks: Fetch all bookmarks (paginated)

        Returns:
            Number of bookmarks fetched
        """
        if not self.is_bird_available():
            print("bird CLI not found. Install from: https://github.com/steipete/bird")
            return 0

        twitter = self.config.twitter
        if not twitter.get("auth_token"):
            print("Twitter credentials not configured.")
            print("Set twitter.auth_token in nextlog.json")
            return 0

        env = os.environ.copy()
        env["AUTH_TOKEN"] = twitter.get("auth_token", "")
        if twitter.get("ct0"):
            env["CT0"] = twitter.get("ct0", "")

        args = [
            self.config.bird_path,
            "bookmarks",
            "-n", str(limit),
            "--json",
        ]

        if all_bookmarks:
            args.append("--all")

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
                cwd=self.config.vault_path,
            )

            if result.returncode != 0:
                print(f"Error fetching bookmarks: {result.stderr}")
                return 0

            bookmarks = self._parse_bookmarks(result.stdout)
            saved = self._save_bookmarks(bookmarks)

            return saved

        except subprocess.TimeoutExpired:
            print("Timeout fetching bookmarks")
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 0

    def _parse_bookmarks(self, output: str) -> list[dict]:
        """Parse bookmark JSON output."""
        try:
            data = json.loads(output)
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError:
            return []

    def _save_bookmarks(self, bookmarks: list[dict]) -> int:
        """Save bookmarks to inbox/raw folder."""
        if not bookmarks:
            return 0

        raw_dir = self.config.inbox_raw
        raw_dir.mkdir(parents=True, exist_ok=True)

        saved = 0
        for bookmark in bookmarks:
            content = self._format_bookmark(bookmark)
            if content:
                filename = self._generate_filename(bookmark)
                filepath = raw_dir / filename
                filepath.write_text(content, encoding="utf-8")
                saved += 1

        return saved

    def _format_bookmark(self, bookmark: dict) -> str:
        """Format bookmark as markdown."""
        tweet = bookmark.get("tweet", {})
        user = tweet.get("user", {})
        text = tweet.get("text", "")
        url = tweet.get("url", "")
        created_at = tweet.get("created_at", "")

        lines = [
            f"# {user.get('name', 'Unknown')} (@{user.get('screen_name', '')})",
            "",
            f">{text}",
            "",
            f"- **Tweet:** {url}",
            f"- **Date:** {created_at}",
            "",
        ]

        if entities := tweet.get("entities", {}):
            if urls := entities.get("urls", []):
                lines.append("## Links")
                for u in urls:
                    lines.append(f"- {u.get('expanded_url', u.get('url', ''))}")
                lines.append("")

        return "\n".join(lines)

    def _generate_filename(self, bookmark: dict) -> str:
        """Generate filename from bookmark."""
        tweet = bookmark.get("tweet", {})
        user = tweet.get("user", {})
        screen_name = user.get("screen_name", "unknown")
        tweet_id = tweet.get("id", datetime.now().strftime("%Y%m%d%H%M%S"))

        return f"{screen_name}-{tweet_id}.md"
