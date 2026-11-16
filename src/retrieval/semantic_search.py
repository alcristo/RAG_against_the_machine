import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any


class SemanticSearch:

    def __init__(self, chunks: List[Any] = []) -> None:
        self.chunks = chunks
        self.model: Any = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            device="cpu"
        )
        self.embeddings: Any = self.model.encode(
            chunks,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True
        )

    def save(self, path: str = "data/processed/embeddings.npy") -> None:
        np.save(path, self.embeddings)

    def load(self, path: str = "data/processed/embeddings.npy") -> None:
        self.embeddings = np.load(path)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        # calculate cosines with dot product
        scores = np.dot(self.embeddings, query_embedding)

        indices = np.argsort(scores)[::-1][:top_k]

        return [
            {
                "document": self.chunks[i],
                "score": float(scores[i])
            }
            for i in indices
        ]
