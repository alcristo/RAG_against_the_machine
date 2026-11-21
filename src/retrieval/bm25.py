import re
from math import log
from typing import Any, List, Tuple, Dict


class BM25:

    def __init__(
        self,
        chunks: Dict[str, Dict[str, Any]],
        index: Dict[str, Dict[str, int]],
        document_lengths: Dict[str, int]
    ) -> None:
        self.chunks = chunks
        self.index = index
        self.lengths = document_lengths
        self.n = len(document_lengths)
        self.avgdl = sum(document_lengths.values()) / self.n

    def tokenize_string(self, text: str) -> List[Any]:
        """text = text.lower().replace('_', ' ')
        return re.findall(r"\b\w+\b", text.lower())"""
        text = text.lower()
        tokens = re.findall(r"[a-zA-Z0-9_]+", text)
        result: List[Any] = []
        for token in tokens:
            result.append(token)

            # extract underscore-separated components
            if "_" in token:
                result.extend(token.split("_"))
        return result

    def tf(self, term: str, chunk_id: int,) -> int:
        return self.index.get(term, {}).get(str(chunk_id), 0)

    def df(self, term: str) -> int:
        return len(self.index.get(term, {}))

    def idf(self, term: str) -> float:
        df = self.df(term)
        return log(1 + (self.n - df + .5) / (df + .5))

    def chunk_score(
        self,
        query: str,
        chunk_id: int,
        k1: float = 1.5,
        b: float = .75
    ) -> float:
        if b < 0 or b > 1:
            b = .75
        query_terms = self.tokenize_string(query)
        score = 0.
        for term in query_terms:
            f = self.tf(term, chunk_id)
            dl = self.lengths[str(chunk_id)]
            score += self.idf(term) * (
                f * (k1 + 1) / (f + k1 * (1 - b + b * dl / self.avgdl))
            )
        return score

    def sorted_scores(
        self,
        query: str,
        # k: int = 5,
        k1: float = 1.5,
        b: float = .75
    ) -> Dict[int, float]:

        if b < 0 or b > 1:
            b = .75
        scores: List[Tuple[float, int]] = []
        for chunk_id in self.lengths:
            scores.append((self.chunk_score(
                query, int(chunk_id), k1, b
            ), int(chunk_id)))
        scores.sort(reverse=True)
        return {chunk_id: score for score, chunk_id in scores}
        """if b < 0 or b > 1:
            b = .75
        candidates: set[int] = set()
        for term in self.tokenize_string(query):
            candidates.update(
                int(chunk_id) for chunk_id in self.index.get(term, {})
            )
        scores: List[Tuple[float, int]] = []
        for chunk_id in candidates:
            scores.append((self.chunk_score(
                query, int(chunk_id), k1, b
            ), int(chunk_id)))
        scores.sort(reverse=True)
        return {chunk_id: score for score, chunk_id in scores}"""
