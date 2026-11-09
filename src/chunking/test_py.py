import ast
from dataclasses import dataclass
from typing import Any, Protocol


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


@dataclass
class CodeChunk:
    name: str
    kind: str
    code: str
    start: int
    end: int
    context: str = ""


class LocatedNode(Protocol):

    @property
    def lineno(self) -> int: ...

    @property
    def end_lineno(self) -> int | None: ...

    @property
    def col_offset(self) -> int: ...

    @property
    def end_col_offset(self) -> int | None: ...


FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


class PythonChunker(ast.NodeVisitor):

    def __init__(self, source: str, max_size: int = 2000) -> None:
        self.source = source
        self.lines = source.splitlines(keepends=True)
        self.max_size = max_size
        self.chunks: list[CodeChunk] = []
        self.line_starts: list[int] = []
        offset = 0
        for line in self.lines:
            self.line_starts.append(offset)
            offset += len(line)

    def get_source(self, node: ast.AST) -> str | None:
        return ast.get_source_segment(self.source, node)

    def get_char_offsets(self, node: LocatedNode) -> tuple[int, int]:

        if node.end_lineno is None or node.end_col_offset is None:
            raise ValueError("AST node has no ending location")

        def byte_to_char(line: str, byte_offset: int) -> int:
            return len(line.encode("utf-8")[:byte_offset].decode("utf-8"))

        start_line = self.lines[node.lineno - 1]
        end_line = self.lines[node.end_lineno - 1]

        start = (
            self.line_starts[node.lineno - 1]
            + byte_to_char(start_line, node.col_offset)
        )
        end = (
            self.line_starts[node.end_lineno - 1]
            + byte_to_char(end_line, node.end_col_offset)
        )
        return start, end

    def extract_node(self, node: FunctionNode) -> str:
        start, end = self.get_char_offsets(node)
        return self.source[start:end]

    def add_chunk(self, name: str, kind: str, node: LocatedNode) -> None:
        start, end = self.get_char_offsets(node)
        self.chunks.append(
            CodeChunk(
                name=name,
                kind=kind,
                code=self.source[start:end],
                start=start,
                end=end
            )
        )

    def split_function(
        self,
        node: FunctionNode,
        class_name: str | None = None
    ) -> None:
        name = node.name
        if class_name:
            name = f"{class_name}.{name}"

        # small functions
        f_start, f_end = self.get_char_offsets(node)
        if f_end - f_start + 1 <= self.max_size:
            self.add_chunk(name, "function", node)
            return

        if not node.body:
            return

        # function signature (additional context)
        first_stmt_start, _ = self.get_char_offsets(node.body[0])
        context = self.source[f_start:first_stmt_start].strip()

        current_start: int | None = None
        current_end: int | None = None
        chunk_index = 0
        for stmt in node.body:
            stmt_start, stmt_end = self.get_char_offsets(stmt)

            if current_start is None or current_end is None:
                current_start = stmt_start
                current_end = stmt_end
                continue

            # measure character offset
            if stmt_end - current_start > self.max_size:
                chunk_index += 1
                self.chunks.append(
                    CodeChunk(
                        name=f"{name}.part_{chunk_index}",
                        kind="function_part",
                        code=self.source[current_start:current_end],
                        start=current_start,
                        end=current_end,
                        context=context
                    )
                )
                current_start = stmt_start
                current_end = stmt_end
            else:
                current_end = stmt_end

        # flush remains
        if current_start is not None and current_end is not None:
            chunk_index += 1
            self.chunks.append(
                CodeChunk(
                    name=f"{name}.part_{chunk_index}",
                    kind="function_part",
                    code=self.source[current_start:current_end],
                    start=current_start,
                    end=current_end,
                    context=context
                )
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.split_function(child, node.name)

            elif isinstance(child, ast.ClassDef):
                self.visit_ClassDef(child)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.split_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.split_function(node)


def chunk_python(source: str, max_size: int = 2000) -> list[CodeChunk]:
    tree = ast.parse(source)
    chunker = PythonChunker(source, max_size)
    chunker.visit(tree)
    return chunker.chunks


if __name__ == "__main__":
    with open("src/chunking/index.py") as f:
        code = f.read()
    chunks = chunk_py(code)
    for i, c in enumerate(chunks):
        print(f"\nChunk {i}\n\n{c['content']}")
