from tqdm import tqdm
from typing import List, Dict, Any


class Chunk:
    """
    Chunk class for storage of file contents.

    Args:
        chunk_id: The chunk ID.
        doc_id: The document ID.
        content: The stored content.
        metadata: Metadata dictionary (default is empty).
    """

    def __init__(
        self,
        chunk_id: int,
        doc_id: str,
        content: str,
        start_index: int,
        end_index: int,
        context: str = ""
    ) -> None:
        self.id = chunk_id
        self.document = doc_id
        self.content = content
        self.start_index = start_index
        self.end_index = end_index
        self.context = context

    def dump(self, chunk_dict: Dict[int, Dict[str, Any]]) -> None:
        chunk_dict[self.id] = {
            "file": self.document,
            "start_index": self.start_index,
            "end_index": self.end_index
        }


def recursive_split(
    text: str,
    max_size: int = 2000,
    overlap: int = -1,
    separators: list[str] | None = None,
) -> list[tuple[str, int, int]]:

    if not text:
        return []

    if overlap < 0 or overlap > max_size // 5:
        overlap = max_size // 10

    if separators is None:
        separators = ["\n\n", "\n", ". ", " "]

    if max_size <= 0 or overlap >= max_size:
        raise ValueError("Invalid max_size or overlap")

    # Split into ordered, non-overlapping source intervals.
    def split(start: int, end: int, sep_idx: int):
        if end - start <= max_size:
            return [(start, end)]

        if sep_idx >= len(separators):
            return [
                (i, min(i + max_size, end))
                for i in range(start, end, max_size)
            ]

        sep = separators[sep_idx]
        boundaries = []
        pos = start

        while pos < end:
            pos = text.find(sep, pos, end)

            if pos == -1:
                break

            boundaries.append(pos + len(sep))
            pos += len(sep)

        if not boundaries:
            return split(start, end, sep_idx + 1)

        pieces = []
        piece_start = start

        for boundary in boundaries:
            if boundary - piece_start <= max_size:
                continue

            # Use the last separator before the size limit.
            candidates = [
                b for b in boundaries
                if piece_start < b <= piece_start + max_size
            ]

            if not candidates:
                return split(start, end, sep_idx + 1)

            cut = candidates[-1]

            pieces.extend(split(piece_start, cut, sep_idx + 1))
            piece_start = cut

        if piece_start < end:
            pieces.extend(split(piece_start, end, sep_idx + 1))

        return pieces

    # Generate semantic, non-overlapping pieces.
    pieces = split(0, len(text), 0)

    # Merge adjacent pieces, respecting the maximum size.
    merged = []
    current_start = None
    current_end = None

    for start, end in pieces:
        if current_start is None:
            current_start, current_end = start, end

        elif end - current_start <= max_size:
            current_end = end

        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end

    if current_start is not None:
        merged.append((current_start, current_end))

    # Introduce overlap without exceeding max_size.
    result = []

    for i, (start, end) in enumerate(merged):
        if i > 0:
            previous_end = merged[i - 1][1]
            start = max(start, previous_end - overlap)

        assert end - start <= max_size

        result.append((text[start:end], start, end))

    return result


def recursive_text_split(
    text: str,
    max_size: int = 2000,
    overlap: int = -1
):
    return recursive_split(
        text, max_size, overlap,
        ["\n\n", "\n", ". ", " "]
    )


def recursive_py_split(
    text: str,
    max_size: int = 2000,
    overlap: int = -1
):
    return recursive_split(
        text, max_size, overlap,
        ["\n\n\n", "\n\n", "\n", ". ", " "]
    )


def merge_small_chunks(
    chunks: list[str],
    max_size: int = 2000,
    min_size: int = 500,
) -> list[str]:

    if not chunks:
        return []

    result: list[str] = []
    current = chunks[0]

    for chunk in chunks[1:]:

        if (
            len(current) < min_size
            and len(current) + len(chunk) <= max_size
        ):
            current += "\n" + chunk

        else:
            result.append(current)
            current = chunk

    result.append(current)

    return result


def merge_chunks_no_context(
    chunks: list[str],
    max_size: int = 2000
) -> list[str]:

    result: list[str] = []
    current = ""

    for chunk in chunks:
        candidate = current + "\n" + chunk if current else chunk

        if len(candidate) <= max_size:
            current = candidate
        else:
            if current:
                result.append(current)
            current = chunk

    if current:
        result.append(current)

    return result


def merge_chunks(chunks: List[Chunk], max_size: int = 2000) -> List[Chunk]:
    if not chunks:
        return []

    result = [chunks[0]]
    current = chunks[0]
    for chunk in chunks[1:]:

        can_merge = all((
            current.document == chunk.document,
            current.context == chunk.context,
            current.end_index == chunk.start_index
        ))
        merged_content = current.content + chunk.content

        if can_merge and len(merged_content) <= max_size:
            current.content += chunk.content
            current.end_index = chunk.end_index
        else:
            result.append(chunk)
            current = chunk
    return result


def add_overlap(
    chunks: List[Chunk],
    overlap_size: int = 200,
) -> List[Chunk]:
    result: List[Chunk] = []
    for i, chunk in enumerate(chunks):
        content = chunk.content
        if i > 0:
            previous = chunks[i - 1]
            if all((
                previous.document == chunk.document,
                previous.end_index == chunk.start_index
            )):
                overlap = previous.content[-overlap_size:]
                content = overlap + content
        result.append(Chunk(
            chunk_id=chunk.id,
            doc_id=chunk.document,
            content=content,
            start_index=chunk.start_index,
            end_index=chunk.start_index + len(content),
            context=chunk.context
        ))
    return result


def chunk_one_file(
    filename: str,
    nxt_id: int,
    max_size: int = 2000
) -> List[Chunk]:
    chunks: List[Chunk] = []
    with open(filename) as f:
        txt = f.read()
    if filename.endswith(".py"):
        contents = recursive_py_split(txt)
    else:
        contents = recursive_text_split(txt)
    current_index = 0
    for c in contents:
        if not c.strip():
            current_index += len(c)
            continue
        if len(c) > max_size:
            raise AttributeError(
                f"Chunking error in {filename}:\n\n{c}"
            )
        chunks.append(Chunk(
            chunk_id=nxt_id,
            doc_id=filename,
            content=c,
            start_index=current_index,
            end_index=current_index + len(c)
        ))
        current_index += len(c)
        nxt_id += 1
    return chunks


def chunk_files(
    files: List[str],
    max_size: int = 2000,
    overlap: int = -1
) -> List[Chunk]:

    chunks: list[Chunk] = []
    chunk_id = 0

    for filepath in tqdm(files, desc="Chunking files", unit="files"):

        with open(filepath) as f:
            txt = f.read()

        if not txt:
            continue

        if filepath.endswith(".py"):
            contents = recursive_py_split(txt, max_size, overlap)
        else:
            contents = recursive_text_split(txt, max_size, overlap)

        for content, start, end in contents:

            assert len(content) <= max_size
            assert content == txt[start:end]
            assert 0 <= start < end <= len(txt)

            chunks.append(Chunk(
                chunk_id=chunk_id,
                doc_id=filepath,
                content=content,
                start_index=start,
                end_index=end
            ))

            chunk_id += 1

    return chunks


if __name__ == "__main__":
    filename = "src/chunking/index.py"
    with open(filename) as f:
        txt = f.read()
    raw = recursive_py_split(txt)
    print(f"{len(raw)} chunks parsed")
    chunks: List[Chunk] = []
    for i, chunk in enumerate(raw):
        chunks.append(Chunk(
            chunk_id=i,
            doc_id=filename,
            content=chunk,
            start_index=sum([len(t) for t in raw[:i]]),
            end_index=sum([len(t) for t in raw[:i]]) + len(chunk),
        ))
    for i, c in enumerate(chunks):
        # print(f"Chunk {i}\n\n{c.content}")
        if len(c.content) >= 2000:
            print("Chunk length violation")
    merged = merge_chunks(chunks)
    print(f"{len(merged)} chunks after merging")
    for i, c in enumerate(merged):
        # print(f"Chunk {i}\n\n{c.content}")
        if len(c.content) >= 2000:
            print("Chunk length violation")
