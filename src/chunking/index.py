from typing import List, Tuple, Dict, Any, Protocol
from dataclasses import dataclass
import sys


class ExtensionError(BaseException):
    pass


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
        metadata: Dict[str, Any] = {}
    ) -> None:
        self.id = chunk_id
        self.document = doc_id
        self.content = content
        self.metadata: Dict[str, Any] = metadata


class FileParser(Protocol):

    def parse(self, filename: str) -> None:
        pass


@dataclass
class Section:

    def __init__(self, title: str, level: int, content: str):
        self.title = title
        self.level = level
        self.content = content
        self.children: List["Section"] = []

    def get_full_content(self):
        return self.title.strip() + "\n\n" + self.content.strip()


class Markdown:

    def parse(self, filename: str) -> list[Section]:
        # read file
        xtns = filename.split('.')[-1]
        if xtns != "md":
            raise ExtensionError(f"file as extension .{xtns}; must be '.md'")
        try:
            with open(filename) as f:
                txt = f.read()
        except OSError as e:
            print(e, file=sys.stderr)
            return []
        lines = txt.splitlines()

        # sections is a list of (section_level, line number)
        sections: List[Tuple[int, int]] = []
        in_block = False
        for i, line in enumerate(lines):
            if line.startswith("```"):
                in_block = not in_block
            if not in_block and line.strip().startswith("#"):
                level = len(line.strip().split()[0])
                if level in range(1, 7):
                    sections.append((level, i))
        if not sections:
            return [Section("", 0, txt)]

        # if text doesn't start with a section, chunk initial text
        text_sects: List[str] = []
        if sections[0][1]:
            text_sects.append('\n'.join(lines[:sections[0][1]]))
        # get text
        for i, section in enumerate(sections):
            start = section[1]
            try:
                end = sections[i + 1][1]
                text_sects.append('\n'.join(lines[start:end]))
            except IndexError:
                text_sects.append('\n'.join(lines[start:]))

        # create Section classes
        sec_list: List[Section] = []
        s = 0
        first: str | None = None
        if not text_sects[0].startswith('#'):
            s = 1
            first = text_sects[0]
        for sec in text_sects[s:]:
            title = sec.strip().splitlines()[0].lstrip('#').strip()
            try:
                content = sec.split("\n", 1)[1]
            except IndexError:
                content = '\n'
            level = sec.strip().splitlines()[0].count('#')
            sec_list.append(Section(title, level, content))

        # define children (immediate lower level)
        for i, sctn in enumerate(sec_list):
            j = i + 1
            try:
                while sec_list[j] and sec_list[j].level > sctn.level:
                    if sec_list[j].level == sctn.level + 1:
                        sctn.children.append(sec_list[j])
                    j += 1
            except IndexError:
                break
        if first:
            sec_list.insert(0, Section("", 0, first))
        return sec_list


class CodeBlock:

    def __init__(self, content: str) -> None:
        self.content = content
        self.logic_blocks = content.split("\n\n")


class Python:

    def parse(self, filename: str) -> List[CodeBlock]:

        # read file
        xtns = filename.split('.')[-1]
        if xtns != "py":
            raise ExtensionError(f"file as extension .{xtns}; must be '.py'")
        try:
            with open(filename) as f:
                txt = f.read()
        except OSError as e:
            print(e, file=sys.stderr)
            return []

        # divide by logic blocks
        logic_blocks = txt.split("\n\n\n")
        code_blocks: List[CodeBlock] = []
        for block in logic_blocks:
            code_block = CodeBlock(block)
            code_blocks.append(code_block)
        return code_blocks


class Chunker:
    chunks: List[Chunk] = []

    def markdown(self, filename: str) -> None:
        # read file
        try:
            with open(filename) as f:
                txt = f.read()
        except OSError as e:
            print(e, file=sys.stderr)
            return
        if not self.chunks:
            chunk_id = 0
        else:
            chunk_id = self.chunks[-1].id + 1

        # chunk all if length is lower than limit
        if len(txt) <= 2000:
            new_chunk = Chunk(chunk_id, filename, txt)
            self.chunks.append(new_chunk)
            return

        # chunk by sections
        md = Markdown()
        sections = md.parse(filename)
        lengths = [len(s.get_full_content().strip()) for s in sections]
        for i, l in enumerate(lengths):
            if l <= 2000:
                chunk = Chunk(
                    len(self.chunks),
                    filename,
                    sections[i].get_full_content().strip()
                )
                self.chunks.append(chunk)
                continue

            # chunk by paragraphs
            paragraphs = sections[i].content.strip().split("\n\n")
            for par in paragraphs:
                if len(par) <= 2000:
                    chunk = Chunk(
                        len(self.chunks),
                        filename,
                        par.strip()
                    )
                    self.chunks.append(chunk)
                    continue

                # chunk by sentences
                sentences = [s.strip() for s in par.split('.')]
                for s in sentences:
                    if len(s) <= 2000:
                        chunk = Chunk(
                            len(self.chunks),
                            filename,
                            s.strip()
                        )
                        self.chunks.append(chunk)
                        continue

                    # chunk by words
                    words = [w for w in s.split(' ')]
                    for w in words:
                        chunk = Chunk(
                            len(self.chunks),
                            filename,
                            w.strip()
                        )
                        self.chunks.append(chunk)
                        continue

    def python(self, filename: str) -> None:
        # read file
        try:
            with open(filename) as f:
                txt = f.read()
        except OSError as e:
            print(e, file=sys.stderr)
            return
        if not self.chunks:
            chunk_id = 0
        else:
            chunk_id = self.chunks[-1].id + 1
        if len(txt) <= 2000:
            self.chunks.append(Chunk(chunk_id, filename, txt))
            return

        # chunk by blocks (imports, classes, functions, ...)
        py = Python()
        blocks = py.parse(filename)
        lengths = [len(b.content.strip()) for b in blocks]
        for i, l in enumerate(lengths):
            if l <= 2000:
                chunk = Chunk(
                    len(self.chunks),
                    filename,
                    blocks[i].content
                )
                self.chunks.append(chunk)
                continue

            # chunk by logic blocks
            for block in blocks[i].logic_blocks:
                if len(block) <= 2000:
                    chunk = Chunk(
                        len(self.chunks),
                        filename,
                        block
                    )
                    self.chunks.append(chunk)
                    continue

                # chunk by statements
                for line in block.splitlines():
                    if not line.strip():
                        continue
                    chunk = Chunk(
                        len(self.chunks),
                        filename,
                        line
                    )
                    self.chunks.append(chunk)


if __name__ == "__main__":
    chunker = Chunker()
    chunker.markdown("/home/alcristo/cursus/mst3/Fly-in/README.md")
    i = 0
    for chunk in chunker.chunks:
        print(f"\nMarkdown Chunk {i}\n")
        print(chunk.content)
        i += 1
    chunker.python("src/index.py")
    for chunk in chunker.chunks[i:]:
        print(f"\nPython Chunk {i}\n")
        print(chunk.content)
        i += 1
