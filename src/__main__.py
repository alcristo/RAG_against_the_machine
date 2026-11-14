from chunking import get_py_md_files, get_file_metadata, chunk_files, chunk_one_file
from indexing import build_index, update_index
from retrieval import BM25
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

    # read the files
    files = get_py_md_files("data/raw/vllm-0.10.1")
    try:
        file_metadata = get_file_metadata(files)
    except OSError as e:
        print(e, file=sys.stderr)
        return

    if old_metadata and old_metadata["chunk_size"] != max_chunk_size:
        # if chunk size has changed, re-index everythng
        pass

    elif old_metadata:
        # if old metadata exists, check for changes in the file dataset
        changes: List[str] = []
        additions: List[str] = []
        deletions: List[str] = []

        # get deleted files
        for key in old_metadata["files"].keys():
            if key not in files:
                deletions.append(key)

        for fn in files:
            # get new files
            if not old_metadata["files"].get(fn):
                additions.append(fn)
                continue
            old_hash = old_metadata["files"][fn]["hash"]
            new_hash = file_metadata[fn]["hash"]

            # get changed files
            if old_hash != new_hash:
                changes.append(fn)

        if all((not changes, not additions, not deletions)):
            # if no additions, deletions or changes, no need to re-index
            print("no changes were detected")
            return

        print(
            "file dataset has changed: "
            f"{len(changes)} modified files, "
            f"{len(additions)} additions, "
            f"{len(deletions)} deletions"
        )
        print(f"Additions: {additions}")
        print(f"Changes: {changes}")
        print(f"Deletions: {deletions}")

        # load structures
        with open("data/processed/index.json") as f:
            old_index: Dict[str, Dict[str, Any]] = json.load(f)
        with open("data/processed/chunks.json") as f:
            old_chunks: Dict[str, Dict[str, Any]] = json.load(f)
        with open("data/processed/document_length.json") as f:
            old_lengths = json.load(f)
        index_copy = old_index.copy()

        # delete files from structures
        for fn in deletions:
            file_chunks = old_metadata["files"][fn]["chunks"]
            old_metadata["files"].pop(fn)
            for c in file_chunks:
                try:
                    old_chunks.pop(str(c))
                except KeyError:
                    pass
                try:
                    old_lengths.pop(str(c))
                except KeyError:
                    pass
                for k, v in index_copy.items():
                    try:
                        v.pop(str(c))
                        if not v:
                            old_index.pop(k)
                    except KeyError:
                        pass

        # re-index changed files
        for fn in changes:
            chunk_ids = [int(k) for k in old_chunks.keys()]
            nxt_id = max(chunk_ids) + 1
            file_chunks = old_metadata["files"][fn]["chunks"]

            # delete the files with their chunks
            for c in file_chunks:
                try:
                    old_chunks.pop(str(c))
                except KeyError:
                    pass
                try:
                    old_lengths.pop(str(c))
                except KeyError:
                    pass
                for k, v in index_copy.items():
                    try:
                        v.pop(str(c))
                        if not v:
                            old_index.pop(k)
                    except KeyError:
                        pass

            # re-insert the files with new chunks
            new_chunks = chunk_one_file(fn, nxt_id, max_chunk_size)
            try:
                file_metadata = get_file_metadata([fn])
            except OSError as e:
                print(e, file=sys.stderr)
                return
            print(file_metadata)
            old_metadata["files"].update({fn: file_metadata[fn]})
            chunk_ids = [chunk.id for chunk in new_chunks]
            print(chunk_ids)
            old_metadata["files"][fn]["chunks"] = chunk_ids
            chunk_dict: Dict[int, Dict[str, Any]] = {}
            for ch in new_chunks:
                ch.dump(chunk_dict)
            for c, v in chunk_dict.items():
                old_chunks.update({str(c): v})
            update_index(old_index, old_lengths, new_chunks)

        # index new files
        for fn in additions:
            print(f"Adding {fn}")
            chunk_ids = [int(k) for k in old_chunks.keys()]
            nxt_id = max(chunk_ids) + 1
            print(f"chunking {fn}")
            new_chunks = chunk_one_file(fn, nxt_id, max_chunk_size)
            chunk_ids = [chunk.id for chunk in new_chunks]
            print(f"assigning chunk ids to metadata")
            try:
                file_metadata = get_file_metadata([fn])
            except OSError as e:
                print(e, file=sys.stderr)
                return
            print(file_metadata)
            old_metadata["files"].update({fn: file_metadata[fn]})
            old_metadata["files"][fn]["chunks"] = chunk_ids
            chunk_dict = {}
            for ch in new_chunks:
                ch.dump(chunk_dict)
            for c, v in chunk_dict.items():
                old_chunks.update({str(c): v})
            print(f"indexing {fn}")
            update_index(old_index, old_lengths, new_chunks)

        # save new data structures
        try:
            with open("data/processed/chunks.json", "w") as f:
                json.dump(old_chunks, f, indent=2)
            with open("data/processed/index.json", "w") as f:
                json.dump(old_index, f, indent=2)
            with open("data/processed/document_length.json", "w") as f:
                json.dump(old_lengths, f, indent=2)
            """full_metadata: Dict[str, Any] = {
                "chunk_size": max_chunk_size, "files": file_metadata
            }"""
            with open("data/processed/metadata.json", "w") as f:
                json.dump(old_metadata, f, indent=2)
        except (OSError, json.JSONDecodeError) as e:
            os.chmod("data/processed/chunks.json", 700)
            os.remove("data/processed/chunks.json")
            os.chmod("data/processed/index.json", 700)
            os.remove("data/processed/index.json")
            os.chmod("data/processed/document_length.json", 700)
            os.remove("data/processed/document_length.json")
            os.chmod("data/processed/metadata.json", 700)
            os.remove("data/processed/metadata.json")
            print(e, file=sys.stderr)
            return
        return

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
        chunk_dict = {}
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
        os.chmod("data/processed/chunks.json", 700)
        os.remove("data/processed/chunks.json")
        os.chmod("data/processed/index.json", 700)
        os.remove("data/processed/index.json")
        os.chmod("data/processed/document_length.json", 700)
        os.remove("data/processed/document_length.json")
        os.chmod("data/processed/metadata.json", 700)
        os.remove("data/processed/metadata.json")
        print(e, file=sys.stderr)
        return


def search(query: str, k: int = 5):
    try:
        current_file = "data/processed/chunks.json"
        with open(current_file) as f:
            chunks = json.load(f)
        current_file = "data/processed/document_length.json"
        with open(current_file) as f:
            dls = json.load(f)
        current_file = "data/processed/index.json"
        with open(current_file) as f:
            index = json.load(f)
    except OSError as e:
        print(e, file=sys.stderr)
        return
    google = BM25(chunks, index, dls)
    scores = google.sorted_scores(query, k)
    for key, _ in scores.items():
        print(f"{key}: {chunks[str(key)]['file']}")
        print(f"Start index: {chunks[str(key)]['start_index']}")
        print(f"End index: {chunks[str(key)]['end_index']}")
        print()


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
