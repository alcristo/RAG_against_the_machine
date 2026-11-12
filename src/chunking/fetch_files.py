from typing import List, Dict, Any
from hashlib import sha256
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


def get_py_md_files(dir: str) -> List[str]:
    """Return list of Python and Markdown file names from directory"""
    all_files: List[str] = []
    for root, _, files in os.walk(dir):
        for file in files:
            all_files.append(os.path.join(root, file))
    important: List[str] = []
    for f in all_files:
        extension = f.split('.')[-1]
        if extension in ("md", "py"):
            important.append(f)
    return important


def get_file_metadata(files: List[str]) -> Dict[str, Any]:
    """Return file content hash dictionary from file name list"""
    file_metadata: Dict[str, Any] = {}
    for file in files:
        with open(file, "rb") as f:
            file_hash = sha256(f.read()).hexdigest()
        file_metadata.update({file: {"hash": file_hash, "chunks": []}})
    return file_metadata
