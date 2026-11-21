from tqdm import tqdm
from markdown_it import MarkdownIt
from markdown_it.token import Token
import ast
from typing import List, Tuple, Dict, Any


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
        context: str = "",
        max_chars: int = 2000
    ) -> None:
        if any((
            len(content) > max_chars,
            end_index - start_index - 1 > max_chars
        )):
            raise ValueError(f"chunk exceeds maximum size of {max_chars}")
        self.id = chunk_id
        self.document = doc_id
        self.content = content
        self.start_index = start_index
        self.end_index = end_index
        self.context = context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "file": self.document,
            "content": self.content,
            "start_index": self.start_index,
            "end_index": self.end_index,
        }

    def dump(self, chunk_dict: Dict[int, Dict[str, Any]]) -> None:
        chunk_dict[self.id] = {
            "file": self.document,
            "context": self.context,
            "start_index": self.start_index,
            "end_index": self.end_index
        }


class Unit:
    def __init__(
        self,
        start_index: int,
        end_index: int,
        content: str,
        context: str = "",
        unit_type: str = ""
    ) -> None:
        self.start_index = start_index
        self.end_index = end_index
        self.content = content
        self.context = context
        self.unit_type = unit_type


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

            # Desired overlap.
            new_start = previous_end - overlap

            # Never exceed max_size.
            new_start = max(new_start, end - max_size)

            # Never move beyond the original chunk start.
            start = min(start, new_start)

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
    for content, start, end in contents:

        assert len(content) <= max_size
        assert content == txt[start:end]
        assert 0 <= start < end <= len(txt)

        chunks.append(Chunk(
            chunk_id=nxt_id,
            doc_id=filename,
            content=content,
            start_index=start,
            end_index=end
        ))
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


def build_line_offsets(source: str) -> List[int]:
    offsets = [0]

    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    return offsets


def ast_position_to_char_offset(
        source: str,
        line_offsets: List[int],
        lineno: int,
        byte_col: int
) -> int:
    lines = source.splitlines(keepends=True)
    line = lines[lineno - 1]
    char_col = len(line.encode("utf-8")[:byte_col].decode("utf-8"))
    return line_offsets[lineno - 1] + char_col


def extract_node_positions(filename: str, chunks: List[Chunk], chunk_id: int):
    with open(filename) as f:
        source = f.read()
    tree = ast.parse(source)
    line_offsets = build_line_offsets(source)
    chunk_id = len(chunks)
    for node in ast.walk(tree):
        if isinstance(node, (
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef
        )):
            start = ast_position_to_char_offset(
                source, line_offsets, node.lineno, node.col_offset
            )
            end = ast_position_to_char_offset(
                source, line_offsets, node.end_lineno, node.end_col_offset
            )
            chunks.append(Chunk(
                chunk_id, filename, source[start:end], start, end
            ))
            chunk_id += 1


def extract_md_positions(filename: str, chunks: List[Chunk], chunk_id: int):
    with open(filename) as f:
        source = f.read()
    md = MarkdownIt()
    tokens = md.parse(source)
    line_offsets = build_line_offsets(source)
    for token in tokens:
        if token.map is None:
            continue

        start_line, end_line = token.map[:2]
        start = line_offsets[start_line]
        end = line_offsets[end_line]
        chunks.append(Chunk(
            chunk_id, filename, source[start:end], start, end
        ))
        chunk_id += 1


def split_oversized_unit(
    source: str,
    start: int,
    end: int,
    max_chars: int = 2000
):
    while end - start > max_chars:
        limit = start + max_chars

        split_at = source.rfind("\n", start, limit)

        if split_at <= start or split_at < start + max_chars // 2:
            split_at = limit
        else:
            split_at += 1

        yield start, split_at
        start = split_at

    if start < end:
        yield start, end


def create_chunks(
    source: str,
    doc_id: str,
    units: List[Dict[str, Any]],
    chunk_id: int,
    max_chars: int = 2000
) -> List[Chunk]:
    chunks: List[Chunk] = []

    # sort units by original position
    units = sorted(units, key=lambda x: x["start"])

    # split oversized semantic units
    split_units = []
    for unit in units:
        start = unit["start"]
        end = unit["end"]

        if end - start <= max_chars:
            split_units.append(unit)
            continue

        for part_start, part_end in split_oversized_unit(
            source, start, end, max_chars
        ):
            split_units.append({
                **unit,
                "start": part_start,
                "end": part_end
            })

    # assemble chunks
    current_start, current_end = None, None
    current_context = []
    for unit in split_units:
        start = unit["start"]
        end = unit["end"]

        if current_start is None:
            current_start = start
            current_end = end
            current_context = [unit.get("context", "")]
            continue

        # check source span
        if end - current_start <= max_chars:
            current_end = max(current_end, end)
            current_context.append(unit.get("context", ""))
        else:
            chunks.append(Chunk(
                chunk_id,
                doc_id,
                source[current_start:current_end],
                current_start,
                current_end,
                " ".join(filter(None, current_context))
            ))
            chunk_id += 1
            current_start = start
            current_end = end
            current_context = [unit.get("context", "")]

    # last chunk
    if current_start is not None:
        chunks.append(Chunk(
            chunk_id,
            doc_id,
            source[current_start:current_end],
            current_start,
            current_end,
            " ".join(filter(None, current_context))
        ))
    return chunks


"""def get_python_units(source: str) -> List[Unit]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    line_offsets = build_line_offsets(source)

    def get_position(node: ast.stmt) -> Tuple[int, int]:
        start = ast_position_to_char_offset(
            source,
            line_offsets,
            node.lineno,
            node.col_offset
        )
        end = ast_position_to_char_offset(
            source,
            line_offsets,
            node.end_lineno,
            node.end_col_offset
        )
        return start, end
    units: List[Unit] = []
    for node in tree.body:

        # Class:
        if isinstance(node, ast.ClassDef):
            class_start, class_end = get_position(node)
            for child in node.body:
                if isinstance(child, (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef
                )):
                    start, end = get_position(child)
                    context = (
                        f"Class: {node.name} | "
                        f"Method: {child.name}"
                    )
                    units.append(Unit(
                        start, end, source[start:end], context, "method"
                    ))

            # no methods
            if not any(
                isinstance(child, (ast.FunctionDef)) for child in node.body
            ):
                units.append(Unit(
                    class_start,
                    class_end,
                    source[class_start:class_end],
                    f"Class: {node.name}"
                ))

        # function
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start, end = get_position(node)

            units.append(Unit(
                start,
                end,
                source[start:end],
                f"Function {node.name}",
                "function"
            ))

        # other (imports, constants, docstrings, ...)
        else:
            start, end = get_position(node)

            units.append(Unit(
                start,
                end,
                source[start:end],
                "Module",
                "module"
            ))
    return sorted(units, key=lambda u: u.start_index)"""


def get_python_units(source: str) -> List[Unit]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines(keepends=True)
    line_offsets = build_line_offsets(source)

    units: List[Unit] = []

    def position_to_offset(lineno: int, byte_col: int) -> int:
        line = lines[lineno - 1]
        char_col = len(line.encode("utf-8")[:byte_col].decode("utf-8"))
        return line_offsets[lineno - 1] + char_col

    def get_position(node: ast.stmt) -> Tuple[int, int]:
        start_line = node.lineno
        end_line = node.end_lineno

        decorators = getattr(node, "decorator_list", [])

        if decorators:
            start_line = min(
                start_line, *(decorator.lineno for decorator in decorators)
            )

        start = position_to_offset(
            start_line,
            0 if start_line != node.lineno else node.col_offset
        )
        end = position_to_offset(end_line, node.end_col_offset)
        return start, end

    def add_unit(node: ast.stmt, context: str, unit_type: str) -> None:
        start, end = get_position(node)

        if start >= end:
            return

        units.append(Unit(start, end, source[start:end], context, unit_type))

    def is_function(node: ast.stmt) -> bool:
        return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))

    def visit_function(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parents: List[str]
    ) -> None:
        name: str = node.name

        context_parts = parents + [f"Function: {name}"]
        context = " > ".join(context_parts)

        # index the complete function
        add_unit(node, context, "function")

        # nested functions and classes
        for child in node.body:
            if is_function(child):
                visit_function(child, context_parts)
            elif isinstance(child, ast.ClassDef):
                visit_class(child, context_parts)

    def visit_class(node: ast.ClassDef, parents: List[str]) -> None:
        context_parts = parents + [f"Class: {node.name}"]
        context = " > ".join(context_parts)

        # preserve class declaration; no method duplication
        if node.body:
            first_start, _ = get_position(node.body[0])
            class_start, _ = get_position(node)

            if class_start < first_start:
                units.append(Unit(
                    class_start,
                    first_start,
                    source[class_start:first_start],
                    context,
                    "class_header"
                ))
        else:
            add_unit(node, context, "class")

        # visit direct class members
        for child in node.body:
            if is_function(child):
                visit_function(child, context_parts)
            elif isinstance(child, ast.ClassDef):
                visit_class(child, context_parts)
            else:
                # class attributes, docstrings, etc.
                add_unit(child, context, "class_member")

    # module-level statements
    for node in tree.body:
        if is_function(node):
            visit_function(node, [])
        elif isinstance(node, ast.ClassDef):
            visit_class(node, [])
        else:
            # imports, constants, assignments, module docstrings, etc.
            add_unit(node, "Module", "module")

    return sorted(units, key=lambda unit: (unit.start_index, unit.end_index))


"""def get_markdown_units(source: str) -> List[Unit]:

    md = MarkdownIt()
    tokens = md.parse(source)
    line_offsets = build_line_offsets(source)

    heading_stack: List[Tuple[int, str]] = []
    units: List[Unit] = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        # identify headings
        if token.type == "heading_open":
            level = int(token.tag[1])
            # return to a higher level: remove all lower levels
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            inline_token = tokens[i + 1]
            heading = inline_token.content
            heading_stack.append((level, heading))
            i += 1
            continue

        # meaningful Markdown blocks
        if token.map is not None and token.type in (
            "paragraph_open", "fence", "code_block", "html_block"
        ):
            start_line, end_line = token.map[:2]
            start = line_offsets[start_line]
            end = line_offsets[end_line]
            content = source[start:end]
            context = " > ".join(heading for _, heading in heading_stack)
            units.append(Unit(
                start, end, content, context, token.type
            ))
        i += 1

    return units"""


def get_markdown_units(source: str) -> List[Unit]:

    md = MarkdownIt().enable("table")
    tokens = md.parse(source)

    line_offsets = build_line_offsets(source)
    heading_stack: List[Tuple[int, str]] = []
    units: List[Unit] = []
    i = 0

    # extract as complete blocks
    containers = {
        "bullet_list_open": "list",
        "ordered_list_open": "list",
        "blockquote_open": "blockquote",
        "table_open": "table"
    }

    # individual blocks
    blocks = {
        "paragraph_open": "paragraph",
        "fence": "code",
        "code_block": "code",
        "htlm_block": "html"
    }

    def add_unit(token: Token, context: str, unit_type: str) -> None:
        if token.map is None:
            return

        start_line, end_line = token.map
        start = line_offsets[start_line]
        end = line_offsets[end_line]

        if start >= end:
            return

        units.append(Unit(start, end, source[start:end], context, unit_type))

    i = 0

    while i < len(tokens):
        token = tokens[i]

        # update heading hierarchy
        if token.type == "heading_open":
            level = int(token.tag[1])

            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()

            heading = tokens[i + 1].content

            heading_stack.append((level, heading))

            i += 1
            continue

        context = " > ".join([head for _, head in heading_stack])

        # extract containers
        if token.type in containers:
            unit_type = containers[token.type]

            add_unit(token, context, unit_type)

            # skip nested tokens until closing token
            depth = 1
            opening_type = token.type
            closing_type = opening_type.replace("_open", "_close")

            i += 1

            while i < len(tokens) and depth > 0:
                current = tokens[i]

                if current.type == opening_type:
                    depth += 1
                elif current.type == closing_type:
                    depth -= 1

                i += 1

            continue

        # individual blocks
        if token.type in blocks:
            add_unit(token, context, blocks[token.type])

        i += 1

    return sorted(units, key=lambda unit: unit.start_index)


def assemble_chunks(
    source: str,
    doc_id: str,
    units: List[Unit],
    chunk_id: int,
    max_chars: int = 2000,
    overlap_units: int = 1
) -> List[Chunk]:
    chunks: List[Chunk] = []
    current_units: List[Unit] = []
    # chunk_id = 0

    def save_chunk():
        nonlocal chunk_id
        if not current_units:
            return

        start = current_units[0].start_index
        end = current_units[-1].end_index
        content = source[start:end]
        if len(content) > max_chars:
            raise ValueError(
                f"Chunk {chunk_id} exceeds maximum size: "
                f"{len(content)} > {max_chars}"
            )
        contexts = list(Dict.fromkeys(
            unit.context for unit in current_units if unit.context
        ))
        context = " | ".join(contexts)
        chunks.append(Chunk(
            chunk_id, doc_id, content, start, end, context, max_chars
        ))
        chunk_id += 1

    for unit in units:

        # oversized units: split
        if len(unit.content) > max_chars:

            # save previously accumulated units
            save_chunk()
            current_units = []

            # split unit
            for start, end in split_oversized_unit(
                source, unit.start_index, unit.end_index, max_chars
            ):
                split_unit = Unit(
                    start,
                    end,
                    source[start:end],
                    unit.context,
                    unit.unit_type
                )
                current_units.append(split_unit)
                save_chunk()
                current_units = []
            continue
        if not current_units:
            current_units.append(unit)
            continue
        candidate_start = current_units[0].start_index
        candidate_end = unit.end_index
        candidate_size = candidate_end - candidate_start
        same_context = current_units[-1].context == unit.context
        if candidate_size <= max_chars and same_context:
            current_units.append(unit)
        else:
            previous_units = current_units.copy()
            save_chunk()

            overlap: List[Unit] = []
            for previous in reversed(previous_units):
                if len(overlap) >= overlap_units:
                    break

                candidate_overlap = [previous] + overlap

                overlap_start = candidate_overlap[0].start_index
                overlap_size = unit.end_index - overlap_start

                if overlap_size > max_chars:
                    break

                overlap = candidate_overlap

            # start new chunk with overlap
            current_units = overlap + [unit]

    save_chunk()

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
            content=chunk[0],
            start_index=sum([len(t) for t in raw[:i]]),
            end_index=sum([len(t) for t in raw[:i]]) + len(chunk[0]),
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
