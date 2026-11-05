from typing import List, Tuple, Dict, Any, Protocol
from dataclasses import dataclass
import sys
import os


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
        return self.title + '\n' + self.content.strip()


class Markdown:
    def parse(self, filename: str) -> list[Section]:
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
            content = sec.split("\n", 1)[1]
            level = sec.strip().splitlines()[0].count('#')
            sec_list.append(Section(title, level, content))

        # define children (immediate lower level)
        for i, sctn in enumerate(sec_list):
            j = i + 1
            while sec_list[j] and sec_list[j].level > sctn.level:
                if sec_list[j].level == sctn.level + 1:
                    sctn.children.append(sec_list[j])
                j += 1
        if first:
            sec_list.insert(0, Section("", 0, first))
        return sec_list


class Chunker:
    chunks: List[Chunk] = []

    def markdown(self, filename: str) -> None:
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
            new_chunk = Chunk(chunk_id, filename, txt)
            self.chunks.append(new_chunk)
            return

    def python(self, filename: str) -> None:
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


def get_all_files(dir: str) -> List[str]:
    """Return list of all files in this directory and subdirecctories"""
    all_files: List[str] = []
    for root, _, files in os.walk(dir):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


def get_extensions(files: List[str]) -> Dict[str, int]:
    """Return dictionary with number of extensions or hidden files"""
    exts: Dict[str, int] = {}
    for f in files:
        extension = f.split(".")[-1]
        if extension.find("/") >= 0:
            continue
        if not exts.get(extension):
            exts[extension] = 0
        exts[extension] += 1
    return exts


def get_important_files(files: List[str]) -> List[str]:
    """Return list of Python and Markdown file names"""
    important: List[str] = []
    for f in files:
        extension = f.split('.')[-1]
        if extension in ("md", "py"):
            important.append(f)
    return important


if __name__ == "__main__":
    rag_files = get_all_files("data/raw/vllm-0.10.1/")
    d = get_extensions(rag_files)
    for key, value in d.items():
        print(f"{key}: {value}")
    imp_files = get_important_files(rag_files)
    for file in imp_files:
        print(file)
    print(len(imp_files))
