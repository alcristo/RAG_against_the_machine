import re
from markdown_it import MarkdownIt
from typing import Any


def chunk_markdown(content: str) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    current_heading: list[str] = []
    current_content: list[str] = []

    for line in content.splitlines():

        if re.match(r"^#{1,6}\s", line):

            if current_content:
                chunks.append({
                    "heading": " > ".join(current_heading),
                    "content": "\n".join(current_content)
                })

            level = len(line) - len(line.lstrip("#"))
            heading = line.lstrip("#").strip()

            current_heading = current_heading[:level - 1]
            current_heading.append(heading)

            current_content = []

        else:
            current_content.append(line)

    if current_content:
        chunks.append({
            "heading": " > ".join(current_heading),
            "content": "\n".join(current_content)
        })

    return chunks


def divide_content(
    headings: dict[str, int],
    inline: str,
    chunk_size: int = 2000
) -> list[str]:
    if chunk_size > 2000:
        raise ValueError("maximum chunk size must be 2000 characters or lower")
    heads = ""
    for title, level in headings.items():
        head = "".join(["#" for _ in range(level)]) + ' ' + title
        heads += head + "\n"
    total_chunk = heads + inline
    if len(total_chunk) <= chunk_size:
        return [total_chunk]
    chunks: list[str] = []
    paragraphs = inline.split("\n\n")
    for p in paragraphs:
        p_chunk = heads + p
        if len(p_chunk) <= chunk_size:
            chunks.append(p_chunk)
            continue
        sentences = p.split(". ")
        for s in sentences:
            s_chunk = heads + s
            if len(s_chunk) <= chunk_size:
                chunks.append(s_chunk)
                continue
            words = s.split()
            for w in words:
                w_chunk = heads + w
                if len(w_chunk) <= chunk_size and w_chunk not in chunks:
                    chunks.append(w_chunk)
    return chunks


def extract_table(tokens: list[Any]) -> list[list[Any]]:
    i = 0
    while tokens[i].type not in ("thead_open", "tbody_open"):
        i += 1
    head: list[str] = []
    sep: list[str] = []
    table: list[Any] = []
    if i >= len(tokens):
        return table
    if tokens[i].type == "thead_open":
        while i < len(tokens) and tokens[i].type != "tr_open":
            i += 1
        while i < len(tokens) and tokens[i].type != "tr_close":
            if tokens[i].type == "inline":
                content: str = tokens[i].content
                head.append(content)
            i += 1
        head_l = len(head)
        for _ in range(head_l):
            sep.append('-')
        table.extend([head, sep])
        i += 2
    while tokens[i].type not in ("tbody_close", "table_close"):
        while i < len(tokens) and tokens[i].type != "tr_open":
            i += 1
        row: list[str] = []
        while i < len(tokens) and tokens[i].type != "tr_close":
            if tokens[i].type == "inline":
                content = tokens[i].content
                row.append(content)
            i += 1
        table.append(row)
        i += 1
    return table


def extract_markdown(markdown: str) -> list[dict[str, Any]]:
    md = MarkdownIt("commonmark", {"html": False})
    md.enable("table")

    tokens = md.parse(markdown)

    blocks: list[dict[str, Any]] = []
    heading_stack: list[dict[str, Any]] = []
    pending_heading = None
    current_type = None

    for i, token in enumerate(tokens):

        # detect headings
        if token.type == "heading_open":
            # heading open tags are h1, h2, h3, h4, h5, h6
            pending_heading = int(token.tag[1])

        # extract heading text
        elif token.type == "inline":

            content = token.content

            if pending_heading is not None:
                # content is heading
                level = pending_heading

                heading_stack = [
                    h for h in heading_stack
                    if h["level"] < level
                ]

                heading_stack.append({
                    "level": level,
                    "title": content
                })

                blocks.append({
                    "type": "heading",
                    "level": level,
                    "content": content
                })

                pending_heading = None

            elif current_type == "table":
                continue

            elif content.strip():
                # content is not heading
                blocks.append({
                    "type": current_type or "paragraph",
                    "content": content,
                    "heading": " > ".join(
                        h["title"] for h in heading_stack
                    ),
                    "lines": token.map
                })

        # extract code blocks
        elif token.type in ("fence", "code_block"):

            blocks.append({
                "type": "code",
                "language": token.info.strip(),
                "content": token.content,
                "heading": " > ".join(
                    h["title"] for h in heading_stack
                ),
                "lines": token.map
            })

        # extract table blocks
        elif token.type == "table_open":
            current_type = "table"
            tab_tokens: list[Any] = []
            j = i
            while tokens[j].type != "table_close":
                tab_tokens.append(tokens[j])
                j += 1
            table = extract_table(tab_tokens)
            tab_str = ""
            for row in table:
                row_str = "| " + " | ".join(row) + " |"
                tab_str += f"{row_str}\n"
            blocks.append({
                "type": "table",
                "content": tab_str.strip(),
                "heading": " > ".join(
                    h["title"] for h in heading_stack
                ),
                "lines": len(table) + 1
            })

        elif token.type == "paragraph_open":
            current_type = "paragraph"

        elif token.type == "list_item_open":
            current_type = "list_item"

    return blocks


if __name__ == "__main__":
    with open("/home/alcristo/cursus/mst3/Fly-in/README.md") as f:
        txt = f.read()

    blocks = extract_markdown(txt)
    for i, b in enumerate(blocks):
        print(f"Chunk {i}\n")
        print(f'{b}\n')
