# NextLog

Agentic vault system for processing bookmarks and synthesizing notes.

Process raw information from X/Twitter bookmarks, YouTube links, GitHub repos, and web articles into structured, interconnected notes with local search.

## Features

- **Inbox Processing**: Extract content from X articles, YouTube transcripts, GitHub repos, and web articles
- **LLM-Powered Synthesis**: Automatically identify topics and create structured notes
- **Local Search**: QMD integration for hybrid search (BM25 + vector + LLM reranking)
- **Knowledge Graph**: Auto-generated from wikilinks in synthesis notes
- **CLI First**: Cron-friendly commands for automation
- **Cross-Topic Linking**: Automatically discover and link related topics

## Quick Start

```bash
# Install
cd nextlog
pip install -e ".[dev]"

# Set up QMD (optional but recommended)
npm install -g @tobilu/qmd
nextlog setup-search

# Run full pipeline
nextlog run

# Or step by step
nextlog fetch -l 20     # Fetch X bookmarks
nextlog process         # Extract content from URLs
nextlog synthesize      # Create structured notes
nextlog search "AI"     # Search your notes
```

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Inbox     │───▶│ Processing  │───▶│ Synthesis   │───▶│   Output    │
│  (raw dump) │    │  (extract)  │    │  (organize) │    │   Vault     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │
  inbox/raw/         - X articles       - Topic ID        - inbox/processed/
                     - YouTube          - Note gen        - synthesis/<topic>/
                     - GitHub           - Cross-links     - QMD index
                     - Articles         - Wikilinks
```

## Commands

| Command | Description |
|---------|-------------|
| `nextlog fetch` | Fetch X bookmarks using bird CLI |
| `nextlog process` | Extract content from URLs in inbox |
| `nextlog synthesize` | Create structured notes from processed items |
| `nextlog search "query"` | Search via QMD (hybrid: BM25 + vector + reranking) |
| `nextlog setup-search` | Set up QMD collections with context and embeddings |
| `nextlog graph` | Show knowledge graph from wikilinks |
| `nextlog run` | Run full pipeline: fetch + process + synthesize |
| `nextlog status` | Show status and file counts |

### Search Options

```bash
nextlog search "AI agents"              # Hybrid search (best quality)
nextlog search "ML" -t vsearch           # Vector semantic search only
nextlog search "NN" -t search           # BM25 full-text search
nextlog search "DL" -s 0.3               # Filter by minimum score
nextlog search "API" -c synthesis        # Search specific collection
```

### Fetch Options

```bash
nextlog fetch                    # Fetch 20 bookmarks (default)
nextlog fetch -l 50              # Fetch 50 bookmarks
nextlog fetch --all              # Fetch ALL bookmarks (requires bird from git)
```

## Configuration

Copy `nextlog.example.json` to `nextlog.json`:

```json
{
  "vault": ".",
  "twitter": {
    "auth_token": "your_auth_token",
    "ct0": "your_ct0"
  },
  "llm": {
    "provider": "openrouter",
    "api_key": "your_openrouter_api_key",
    "model": "anthropic/claude-3.5-sonnet"
  },
  "bird_path": "bird"
}
```

### Getting Twitter Credentials

1. Open twitter.com in your browser
2. Open DevTools (F12) → Application tab → Cookies
3. Copy `auth_token` value
4. Add to `nextlog.json`

### Getting OpenRouter API Key

1. Sign up at https://openrouter.ai/
2. Create API key
3. Add to `nextlog.json` or set `OPENROUTER_API_KEY` env var

## Folder Structure

```
nextlog/
├── inbox/
│   ├── raw/              # Raw bookmarks (pending processing)
│   └── processed/        # Extracted content with frontmatter
├── synthesis/            # Organized notes by topic
│   ├── ai/
│   ├── tools/
│   └── productivity/
├── ref/                  # Ultra-refined notes (manual)
└── .state/              # State tracking
```

## Dependencies

### Required
- **Python 3.11+**
- **bird CLI** - For fetching X bookmarks
  ```bash
  npm install -g @steipete/bird
  # Or build from source for --all support
  ```

### Optional (Recommended)
- **QMD** - For local search
  ```bash
  npm install -g @tobilu/qmd
  ```

## QMD Search

QMD provides local hybrid search with:
- **BM25** full-text search (fast, keyword-based)
- **Vector** semantic search (embedding-based)
- **Query expansion** (LLM generates variations)
- **Reranking** (LLM scores relevance)

### Setup QMD

```bash
# Install QMD
npm install -g @tobilu/qmd

# Set up collections and generate embeddings
nextlog setup-search

# Search
nextlog search "your query"
```

### QMD Options

- `--type, -t` - Search type: `search` (BM25), `vsearch` (vector), `query` (hybrid)
- `--min-score, -s` - Minimum score threshold (0.0-1.0)
- `--collection, -c` - Search specific collection
- `--limit, -n` - Number of results

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | LLM API key |
| `AUTH_TOKEN` | Twitter auth token |
| `CT0` | Twitter ct0 cookie |

## Tech Stack

- **Python 3.11+** - Core language
- **Click** - CLI framework
- **OpenRouter** - LLM provider
- **QMD** - Local search engine
- **bird** - Twitter/X API wrapper

## License

MIT
