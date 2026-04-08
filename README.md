# NextLog

Agentic vault system for processing bookmarks and synthesizing notes.

Process raw information from X/Twitter bookmarks, YouTube links, Obsidian web clips and synthesize them into structured, interconnected notes.

## Features

- **Inbox Processing**: Extract content from X articles, YouTube transcripts, GitHub repos, and web articles
- **LLM-Powered Synthesis**: Automatically identify topics and create structured notes
- **Local Search**: QMD integration for hybrid search (BM25 + vector + LLM reranking)
- **Knowledge Graph**: Auto-generated from wikilinks and LLM-extracted entities
- **CLI First**: Cron-friendly commands for automation

## Quick Start

```bash
# Install
cd nextlog
pip install -e ".[dev]"

# Run
python -m nextlog status
python -m nextlog process
```

## Architecture

```
Inbox (raw) → Processing (extract) → Synthesis (organize) → Output Vault
                    ↓                      ↓                    ↓
              inbox/processed/       synthesis/meta-topic/   QMD index
              (frontmatter)         (wikilinks, cross-ref)
```

## Commands

| Command | Description |
|---------|-------------|
| `python -m nextlog fetch` | Fetch X bookmarks |
| `python -m nextlog process` | Process inbox items |
| `python -m nextlog synthesize` | Create structured notes |
| `python -m nextlog search "query"` | Search via QMD |
| `python -m nextlog run` | Full pipeline |
| `python -m nextlog status` | Show status |

## Configuration

Copy `nextlog.example.json` to `nextlog.json` and configure:

```json
{
  "vault": ".",
  "twitter": {
    "auth_token": "",
    "ct0": ""
  },
  "llm": {
    "provider": "openrouter",
    "api_key": "",
    "model": "anthropic/claude-3.5-sonnet"
  }
}
```

## Folder Structure

```
nextlog/
├── inbox/
│   ├── raw/           # Pending items
│   └── processed/    # Extracted content
├── synthesis/        # Organized notes
│   └── <topic>/
└── ref/              # Ultra-refined (future)
```

## Tech Stack

- Python 3.11+
- OpenRouter for LLM
- QMD for local search
- Click for CLI
