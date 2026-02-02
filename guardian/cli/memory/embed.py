import click

from guardian.runtime.embed.embedder import embed_file


@click.command(name="embed")
@click.option(
    "--path",
    default="chunked_docs.txt",
    show_default=True,
    help="Input file (chunks separated by blank lines).",
)
@click.option(
    "--use-openai/--use-local",
    default=True,
    show_default=True,
    help="Use OpenAI API or local model.",
)
@click.option(
    "--store",
    type=click.Choice(["chroma", "faiss"]),
    default="chroma",
    show_default=True,
    help="Vector store backend.",
)
@click.option(
    "--chroma-path",
    default="./.chroma",
    show_default=True,
    help="Chroma persistence path.",
)
@click.option(
    "--collection",
    default="codexify_vault",
    show_default=True,
    help="Chroma collection name.",
)
def embed(path, use_openai, store, chroma_path, collection):
    """Embed and index documents into the configured vector store."""
    result = embed_file(
        path=path,
        use_openai=use_openai,
        store=store,
        chroma_path=chroma_path,
        collection=collection,
    )
    click.echo(f"Embedded {result['count']} docs → store={result['store']}")
