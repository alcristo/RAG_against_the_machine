from chunking import get_all_files, get_important_files, chunk_files
from indexing import build_index
import time
import json
import os


def main():
    try:
        files = get_important_files(get_all_files("data/raw/vllm-0.10.1"))
        t0 = time.time()
        chunks = chunk_files(files)
        dt = time.time() - t0
    except OSError as e:
        print(e)
        return
    print(f"Chunking finished in {round(dt, 3)}s")
    print(f"Divided {len(files)} files in {len(chunks)} chunks")
    t0 = time.time()
    index, doc_l = build_index(chunks)
    dt = time.time() - t0
    print(f"Indexed {len(chunks)} chunks in {round(dt, 3)}s")
    try:
        os.makedirs("data/storage", exist_ok=True)
        with open("data/storage/index.json", "w") as f:
            json.dump(index, f, indent=2)
        with open("data/storage/document_length.json", "w") as f:
            json.dump(doc_l, f, indent=2)
    except (OSError, json.JSONDecodeError) as e:
        print(e)
        return


if __name__ == "__main__":
    main()
