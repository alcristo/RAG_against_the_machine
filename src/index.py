from typing import List
import os


def get_all_files(dir: str) -> List[str]:
    """Return list of all files in this directory and subdirecctories"""
    all_files: List[str] = []
    for root, _, files in os.walk(dir):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


def get_extensions(files: List[str]) -> dict[str, int]:
    """Return dictionary with number of extensions or hidden files"""
    exts: dict[str, int] = {}
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
