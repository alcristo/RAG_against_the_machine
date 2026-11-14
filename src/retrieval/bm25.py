import re
from math import log
from typing import Any, List, Tuple, Dict
import nltk
from nltk.stem import WordNetLemmatizer


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
        nltk.download("wordnet")
        self.lemmatizer = WordNetLemmatizer()

    def tokenize_string(self, text: str) -> List[Any]:
        text = text.lower().replace('_', ' ')
        tokens = re.findall(r"\b\w+\b", text.lower())
        return [self.lemmatizer.lemmatize(token) for token in tokens]

    def tokenize_terms(self, terms: List[str]) -> List[Any]:
        return [self.lemmatizer.lemmatize(token) for token in terms]

    def tf(self, term: str, chunk_id: int,) -> int:
        return self.index[term].get(str(chunk_id), 0)

    def df(self, term: str) -> int:
        return len(self.index[term])

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
        k: int = 5,
        k1: float = 1.5,
        b: float = .75
    ) -> Dict[int, float]:
        if b < 0 or b > 1:
            b = .75
        scores: List[Tuple[float, int]] = []
        for i in range(self.n):
            scores.append((self.chunk_score(
                query, i, k1, b
            ), i))
        scores.sort(reverse=True)
        scores_dict: Dict[int, float] = {}
        for i in range(k):
            score, chunk = scores[i]
            scores_dict.update({chunk: score})
        return scores_dict
