from chunking import get_py_md_files, get_file_metadata, chunk_files, chunk_one_file
from indexing import build_index
import fire
from fire.core import FireExit
from typing import Any, Dict, List
import time
import json
import sys
import os


def index(max_chunk_size: int = 2000):
    if max_chunk_size < 500:
        print("max chunk size can't be lower than 500", file=sys.stderr)
        return
    if max_chunk_size > 2000:
        print("max chunk size can't be greater than 2000", file=sys.stderr)
        return

    # load former configuration metadata
    old_metadata: Dict[str, Any] = {}
    try:
        with open("data/processed/metadata.json") as f:
            old_metadata = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    except OSError as e:
        print(e, file=sys.stderr)
        return

    files = get_py_md_files("data/raw/vllm-0.10.1")
    try:
        file_metadata = get_file_metadata(files)
    except OSError as e:
        print(e, file=sys.stderr)
        return
    if old_metadata and old_metadata["chunk_size"] != max_chunk_size:
        pass
    elif old_metadata:
        changes: List[str] = []
        additions: List[str] = []
        deletions: List[str] = []
        for key in old_metadata["files"].keys():
            if key not in files:
                deletions.append(key)
        for fn in files:
            if not old_metadata["files"].get(fn):
                additions.append(fn)
                continue
            old_hash = old_metadata["files"][fn]["hash"]
            new_hash = file_metadata[fn]["hash"]
            if old_hash != new_hash:
                changes.append(fn)
        if all((not changes, not additions, not deletions)):
            return
        
        # for fn in deletions:

    # chunk files
    try:
        t0 = time.time()
        chunks = chunk_files(files, max_chunk_size)
        dt = time.time() - t0
    except OSError as e:
        print(e, file=sys.stderr)
        return
    print(f"Chunking finished in {round(dt, 3)}s")
    print(f"Divided {len(files)} files in {len(chunks)} chunks")

    # save chunks metadata
    for c in chunks:
        filename = c.document
        file_metadata[filename]["chunks"].append(c.id)

    # index chunks
    t0 = time.time()
    index, doc_l = build_index(chunks)
    dt = time.time() - t0
    print(f"Indexed {len(chunks)} chunks in {round(dt, 3)}s")

    # save index and configuration files
    try:
        chunk_dict: Dict[int, Dict[str, Any]] = {}
        for c in chunks:
            c.dump(chunk_dict)
        os.makedirs("data/processed", exist_ok=True)
        with open("data/processed/chunks.json", "w") as f:
            json.dump(chunk_dict, f, indent=2)
        with open("data/processed/index.json", "w") as f:
            json.dump(index, f, indent=2)
        with open("data/processed/document_length.json", "w") as f:
            json.dump(doc_l, f, indent=2)
        full_metadata = {"chunk_size": max_chunk_size, "files": file_metadata}
        if not old_metadata:
            with open("data/processed/metadata.json", "w") as f:
                json.dump(full_metadata, f, indent=2)
    except (OSError, json.JSONDecodeError) as e:
        os.remove("data/processed/chunks.json")
        os.remove("data/processed/index.json")
        os.remove("data/processed/document_length.json")
        os.remove("data/processed/metadata.json")
        print(e, file=sys.stderr)
        return


def search(query: str, k: int = 5):
    pass


def search_dataset(
    dataset_path: str,
    k: int = 5,
    save_directory: str = "data/processed/StudentSearchResults.json"
):
    pass


def answer(query: str, k: int = 5):
    pass


def answer_dataset(
    student_search_results_path: str,
    k: int = 5,
    save_directory: str = "data/processed/StudentSearchResultsAndAnswer.json"
):
    pass


def evaluate(dataset_path: str, student_search_results_path: str):
    pass


COMMANDS = (
    "index",
    "search",
    "search_dataset",
    "answer",
    "answer_dataset",
    "evaluate"
)


if __name__ == "__main__":
    try:
        fire.Fire()
    except KeyboardInterrupt:
        pass
    except FireExit:
        pass
    except BaseException as e:
        print(f"Caught {e.__class__.__name__}: {e.__str__()}", file=sys.stderr)
