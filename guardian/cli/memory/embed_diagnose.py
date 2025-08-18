import os
import click

DEFAULT_PATH = os.getenv("CODEXIFY_CHROMA_PATH", "./.chroma")
DEFAULT_COLLECTION = os.getenv("CODEXIFY_COLLECTION", "codexify_vault")


@click.command(name="embed-diagnose")
@click.option("--path", default=DEFAULT_PATH, show_default=True, help="Chroma persistence path.")
@click.option("--collection", default=DEFAULT_COLLECTION, show_default=True, help="Chroma collection name.")
def embed_diagnose(path: str, collection: str):
    """Quick health check for your embedding index (Chroma)."""
    try:
        import chromadb
    except ImportError:
        click.echo("chromadb not installed. `pip install chromadb`")
        raise SystemExit(1)

    client = chromadb.PersistentClient(path=path)
    coll = client.get_or_create_collection(name=collection)
    count = coll.count()
    click.echo(f"Collection: {collection}\nPath: {path}\nDocs: {count}")

