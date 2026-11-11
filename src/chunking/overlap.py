from typing import List


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


def recursive_split(
    text: str,
    max_size: int = 2000,
    overlap: int = 200,
    separators: list[str] | None = None,
) -> list[str]:

    if separators is None:
        separators = ["\n\n", "\n", ". ", " "]

    effective_max_size = max_size - overlap

    def split(text: str) -> list[str]:

        if len(text) <= effective_max_size:
            return [text] if text.strip() else []

        for sep in separators:
            parts = text.split(sep)

            if len(parts) == 1:
                continue

            chunks: list[str] = []
            current = ""

            for part in parts:
                candidate = f"{current}{sep}{part}" if current else part

                if len(candidate) <= effective_max_size:
                    current = candidate

                else:
                    if current:
                        chunks.append(current)

                    if len(part) > effective_max_size:
                        chunks.extend(split(part))
                        current = ""
                    else:
                        current = part

            if current:
                chunks.append(current)

            return chunks

        return [
            text[i:i + effective_max_size]
            for i in range(0, len(text), effective_max_size)
        ]

    chunks = split(text[:])

    if overlap <= 0:
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    result: list[str] = []

    for i, chunk in enumerate(chunks):

        if i == 0:
            result.append(chunk.strip())
            continue

        previous = chunks[i - 1]
        prefix = previous[-overlap:]

        result.append((prefix + chunk).strip())

    return result


def recursive_text_split(text: str, max_size: int = 2000, overlap: int = 200):
    return recursive_split(
        text,
        max_size,
        overlap,
        ["\n\n", "\n", ". ", " "]
    )


def recursive_py_split(text: str, max_size: int = 2000, overlap: int = 200):
    return recursive_split(
        text,
        max_size,
        overlap,
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
