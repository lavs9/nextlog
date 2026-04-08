"""Search integration for NextLog using QMD.

Optimized usage of QMD for NextLog:
- Use `query` command for hybrid search (BM25 + vector + reranking)
- Set up context for collections to improve search relevance
- Use min-score to filter low-quality results
- Index updates after processing new content
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .config import Config


class Search:
    """Search using QMD."""

    def __init__(self, config: Config):
        self.config = config

    def _run_qmd(self, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run QMD command."""
        return subprocess.run(
            ["qmd"] + args,
            capture_output=True,
            text=True,
            cwd=self.config.vault_path,
            timeout=timeout,
        )

    def is_available(self) -> bool:
        """Check if QMD is available."""
        try:
            result = subprocess.run(
                ["qmd", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def status(self) -> dict[str, Any]:
        """Get QMD status and index health."""
        result = self._run_qmd(["status", "--json"])
        if result.returncode != 0:
            return {}
        try:
            return json.loads(result.stdout)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return {}

    def search(
        self,
        query: str,
        limit: int = 5,
        collection: str | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """BM25 full-text search (fast, keyword-based)."""
        args = ["search", query, "-n", str(limit), "--json"]
        if collection:
            args.extend(["-c", collection])
        if min_score > 0:
            args.extend(["--min-score", str(min_score)])

        result = self._run_qmd(args)
        if result.returncode != 0:
            return []

        try:
            return json.loads(result.stdout)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return []

    def vsearch(
        self,
        query: str,
        limit: int = 5,
        collection: str | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Vector semantic search."""
        args = ["vsearch", query, "-n", str(limit), "--json"]
        if collection:
            args.extend(["-c", collection])
        if min_score > 0:
            args.extend(["--min-score", str(min_score)])

        result = self._run_qmd(args)
        if result.returncode != 0:
            return []

        try:
            return json.loads(result.stdout)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return []

    def query(
        self,
        query: str,
        limit: int = 5,
        collection: str | None = None,
        min_score: float = 0.0,
        explain: bool = False,
    ) -> list[dict[str, Any]]:
        """Hybrid query with reranking (best quality).

        This uses:
        - Query expansion (LLM generates variations)
        - BM25 full-text search
        - Vector semantic search
        - RRF fusion
        - LLM reranking
        """
        args = ["query", query, "-n", str(limit), "--json"]
        if collection:
            args.extend(["-c", collection])
        if min_score > 0:
            args.extend(["--min-score", str(min_score)])
        if explain:
            args.append("--explain")

        result = self._run_qmd(args, timeout=60)
        if result.returncode != 0:
            return []

        try:
            return json.loads(result.stdout)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return []

    def add_collection(self, name: str, path: Path, pattern: str = "**/*.md") -> bool:
        """Add QMD collection."""
        if not path.exists():
            return False

        result = self._run_qmd([
            "collection", "add", str(path.absolute()),
            "--name", name,
            "--mask", pattern,
        ])
        return result.returncode == 0

    def remove_collection(self, name: str) -> bool:
        """Remove QMD collection."""
        result = self._run_qmd(["collection", "remove", name])
        return result.returncode == 0

    def list_collections(self) -> list[dict[str, Any]]:
        """List QMD collections with stats."""
        result = self._run_qmd(["collection", "list", "--json"])
        if result.returncode != 0:
            return []

        try:
            return json.loads(result.stdout)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return []

    def add_context(self, path: str, context: str) -> bool:
        """Add context to a collection path for better search relevance.

        Context helps QMD understand the meaning of documents and
        improves search quality for agentic workflows.
        """
        result = self._run_qmd(["context", "add", path, context])
        return result.returncode == 0

    def list_contexts(self) -> list[dict[str, Any]]:
        """List all contexts."""
        result = self._run_qmd(["context", "list", "--json"])
        if result.returncode != 0:
            return []

        try:
            return json.loads(result.stdout)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return []

    def embed(self, collection: str | None = None, force: bool = False) -> bool:
        """Generate vector embeddings for semantic search."""
        args = ["embed"]
        if force:
            args.append("-f")
        if collection:
            args.extend(["-c", collection])

        result = self._run_qmd(args, timeout=300)
        return result.returncode == 0

    def update_index(self, collection: str | None = None) -> bool:
        """Update QMD index for new/modified files."""
        args = ["update"]
        if collection:
            args.append(collection)

        result = self._run_qmd(args)
        return result.returncode == 0

    def get_document(
        self,
        doc_path: str | Path,
        from_line: int | None = None,
        max_lines: int | None = None,
    ) -> dict[str, Any] | None:
        """Get document content."""
        path_str = str(doc_path)
        if from_line:
            path_str += f":{from_line}"

        args = ["get", path_str, "--json"]
        if max_lines:
            args.extend(["-l", str(max_lines)])

        result = self._run_qmd(args)
        if result.returncode != 0:
            return None

        try:
            return json.loads(result.stdout)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return None

    def multi_get(self, pattern: str, max_bytes: int = 20480) -> list[dict[str, Any]]:
        """Get multiple documents by glob pattern or comma-separated list."""
        result = self._run_qmd([
            "multi-get", pattern,
            "--json",
            "--max-bytes", str(max_bytes),
        ])
        if result.returncode != 0:
            return []

        try:
            data = json.loads(result.stdout)
            return data.get("docs", [])
        except json.JSONDecodeError:
            return []

    def build_knowledge_graph(self) -> dict[str, Any]:
        """Build knowledge graph from wikilinks in synthesis notes."""
        graph: dict[str, Any] = {"nodes": [], "edges": []}
        synth_dir = self.config.synthesis

        if not synth_dir.exists():
            return graph

        notes = list(synth_dir.rglob("*.md"))
        note_names: dict[str, Path] = {}

        for note in notes:
            rel_path = note.relative_to(synth_dir)
            name = str(rel_path.with_suffix("")).replace("/", ".")
            note_names[name] = note

        for note_path in notes:
            content = note_path.read_text(encoding="utf-8")

            node_id = str(note_path.relative_to(synth_dir).with_suffix(""))
            graph["nodes"].append({
                "id": node_id,
                "path": str(note_path),
                "title": self._extract_title(content, note_path.stem),
            })

            wikilinks = re.findall(r"\[\[([^\]|]+)", content)
            for link in wikilinks:
                if link in note_names:
                    graph["edges"].append({
                        "from": node_id,
                        "to": str(note_names[link].relative_to(synth_dir).with_suffix("")),
                    })

        return graph

    def _extract_title(self, content: str, fallback: str) -> str:
        """Extract title from markdown content."""
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        return match.group(1) if match else fallback

    def setup_collections(self) -> None:
        """Set up QMD collections with context for better search."""
        inbox_processed = self.config.inbox_processed
        synthesis = self.config.synthesis

        if inbox_processed.exists():
            self.add_collection("inbox", inbox_processed)
            self.add_context("qmd://inbox", "Raw processed content from bookmarks and links")

        if synthesis.exists():
            self.add_collection("synthesis", synthesis)
            self.add_context("qmd://synthesis", "Synthesized notes organized by topic")

    def search_all(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search across all collections with hybrid query."""
        return self.query(query, limit, min_score=min_score)

    def search_with_intent(
        self,
        query: str,
        intent: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search with explicit intent description for better results.

        The intent helps the query expansion understand the user's goal.
        """
        args = ["query", query, "-n", str(limit), "--json", "--explain"]

        result = self._run_qmd(args, timeout=60)
        if result.returncode != 0:
            return []

        try:
            return json.loads(result.stdout)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return []
