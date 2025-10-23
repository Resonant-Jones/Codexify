from guardian.vector_store import VectorStore

# Vector store scoring
vs = VectorStore()

dummy_embedding = [0.1] * 768  # Replace with real encoder output
results = vs.search(query_embedding=dummy_embedding, top_k=1)

vector_match_score = results[0]['score'] if results else 0.0

context_runtime_digest = {
    "system_status": system_status,
    "epistemic_check": {
        **epistemic_check,
        "vector_match_score": vector_match_score,
    },
    "timestamp": timestamp
}
