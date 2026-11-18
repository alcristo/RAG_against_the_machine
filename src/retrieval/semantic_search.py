import numpy as np
from typing import List, Dict, Any, Optional


class SemanticSearch:

    def __init__(self, chunks: Optional[List[Any]] = None) -> None:
        if chunks:
            self.chunks = chunks
            self.contents = [c.content for c in chunks]
        else:
            self.chunks, self.contents = [], []
        from static_embed_runner import StaticEmbedRunner
        self.model = StaticEmbedRunner.load(
            "sentence-transformers/static-retrieval-mrl-en-v1"
        )
        self.embeddings: Any = None

    def generate_embeddings(self):
        self.embeddings = self.model.encode(self.contents)
        print(f"Embeddings generated; size: {self.embeddings.shape}")

    def save(self, path: str = "data/processed/embeddings.npy") -> None:
        np.save(path, self.embeddings)

    def load(self, path: str = "data/processed/embeddings.npy") -> None:
        self.embeddings = np.load(path)

    def search(self, query: str) -> List[Dict[str, Any]]:
        if self.embeddings is None:
            raise ValueError("Embeddings have not been generated.")

        query_embedding = self.model.encode(query)

        # calculate cosines with dot product
        scores = np.dot(self.embeddings, query_embedding)

        indices = np.argsort(scores)[::-1]

        return [
            {
                "chunk": i,  # self.chunks[i].id,
                "score": float(scores[i])
            }
            for i in indices
        ]
