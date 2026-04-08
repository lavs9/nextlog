"""CLI for NextLog."""

from pathlib import Path

import click

from .config import load_config
from .processor import Processor


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
    # TODO: Implement fetch logic
    click.echo("Fetch command not yet implemented")


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

    # Ensure folders exist
    config.inbox_processed.mkdir(parents=True, exist_ok=True)

    processor = Processor(config)
    count = processor.process_all(limit=limit)

    click.echo(f"Processed {count} items.")


@main.command()
@click.pass_context
def synthesize(ctx):
    """Synthesize processed items into notes."""
    config = ctx.obj["config"]
    click.echo("Synthesizing notes...")
    click.echo(f"Processed: {config.inbox_processed}")
    click.echo(f"Synthesis: {config.synthesis}")
    # TODO: Implement synthesize logic
    click.echo("Synthesize command not yet implemented")


@main.command()
@click.argument("query")
@click.option("--limit", "-n", default=5, help="Number of results")
@click.pass_context
def search(ctx, query, limit):
    """Search using QMD."""
    click.echo(f"Searching for: {query}")
    # TODO: Implement search via QMD
    click.echo("Search command not yet implemented")


@main.command()
@click.option("--limit", "-l", type=int, help="Limit items to process")
@click.pass_context
def run(ctx, limit):
    """Run full pipeline: fetch + process + synthesize."""
    config = ctx.obj["config"]
    click.echo("Running full pipeline...")
    click.echo(f"Vault: {config.vault_path}")

    # Fetch
    click.echo("\n[1/3] Fetching bookmarks...")
    # TODO: Call fetch

    # Process
    click.echo("\n[2/3] Processing inbox...")
    # TODO: Call process

    # Synthesize
    click.echo("\n[3/3] Synthesizing notes...")
    # TODO: Call synthesize

    click.echo("\nDone!")


@main.command()
@click.pass_context
def status(ctx):
    """Show status."""
    config = ctx.obj["config"]

    click.echo("NextLog Status")
    click.echo("=" * 40)
    click.echo(f"Vault:     {config.vault_path}")
    click.echo(f"Inbox raw:     {config.inbox_raw}")
    click.echo(f"Inbox processed: {config.inbox_processed}")
    click.echo(f"Synthesis:  {config.synthesis}")
    click.echo(f"Ref:        {config.ref}")

    # Count files
    raw_count = len(list(config.inbox_raw.glob("*.md"))) if config.inbox_raw.exists() else 0
    processed_count = (
        len(list(config.inbox_processed.glob("*.md"))) if config.inbox_processed.exists() else 0
    )
    synthesis_count = len(list(config.synthesis.rglob("*.md"))) if config.synthesis.exists() else 0

    click.echo("\nFiles:")
    click.echo(f"  Raw:        {raw_count}")
    click.echo(f"  Processed:  {processed_count}")
    click.echo(f"  Synthesis:  {synthesis_count}")


if __name__ == "__main__":
    main()
