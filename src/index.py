from typing import List
import os


def get_all_files(dir: str) -> List[str]:
    """Return list of all files in this directory and subdirecctories"""
    all_files: List[str] = []
    for root, _, files in os.walk(dir):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


"""if __name__ == "__main__":
    rag_files = get_all_files("data/raw/vllm-0.10.1/")
    for file in rag_files:
        print(file)"""
