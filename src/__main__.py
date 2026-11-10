from tqdm import tqdm
from chunking import get_all_files, get_important_files, Chunk, recursive_text_split, recursive_py_split
import time


def chunk_statistics(chunks: Chunk):
    sizes = [len(chunk.content) for chunk in chunks]

    if not sizes:
        return

    print(f"Total chunks: {len(sizes)}")
    print(f"Average size: {sum(sizes) / len(sizes):.2f}")
    print(f"Minimum size: {min(sizes)}")
    print(f"Maximum size: {max(sizes)}")

    for threshold in [100, 250, 500, 1000, 1500, 2000]:
        count = sum(size <= threshold for size in sizes)
        percentage = count / len(sizes) * 100

        print(
            f"Chunks <= {threshold}: "
            f"{count} ({percentage:.1f}%)"
        )


def main():
    files = get_important_files(get_all_files("data/raw/vllm-0.10.1"))
    t0 = time.time()
    # chunker = Chunker()
    bar = tqdm(
        range(len(files)),
        desc="Chunking files",
        unit="files"
    )
    chunks: list[Chunk] = []
    chunk_id = 0
    for i in bar:
        with open(files[i]) as f:
            txt = f.read()
        if files[i].split('.')[-1] == "py":
            contents = recursive_py_split(txt)
            for c in contents:
                if not c.strip():
                    continue
                if len(c) > 2000:
                    raise AttributeError(
                        f"Chunking error in {files[i]}:\n\n"
                        f"{c}"
                    )
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    doc_id=files[i],
                    content=c,
                    start_index=sum([len(t) for t in contents[:i]]),
                    end_index=sum([len(t) for t in contents[:i]]) + len(c)
                ))
                chunk_id += 1
        else:
            contents = recursive_text_split(txt)
            for c in contents:
                if not c.strip():
                    continue
                if len(c) > 2000:
                    raise AttributeError(
                        f"Chunking error in {files[i]}:\n\n"
                        f"{c}"
                    )
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    doc_id=files[i],
                    content=c,
                    start_index=sum([len(t) for t in contents[:i]]),
                    end_index=sum([len(t) for t in contents[:i]]) + len(c)
                ))
                chunk_id += 1
    dt = time.time() - t0
    print(f"Chunking finished in {round(dt, 3)}s")
    print(f"Divided {len(files)} files in {len(chunks)} chunks")
    # chunk_statistics(chunks)


if __name__ == "__main__":
    main()
