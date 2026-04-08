"""Processing layer for NextLog.

Handles URL detection, content extraction, and markdown generation.
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import requests

from .config import Config


class Processor:
    """Process raw inbox items."""

    def __init__(self, config: Config):
        self.config = config

    def process_all(self, limit: int | None = None) -> int:
        """Process all pending items from inbox/raw."""
        raw_dir = self.config.inbox_raw
        if not raw_dir.exists():
            return 0

        items = list(raw_dir.glob("*.md"))
        if limit:
            items = items[:limit]

        processed = 0
        for item in items:
            if self.process_item(item):
                processed += 1

        return processed

    def process_item(self, item_path: Path) -> bool:
        """Process a single inbox item."""
        try:
            content = item_path.read_text(encoding="utf-8")

            # Extract URLs from content
            urls = self._extract_urls(content)

            # Process each URL
            processed_content = content
            metadata = {
                "source": "inbox",
                "processed_at": datetime.now().isoformat(),
                "urls_found": len(urls),
                "status": "processed",
            }

            for url in urls:
                url_type = self.detect_url_type(url)
                metadata[f"url_type_{url}"] = url_type

                if url_type == "x-article":
                    extracted = self.extract_x_article(url)
                    if extracted:
                        metadata[f"x_article_{url}"] = extracted.get("title", "N/A")
                        processed_content += (
                            f"\n\n## X Article: {extracted.get('title', 'Untitled')}\n\n"
                        )
                        processed_content += extracted.get("content", "")[:5000]

                elif url_type == "youtube":
                    transcript = self.extract_youtube_transcript(url)
                    if transcript:
                        metadata[f"youtube_transcript_{url}"] = "extracted"
                        processed_content += f"\n\n## YouTube Transcript\n\n{transcript[:10000]}"

                elif url_type == "github":
                    repo_info = self.extract_github_info(url)
                    if repo_info:
                        metadata[f"github_{url}"] = repo_info.get("name", "N/A")
                        processed_content += f"\n\n## GitHub: {repo_info.get('full_name')}\n\n"
                        processed_content += f"**Stars:** {repo_info.get('stars', 0)}\n\n"
                        processed_content += (
                            f"**Description:** {repo_info.get('description', '')}\n\n"
                        )
                        processed_content += f"**Readme:** {repo_info.get('readme', '')[:3000]}"

                elif url_type == "article":
                    article_content = self.extract_article(url)
                    if article_content:
                        processed_content += f"\n\n## Article Content\n\n{article_content[:10000]}"

            # Write processed file
            output_path = self.config.inbox_processed / item_path.name

            # Add frontmatter
            frontmatter = self._generate_frontmatter(metadata)
            final_content = frontmatter + "\n" + processed_content

            output_path.write_text(final_content, encoding="utf-8")

            # Optionally remove raw file or mark as processed
            # item_path.unlink()  # Uncomment to remove after processing

            return True

        except Exception as e:
            print(f"Error processing {item_path}: {e}")
            return False

    def _extract_urls(self, text: str) -> list[str]:
        """Extract URLs from text."""
        import re

        url_pattern = re.compile(r"https?://[^\s\)]+")
        urls = url_pattern.findall(text)

        # Deduplicate
        return list(set(urls))

    def _generate_frontmatter(self, metadata: dict) -> str:
        """Generate YAML frontmatter."""
        lines = ["---"]
        for key, value in metadata.items():
            if isinstance(value, str):
                # Escape strings
                value = value.replace('"', '\\"')
                lines.append(f'{key}: "{value}"')
            else:
                lines.append(f"{key}: {value}")
        lines.append("---")
        return "\n".join(lines)

    def detect_url_type(self, url: str) -> str:
        """Detect URL type (x-article, youtube, github, etc.)."""
        url_lower = url.lower()
        if "x.com" in url_lower or "twitter.com" in url_lower:
            if "/i/article/" in url:
                return "x-article"
            return "tweet"
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        if "github.com" in url_lower:
            return "github"
        return "article"

    def extract_x_article(self, url: str) -> dict | None:
        """Extract X article content via bird CLI."""
        try:
            env = os.environ.copy()
            twitter = self.config.twitter
            if twitter.get("auth_token"):
                env["AUTH_TOKEN"] = twitter["auth_token"]
            if twitter.get("ct0"):
                env["CT0"] = twitter["ct0"]

            bird_cmd = self.config.bird_path

            # Extract article ID from URL
            import re

            match = re.search(r"/i/article/(\d+)", url)
            if not match:
                return None

            article_id = match.group(1)

            # Try to search for the article tweet
            search_query = f"url:x.com/i/article/{article_id}"
            result = subprocess.run(
                [bird_cmd, "search", search_query, "-n", "5", "--json"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )

            if result.returncode != 0:
                return None

            try:
                tweets = json.loads(result.stdout)
                if not tweets:
                    return None

                tweet = tweets[0]
                return {
                    "title": tweet.get("article", {}).get("title", "Untitled"),
                    "content": tweet.get("text", ""),
                    "author": tweet.get("author", {}).get("username", "unknown"),
                    "url": url,
                }
            except json.JSONDecodeError:
                return None

        except Exception as e:
            print(f"Error extracting X article: {e}")
            return None

    def extract_youtube_transcript(self, url: str) -> str | None:
        """Extract YouTube transcript via yt-dlp."""
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--write-subs",
                    "--sub-lang",
                    "en",
                    "--skip-download",
                    "--print",
                    " %(subs)s",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # If transcript was downloaded, try to extract it
            # For now, return a placeholder - full implementation would parse the subtitle file
            if result.returncode == 0:
                # Try to get transcript via --get-subs
                result2 = subprocess.run(
                    ["yt-dlp", "--get-subs", url], capture_output=True, text=True, timeout=30
                )
                # Return success indicator for now
                return f"[Transcript available for {url}]"

            return None

        except Exception as e:
            print(f"Error extracting YouTube transcript: {e}")
            return None

    def extract_github_info(self, url: str) -> dict | None:
        """Extract GitHub repo info via API."""
        import re

        match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
        if not match:
            return None

        owner, repo = match.groups()
        repo = repo.replace(".git", "")

        try:
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(api_url, timeout=10)
            if response.status_code != 200:
                return None

            data = response.json()

            # Try to get README
            readme = ""
            try:
                readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
                readme_response = requests.get(readme_url, timeout=10)
                if readme_response.status_code == 200:
                    import base64

                    content = readme_response.json().get("content", "")
                    if content:
                        readme = base64.b64decode(content).decode("utf-8")[:3000]
            except Exception:
                pass

            return {
                "name": data.get("name"),
                "full_name": data.get("full_name"),
                "description": data.get("description", ""),
                "stars": data.get("stargazers_count", 0),
                "language": data.get("language"),
                "url": data.get("html_url"),
                "readme": readme,
            }

        except Exception as e:
            print(f"Error fetching GitHub info: {e}")
            return None

    def extract_article(self, url: str) -> str | None:
        """Extract generic article content."""
        try:
            response = requests.get(
                url,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )

            if response.status_code != 200:
                return None

            html = response.text[:50000]

            # Simple extraction - get title and meta description
            import re

            title_match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
            desc_match = re.search(
                r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )

            content = ""
            if title_match:
                content += f"Title: {title_match.group(1)}\n\n"
            if desc_match:
                content += f"Description: {desc_match.group(1)}\n\n"

            content += f"[Full content available at {url}]"

            return content

        except Exception as e:
            print(f"Error extracting article: {e}")
            return None
