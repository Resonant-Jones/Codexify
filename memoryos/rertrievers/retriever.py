import click
from memoryos.embedders.local_embedder import LocalEmbedder
from memoryos.vector_store.vector_db import VectorDB
from memoryos.retrievers.retriever import Retriever

@click.command()
@click.argument("query")
@click.option("--top_k", default=5, help="Number of top results to return")
def retrieve(query, top_k):
    """Retrieve semantic memory entries based on a query."""
    embedder = LocalEmbedder()
    db = VectorDB()
    retriever = Retriever(db=db, embedder=embedder)
    
    results = retriever.retrieve(query, top_k=top_k)
    for i, (score, metadata) in enumerate(results):
        click.echo(f"{i+1}. Score: {score:.4f} | Metadata: {metadata}")
