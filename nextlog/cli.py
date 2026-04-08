"""CLI for NextLog."""

from pathlib import Path

import click

from .config import load_config
from .processor import Processor
from .search import Search


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
@click.pass_context
def fetch(ctx):
    """Fetch X bookmarks."""
    config = ctx.obj["config"]
    click.echo("Fetching bookmarks from X...")
    click.echo(f"Vault: {config.vault_path}")
    click.echo("\nNote: This requires bird CLI configured in nextlog.json")
    click.echo("Set twitter.auth_token and twitter.ct0 in your config file.")
    click.echo("\nExample nextlog.json:")
    click.echo("""{
  "twitter": {
    "auth_token": "your_auth_token",
    "ct0": "your_ct0"
  }
}""")


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
    """Synthesize processed items into notes."""
    config = ctx.obj["config"]
    click.echo("Synthesizing notes...")
    click.echo(f"Processed: {config.inbox_processed}")
    click.echo(f"Synthesis: {config.synthesis}")

    config.synthesis.mkdir(parents=True, exist_ok=True)

    click.echo("\nNote: Synthesis with LLM not yet implemented.")
    click.echo("Coming soon: Topic identification and note generation.")


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
