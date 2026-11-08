import os
import ast
from typing import Any

def chunk_py(code: str) -> list[dict[str, Any]]:
    tree = ast.parse(code)
    chunks: list[dict[str, Any]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            start = node.lineno
            end = node.end_lineno

            lines = code.splitlines()
            chunk = '\n'.join(lines[start - 1:end])

            chunks.append({
                "type": type(node).__name__,
                "name": node.name,
                "start_line": start,
                "end_line": end,
                "content": chunk
            })
    return chunks


if __name__ == "__main__":
    with open("src/chunking/index.py") as f:
        code = f.read()
    chunks = chunk_py(code)
    for i, c in enumerate(chunks):
        print(f"\nChunk {i}\n\n{c['content']}")
