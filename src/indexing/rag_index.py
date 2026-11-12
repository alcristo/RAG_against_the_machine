from tqdm import tqdm
import re
from typing import Any, List, Dict, Tuple


def tokenize(text: str) -> List[Any]:
    return re.findall(r"\b\w+\b", text.lower())


def build_index(
    chunks: List[Any]
) -> Tuple[Dict[str, Dict[str, int]], Dict[int, int]]:
    inverted_index: Dict[str, Dict[str, int]] = {}
    document_lengths: Dict[int, int] = {}
    bar = tqdm(
        range(len(chunks)),
        desc="Indexing chunks",
        unit="chunks"
    )
    for i in bar:
        c = chunks[i]
        c_id = c.id
        text = c.content
        tokens: List[str] = tokenize(text)
        document_lengths[c_id] = len(tokens)
        for token in tokens:
            if not inverted_index.get(token):
                inverted_index[token] = {}
            if str(c_id) not in inverted_index[token]:
                inverted_index[token][str(c_id)] = 0
            inverted_index[token][str(c_id)] += 1
    return dict(inverted_index), document_lengths
