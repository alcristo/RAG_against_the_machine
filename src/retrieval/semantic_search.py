import numpy as np
import json
from typing import List, Dict, Any, Optional


class SemanticSearch:

    def __init__(self, chunks: Optional[List[Any]] = None) -> None:
        self.chunk_ids: List[int] = []
        self.contents: List[str] = []
        if chunks:
            self.chunk_ids = [c.id for c in chunks]
            self.contents = [
                f"Document: {c.document.removeprefix('data/raw/vllm-0.10.1/')}"
                + "\n\n"
                + c.context
                + "\n\n"
                + c.content
                for c in chunks
            ]
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
        with open("data/processed/chunks.json") as f:
            chunk_dict = json.load(f)
            self.chunk_ids = [int(k) for k in chunk_dict.keys()]
        self.embeddings = np.load(path)

    def search(self, query: str) -> List[Dict[str, Any]]:
        if self.embeddings is None:
            raise ValueError("Embeddings have not been generated.")

        query_embedding = self.model.encode(query.lower().replace('_', ' '))

        # calculate cosines with dot product
        scores = np.dot(self.embeddings, query_embedding)

        # sort scores and reverse the list
        indices = np.argsort(scores)[::-1]

        return [
            {
                "chunk": self.chunk_ids[i],
                "score": float(scores[i])
            }
            for i in indices
        ]
