from tqdm import tqdm
from chunking import get_all_files, get_important_files, Chunker
import time


def main():
    files = get_important_files(get_all_files("data/raw/vllm-0.10.1"))
    t0 = time.time()
    chunker = Chunker()
    bar = tqdm(
        range(len(files)),
        desc="Chunking files",
        unit="files"
    )
    for i in bar:
        f = files[i]
        if f.split('.')[-1] == "py":
            chunker.python(f)
        else:
            chunker.markdown(f)
    dt = time.time() - t0
    print(f"Chunking finished in {round(dt, 3)}s")
    print(f"Divided {len(files)} files in {len(chunker.chunks)} chunks")


if __name__ == "__main__":
    main()
