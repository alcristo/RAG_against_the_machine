from typing import List, Dict
import os


def get_all_files(dir: str) -> List[str]:
    """Return list of all files in this directory and subdirectories"""
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
