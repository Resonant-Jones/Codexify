import faiss
import numpy as np
from typing import List, Tuple

class VectorDB:
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.data = []

    def add(self, vector: List[float], metadata: dict):
        vec_np = np.array([vector], dtype=np.float32)
        self.index.add(vec_np)
        self.data.append(metadata)

    def query(self, vector: List[float], top_k: int = 5) -> List[Tuple[float, dict]]:
        vec_np = np.array([vector], dtype=np.float32)
        D, I = self.index.search(vec_np, top_k)
        results = []
        for distance, idx in zip(D[0], I[0]):
            if idx < len(self.data):
                results.append((distance, self.data[idx]))
        return results