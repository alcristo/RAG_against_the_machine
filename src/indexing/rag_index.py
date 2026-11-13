from tqdm import tqdm
import re
from typing import Any, List, Dict, Tuple, Iterable


def tokenize(text: str) -> List[Any]:
    return re.findall(r"\b\w+\b", text.lower())


def build_index(
    chunks: List[Any], show_tqdm: bool = True
) -> Tuple[Dict[str, Dict[str, int]], Dict[int, int]]:
    inverted_index: Dict[str, Dict[str, int]] = {}
    document_lengths: Dict[int, int] = {}
    bar: Iterable[Any] = []
    if show_tqdm:
        bar = tqdm(
            range(len(chunks)),
            desc="Indexing chunks",
            unit="chunks"
        )
    else:
        bar = range(len(chunks))
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


def update_index(
    index: Dict[str, Dict[str, int]],
    lengths: Dict[int, int],
    new_chunks: List[Any]
) -> Tuple[Dict[str, Dict[str, int]], Dict[int, int]]:
    new_index, new_lengths = build_index(new_chunks, False)
    for k, v in new_index.items():
        if index.get(k):
            for c, t in new_index[k].items():
                index[k].update({c: t})
        else:
            index[k] = v
    for ch, l in new_lengths.items():
        lengths.update({ch: l})
    return index, lengths
