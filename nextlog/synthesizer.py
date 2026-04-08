"""Synthesis layer for NextLog.

Creates structured notes from processed content using LLM.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from .config import Config
from .search import Search


class Synthesizer:
    """Synthesize processed content into structured notes."""

    def __init__(self, config: Config):
        self.config = config
        self.search = Search(config)
        self._llm_client: requests.Session | None = None

    @property
    def llm_client(self) -> requests.Session:
        """Get or create LLM client."""
        if self._llm_client is None:
            self._llm_client = requests.Session()
        return self._llm_client

    def synthesize_all(self, limit: int | None = None) -> int:
        """Synthesize all processed items that haven't been synthesized."""
        processed_dir = self.config.inbox_processed
        if not processed_dir.exists():
            return 0

        items = list(processed_dir.glob("*.md"))
        if limit:
            items = items[:limit]

        synthesized = 0
        for item in items:
            if self._should_synthesize(item):
                if self.synthesize_item(item):
                    synthesized += 1

        return synthesized

    def _should_synthesize(self, item_path: Path) -> bool:
        """Check if item should be synthesized."""
        content = item_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end > 0:
                frontmatter = content[3:fm_end]
                return "synthesized: true" not in frontmatter.lower()
        return True

    def synthesize_item(self, item_path: Path) -> bool:
        """Synthesize a single processed item."""
        try:
            content = item_path.read_text(encoding="utf-8")
            frontmatter = self._extract_frontmatter(content)
            body = self._extract_body(content)

            topics = self.identify_topics(body)
            if not topics:
                topics = ["uncategorized"]

            for topic in topics:
                topic_folder = self.config.synthesis / self._slugify(topic)
                topic_folder.mkdir(parents=True, exist_ok=True)

                sources = [item_path]
                cross_links = self.find_cross_topic_links(body)

                existing_note = self._find_existing_note(topic_folder, topic)
                if existing_note:
                    self.update_note(existing_note, body, sources)
                else:
                    self.create_note(topic, body, sources)

            self._mark_synthesized(item_path)
            return True

        except Exception as e:
            print(f"Error synthesizing {item_path}: {e}")
            return False

    def _extract_frontmatter(self, content: str) -> dict[str, Any]:
        """Extract frontmatter from content."""
        if not content.startswith("---"):
            return {}

        fm_end = content.find("---", 3)
        if fm_end < 0:
            return {}

        fm_text = content[3:fm_end]
        fm = {}
        for line in fm_text.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                fm[key.strip()] = value.strip().strip('"')
        return fm

    def _extract_body(self, content: str) -> str:
        """Extract body content without frontmatter."""
        if content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end > 0:
                return content[fm_end + 3:].strip()
        return content

    def _mark_synthesized(self, item_path: Path) -> None:
        """Mark item as synthesized in frontmatter."""
        content = item_path.read_text(encoding="utf-8")

        if content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end > 0:
                frontmatter = content[3:fm_end]
                body = content[fm_end + 3:]

                if "synthesized:" not in frontmatter.lower():
                    frontmatter = frontmatter.rstrip() + "\nsynthesized: true\n"
                    item_path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")
        else:
            fm = """---
synthesized: true
---
"""
            item_path.write_text(fm + content, encoding="utf-8")

    def identify_topics(self, content: str) -> list[str]:
        """Identify topics using LLM."""
        if not self.config.llm_api_key:
            return self._simple_topic_extraction(content)

        prompt = f"""Analyze the following content and identify the main topics it covers.
Return a JSON array of topic names (max 5 topics).
Each topic should be 1-3 words, suitable for a folder name.

Content:
{content[:3000]}

Return ONLY a JSON array, nothing else."""

        try:
            response = self.llm_client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"]
                topics = json.loads(text)
                if isinstance(topics, list):
                    return topics
        except Exception as e:
            print(f"LLM topic identification failed: {e}")

        return self._simple_topic_extraction(content)

    def _simple_topic_extraction(self, content: str) -> list[str]:
        """Simple keyword-based topic extraction without LLM."""
        keywords = {
            "ai": ["AI", "machine learning", "LLM", "GPT", "Claude", "model"],
            "coding": ["code", "programming", "developer", "Python", "JavaScript"],
            "tools": ["tool", "CLI", "software", "app", "application"],
            "productivity": ["productivity", "workflow", "automation", "效率"],
            "research": ["research", "paper", "study", "analysis"],
        }

        content_lower = content.lower()
        found = []
        for topic, terms in keywords.items():
            if any(term.lower() in content_lower for term in terms):
                found.append(topic)

        return found[:3] if found else ["general"]

    def create_note(self, topic: str, content: str, sources: list[Path]) -> Path | None:
        """Create or update a synthesis note."""
        topic_folder = self.config.synthesis / self._slugify(topic)
        topic_folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d")
        note_name = f"{timestamp}-{self._slugify(topic[:30])}.md"
        note_path = topic_folder / note_name

        title = self._extract_title(content, topic)
        linked_sources = self._format_sources(sources)

        note_content = f"""---
created: {datetime.now().isoformat()}
topics: [{topic}]
sources: {linked_sources}
---

# {title}

{content[:5000]}

## Decision Log
- {datetime.now().isoformat()}: Created note from {len(sources)} source(s)

## References
{linked_sources}
"""

        note_path.write_text(note_content, encoding="utf-8")
        return note_path

    def update_note(self, note_path: Path, new_content: str, sources: list[Path]) -> None:
        """Update existing note, preserving decision logs."""
        existing = note_path.read_text(encoding="utf-8")

        fm_match = re.match(r"^---\n(.*?)\n---", existing, re.DOTALL)
        if not fm_match:
            return

        frontmatter = fm_match.group(1)
        body_start = fm_match.end()

        timestamp = datetime.now().isoformat()
        linked_sources = self._format_sources(sources)

        new_section = f"""

## Update {timestamp}

{new_content[:3000]}

Sources: {linked_sources}
"""

        decision_log = "## Decision Log"
        if decision_log in existing:
            existing = existing.replace(
                decision_log,
                f"{new_section}\n\n{decision_log}"
            )
        else:
            existing += f"\n\n{new_section}\n\n{decision_log}"

        note_path.write_text(existing, encoding="utf-8")

    def _find_existing_note(self, topic_folder: Path, topic: str) -> Path | None:
        """Find existing note for topic."""
        if not topic_folder.exists():
            return None

        notes = list(topic_folder.glob("*.md"))
        return notes[0] if notes else None

    def find_cross_topic_links(self, content: str) -> list[str]:
        """Find cross-topic links using QMD search."""
        if not self.search.is_available():
            return []

        keywords = self._extract_keywords(content[:500])
        links = []

        for keyword in keywords[:3]:
            results = self.search.search(keyword, limit=3)
            for r in results:
                if path := r.get("path"):
                    rel_path = Path(path).relative_to(self.config.synthesis)
                    link_name = str(rel_path.with_suffix("")).replace("/", ".")
                    if link_name not in links:
                        links.append(link_name)

        return links

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        words = re.findall(r"\b[a-z]{4,}\b", text.lower())
        common = {"this", "that", "with", "from", "have", "been", "will", "when", "what", "there"}
        return [w for w in words if w not in common][:10]

    def _slugify(self, text: str) -> str:
        """Convert text to slug."""
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        return text.strip("-")[:50]

    def _extract_title(self, content: str, fallback: str) -> str:
        """Extract title from content."""
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1)
        match = re.search(r"^##\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1)
        return fallback.title()

    def _format_sources(self, sources: list[Path]) -> str:
        """Format sources as wikilinks."""
        return json.dumps([str(s.relative_to(self.config.vault_path)) for s in sources])
