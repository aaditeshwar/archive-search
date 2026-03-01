"""CLI for index build and update."""

import click

from src.indexer.index_pipeline import run_pipeline


@click.group()
def main() -> None:
    """Archive indexer: build or update the search index from the mailing list."""
    pass


@main.command("update")
@click.option("--group-url", default=None, help="Google Group URL (default from env GROUP_URL)")
@click.option("--load-urls-from-file", is_flag=True, help="Whether to scrape topic URLs or not")
@click.option("--skip-linked", is_flag=True, help="Do not fetch or index linked articles/PDFs")
@click.option("--limit", "limit_topics", type=int, default=None, help="Max topic pages to fetch (for testing)")
@click.option("--start-index", "start_index", type=int, default=None, help="Topic index to start from")
@click.option("--no-headless", is_flag=True, help="Show browser window (for debugging)")
def cmd_update(
    group_url: str | None,
    load_urls_from_file: bool,
    skip_linked: bool,
    limit_topics: int | None,
    start_index: int | None,
    no_headless: bool,
) -> None:
    """Incremental update: fetch new messages since last run and index them."""
    run_pipeline(
        full_rebuild=False,
        group_url=group_url,
        load_urls_from_file=load_urls_from_file,
        skip_linked=skip_linked,
        limit_topics=limit_topics,
        start_index=start_index,
        headless=not no_headless,
    )


@main.command("build")
@click.option("--full", "full_rebuild", is_flag=True, default=True, help="Full rebuild (default)")
@click.option("--group-url", default=None, help="Google Group URL (default from env GROUP_URL)")
@click.option("--load-urls-from-file", is_flag=True, help="Whether to scrape topic URLs or not")
@click.option("--skip-linked", is_flag=True, help="Do not fetch or index linked articles/PDFs")
@click.option("--limit", "limit_topics", type=int, default=None, help="Max topic pages to fetch (for testing)")
@click.option("--start-index", "start_index", type=int, default=None, help="Topic index to start from")
@click.option("--no-headless", is_flag=True, help="Show browser window (for debugging)")
def cmd_build(
    full_rebuild: bool,
    group_url: str | None,
    load_urls_from_file: bool,
    skip_linked: bool,
    limit_topics: int | None,
    start_index: int | None,
    no_headless: bool,
) -> None:
    """Build or rebuild the index. Use --full for full rebuild (default)."""
    run_pipeline(
        full_rebuild=full_rebuild,
        group_url=group_url,
        load_urls_from_file=load_urls_from_file,
        skip_linked=skip_linked,
        limit_topics=limit_topics,
        start_index=start_index,
        headless=not no_headless,
    )


if __name__ == "__main__":
    main()
