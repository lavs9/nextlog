"""CLI for NextLog."""

from pathlib import Path

import click

from .config import load_config
from .fetcher import Fetcher
from .processor import Processor
from .search import Search
from .synthesizer import Synthesizer


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def main(ctx, config, verbose):
    """NextLog - Agentic Vault System."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(Path(config) if config else None)
    ctx.obj["verbose"] = verbose


@main.command()
@click.argument("name")
@click.option("--path", "-p", type=click.Path(), help="Vault location (default: current directory)")
@click.pass_context
def init(ctx, name, path):
    """Initialize a new NextLog vault.

    Creates a new vault with the given NAME at the specified PATH.

    Example:
        nextlog init my-vault
        nextlog init work-notes --path ~/notes
    """
    if path:
        vault_path = Path(path).expanduser().absolute()
    else:
        vault_path = Path.cwd() / name

    if vault_path.exists() and any(vault_path.iterdir()):
        click.echo(f"Error: Directory {vault_path} already exists and is not empty.")
        return

    vault_path.mkdir(parents=True, exist_ok=True)

    (vault_path / "inbox" / "raw").mkdir(parents=True, exist_ok=True)
    (vault_path / "inbox" / "processed").mkdir(parents=True, exist_ok=True)
    (vault_path / "synthesis").mkdir(parents=True, exist_ok=True)
    (vault_path / "ref").mkdir(parents=True, exist_ok=True)
    (vault_path / ".state").mkdir(parents=True, exist_ok=True)

    config = {
        "vault": ".",
        "timezone": "America/New_York",
        "twitter": {
            "auth_token": "",
            "ct0": ""
        },
        "llm": {
            "provider": "openrouter",
            "api_key": "",
            "model": "anthropic/claude-3.5-sonnet"
        },
        "bird_path": "bird"
    }

    import yaml
    config_path = vault_path / "nextlog.json"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    readme_content = """# NextLog Vault

This is a NextLog vault for processing bookmarks and synthesizing notes.

## Getting Started

1. Set up Twitter credentials in `nextlog.json`
2. Run `nextlog fetch` to fetch bookmarks
3. Run `nextlog process` to extract content
4. Run `nextlog synthesize` to create notes

## Commands

```bash
nextlog fetch           # Fetch X bookmarks
nextlog process         # Extract content
nextlog synthesize      # Create notes
nextlog search "query"  # Search via QMD
```

For more help, see: https://github.com/lavs9/nextlog
"""

    (vault_path / "README.md").write_text(readme_content)

    click.echo(f"✓ Created vault at: {vault_path}")
    click.echo("\nNext steps:")
    click.echo(f"  cd {vault_path}")
    click.echo("  # Edit nextlog.json with your credentials")
    click.echo("  nextlog fetch")


@main.command()
@click.option("--limit", "-l", type=int, default=20, help="Number of bookmarks to fetch")
@click.option("--all", "fetch_all", is_flag=True, help="Fetch all bookmarks (requires bird from git)")
@click.pass_context
def fetch(ctx, limit, fetch_all):
    """Fetch X bookmarks using bird CLI.

    Requires:
    - bird CLI: https://github.com/steipete/bird
    - Twitter auth_token in nextlog.json

    Example:
        nextlog fetch -l 50
        nextlog fetch --all
    """
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", False)

    click.echo("Fetching bookmarks from X...")
    click.echo(f"Vault: {config.vault_path}")

    fetcher = Fetcher(config)

    if not fetcher.is_bird_available():
        click.echo("\nbird CLI not found.")
        click.echo("Install from: https://github.com/steipete/bird")
        click.echo("\nOr build from source for --all flag support:")
        click.echo("  git clone https://github.com/steipete/bird")
        click.echo("  cd bird && pnpm install && pnpm run build:dist")
        click.echo("  npm link --force")
        return

    if not config.twitter.get("auth_token"):
        click.echo("\nTwitter credentials not configured.")
        click.echo("Set twitter.auth_token in nextlog.json:")
        click.echo("""{
  "twitter": {
    "auth_token": "your_auth_token_from_browser",
    "ct0": "your_ct0_cookie"
  }
}""")
        return

    if fetch_all:
        click.echo("Fetching ALL bookmarks (this may take a while)...")
    else:
        click.echo(f"Fetching {limit} bookmarks...")

    count = fetcher.fetch_bookmarks(limit=limit, all_bookmarks=fetch_all)

    if count > 0:
        click.echo(f"\nFetched {count} bookmarks to inbox/raw/")
        if verbose:
            click.echo(f"Files: {config.inbox_raw}")
    else:
        click.echo("\nNo bookmarks fetched. Check your credentials.")


@main.command()
@click.option("--limit", "-l", type=int, help="Limit items to process")
@click.pass_context
def process(ctx, limit):
    """Process inbox items."""
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", False)

    click.echo("Processing inbox...")
    click.echo(f"Raw: {config.inbox_raw}")
    click.echo(f"Processed: {config.inbox_processed}")

    config.inbox_processed.mkdir(parents=True, exist_ok=True)

    processor = Processor(config)
    count = processor.process_all(limit=limit)

    click.echo(f"Processed {count} items.")


@main.command()
@click.option("--limit", "-l", type=int, help="Limit items to synthesize")
@click.pass_context
def synthesize(ctx, limit):
    """Synthesize processed items into notes.

    Uses LLM to identify topics and create structured notes.
    Requires OpenRouter API key in config for LLM features.
    """
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", False)

    click.echo("Synthesizing notes...")
    click.echo(f"Processed: {config.inbox_processed}")
    click.echo(f"Synthesis: {config.synthesis}")

    config.synthesis.mkdir(parents=True, exist_ok=True)

    if not config.llm_api_key:
        click.echo("\nWarning: No LLM API key configured.")
        click.echo("Set 'llm.api_key' in nextlog.json or OPENROUTER_API_KEY env var.")
        click.echo("Using simple keyword-based topic extraction.\n")

    synthesizer = Synthesizer(config)
    count = synthesizer.synthesize_all(limit=limit)

    click.echo(f"\nSynthesized {count} items.")

    if verbose and count > 0:
        click.echo(f"\nCreated notes in: {config.synthesis}")


@main.command()
@click.argument("query")
@click.option("--limit", "-n", default=5, help="Number of results")
@click.option("--type", "-t", type=click.Choice(["search", "vsearch", "query"]),
              default="query", help="Search type: search=BM25, vsearch=vector, query=hybrid (best)")
@click.option("--min-score", "-s", type=float, default=0.0, help="Minimum score threshold (0.0-1.0)")
@click.option("--collection", "-c", type=str, help="Search specific collection")
@click.pass_context
def search(ctx, query, limit, type, min_score, collection):
    """Search using QMD.

    Examples:
        nextlog search "AI agents"
        nextlog search "machine learning" -t vsearch
        nextlog search "neural networks" -s 0.3 -n 10
    """
    config = ctx.obj["config"]
    search = Search(config)

    if not search.is_available():
        click.echo("QMD not found. Install with:")
        click.echo("  npm install -g @tobilu/qmd")
        click.echo("\nOr use: pip install -e \".[dev]\" to install NextLog dependencies")
        return

    click.echo(f"Searching for: {query}")
    if min_score > 0:
        click.echo(f"Min score: {min_score}")

    if type == "search":
        results = search.search(query, limit, collection=collection, min_score=min_score)
    elif type == "vsearch":
        results = search.vsearch(query, limit, collection=collection, min_score=min_score)
    else:
        results = search.query(query, limit, collection=collection, min_score=min_score)

    if not results:
        click.echo("No results found.")
        return

    click.echo(f"\nFound {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        score = r.get("score", 0)
        path = r.get("path", r.get("displayPath", ""))
        click.echo(f"{i}. {title}")
        click.echo(f"   Score: {score:.2f} | {path}")
        if snippet := r.get("snippet"):
            click.echo(f"   {snippet[:100]}...")
        click.echo()


@main.command()
@click.pass_context
def setup_search(ctx):
    """Set up QMD collections with context and embeddings."""
    config = ctx.obj["config"]
    search = Search(config)

    if not search.is_available():
        click.echo("QMD not found. Install with:")
        click.echo("  npm install -g @tobilu/qmd")
        return

    click.echo("Setting up QMD collections...")

    search.setup_collections()

    click.echo("Collections:")
    for coll in search.list_collections():
        click.echo(f"  - {coll.get('name', 'unknown')}: {coll.get('doc_count', 0)} docs")

    click.echo("\nIndexing files...")
    search.update_index()

    click.echo("Generating embeddings (this may take a while)...")
    search.embed(force=True)

    click.echo("Done!")


@main.command()
@click.pass_context
def graph(ctx):
    """Show knowledge graph."""
    config = ctx.obj["config"]
    search = Search(config)

    graph = search.build_knowledge_graph()

    click.echo("Knowledge Graph")
    click.echo("=" * 40)
    click.echo(f"Nodes: {len(graph['nodes'])}")
    click.echo(f"Edges: {len(graph['edges'])}")

    if graph["nodes"]:
        click.echo("\nNotes:")
        for node in graph["nodes"][:10]:
            click.echo(f"  - {node['id']}")
        if len(graph["nodes"]) > 10:
            click.echo(f"  ... and {len(graph['nodes']) - 10} more")


@main.command()
@click.option("--limit", "-l", type=int, help="Limit items to process")
@click.pass_context
def run(ctx, limit):
    """Run full pipeline: fetch + process + synthesize."""
    config = ctx.obj["config"]
    click.echo("Running full pipeline...")
    click.echo(f"Vault: {config.vault_path}")

    click.echo("\n[1/3] Fetching bookmarks...")
    click.echo("  (Skipping - use fetch command separately)")

    click.echo("\n[2/3] Processing inbox...")
    config.inbox_processed.mkdir(parents=True, exist_ok=True)
    processor = Processor(config)
    processed = processor.process_all(limit=limit)
    click.echo(f"  Processed {processed} items.")

    click.echo("\n[3/3] Synthesizing notes...")
    click.echo("  (Not yet implemented)")

    click.echo("\nDone!")


@main.command()
@click.pass_context
def status(ctx):
    """Show status."""
    config = ctx.obj["config"]
    search = Search(config)

    click.echo("NextLog Status")
    click.echo("=" * 40)
    click.echo(f"Vault:     {config.vault_path}")
    click.echo(f"Inbox raw:     {config.inbox_raw}")
    click.echo(f"Inbox processed: {config.inbox_processed}")
    click.echo(f"Synthesis:  {config.synthesis}")
    click.echo(f"Ref:        {config.ref}")

    raw_count = len(list(config.inbox_raw.glob("*.md"))) if config.inbox_raw.exists() else 0
    processed_count = (
        len(list(config.inbox_processed.glob("*.md"))) if config.inbox_processed.exists() else 0
    )
    synthesis_count = len(list(config.synthesis.rglob("*.md"))) if config.synthesis.exists() else 0

    click.echo("\nFiles:")
    click.echo(f"  Raw:        {raw_count}")
    click.echo(f"  Processed:  {processed_count}")
    click.echo(f"  Synthesis:  {synthesis_count}")

    click.echo("\nQMD:")
    if search.is_available():
        click.echo("  Status: Installed")
        collections = search.list_collections()
        click.echo(f"  Collections: {len(collections)}")
    else:
        click.echo("  Status: Not installed")
        click.echo("  Install: npm install -g @tobilu/qmd")


if __name__ == "__main__":
    main()
