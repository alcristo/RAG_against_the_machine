import re
import markdown_it as mdit
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


def markdown_chunk(content: str) -> None:
    # chunks: list[Any] = []

    parser = mdit.MarkdownIt()
    parsed_content = parser.parse(content)
    for i in parsed_content:
        d = i.as_dict()
        if d["type"] == "inline":
            print(d)

    # return chunks


def extract_markdown(markdown: str) -> list[dict[str, Any]]:
    md = mdit.MarkdownIt("commonmark", {"html": False})
    #md.enable("table")

    tokens = md.parse(markdown)

    blocks: list[dict[str, Any]] = []
    heading_stack = []
    pending_heading = None
    current_type = None

    for token in tokens:

        # Detect headings
        if token.type == "heading_open":
            pending_heading = int(token.tag[1])

        # Extract heading text
        elif token.type == "inline":

            content = token.content

            if pending_heading is not None:
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

            elif content.strip():
                blocks.append({
                    "type": current_type or "paragraph",
                    "content": content,
                    "heading": " > ".join(
                        h["title"] for h in heading_stack
                    ),
                    "lines": token.map
                })

        # Extract code blocks
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
