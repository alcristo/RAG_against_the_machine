from .chunking import (
    get_py_md_files,
    get_file_metadata,
    chunk_files,
    chunk_one_file,
    Chunk,
    Unit,
    get_python_units,
    get_markdown_units,
    assemble_chunks
)
from .indexing import build_index, update_index
from .retrieval import BM25, SemanticSearch
from .answer import load_model, generate_rag_answer
from .models import (
    MinimalSource,
    UnansweredQuestion,
    RagDataset,
    AnsweredQuestion,
    MinimalSearchResults,
    MinimalAnswer,
    StudentSearchResults,
    StudentSearchResultsAndAnswer
)
import numpy as np
from tqdm import tqdm
import fire
from fire.core import FireExit
from typing import Any, Dict, List, Tuple
import time
import json
import sys
import os


def index(max_chunk_size: int = 2000) -> None:
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

        # empty chunk list for semantic embeddings
        extra_chunks: List[Chunk] = []

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
            old_metadata["files"].update({fn: file_metadata[fn]})
            chunk_ids = [chunk.id for chunk in new_chunks]
            old_metadata["files"][fn]["chunks"] = chunk_ids
            chunk_dict: Dict[int, Dict[str, Any]] = {}
            for ch in new_chunks:
                ch.dump(chunk_dict)
            for c, v in chunk_dict.items():
                old_chunks.update({str(c): v})
            update_index(old_index, old_lengths, new_chunks)
            extra_chunks.extend(new_chunks)

        # index new files
        for fn in additions:
            chunk_ids = [int(k) for k in old_chunks.keys()]
            nxt_id = max(chunk_ids) + 1
            new_chunks = chunk_one_file(fn, nxt_id, max_chunk_size)
            chunk_ids = [chunk.id for chunk in new_chunks]
            try:
                file_metadata = get_file_metadata([fn])
            except OSError as e:
                print(e, file=sys.stderr)
                return
            old_metadata["files"].update({fn: file_metadata[fn]})
            old_metadata["files"][fn]["chunks"] = chunk_ids
            chunk_dict = {}
            for ch in new_chunks:
                ch.dump(chunk_dict)
            for c, v in chunk_dict.items():
                old_chunks.update({str(c): v})
            update_index(old_index, old_lengths, new_chunks)
            extra_chunks.extend(new_chunks)

        # re-generate semantic embeddings
        modifications = changes.copy()
        modifications.extend(additions)
        print("Generating new semantic embeddings...")
        t0 = time.time()
        old_sem = SemanticSearch()
        old_sem.load()
        new_sem = SemanticSearch(extra_chunks)
        new_sem.generate_embeddings()
        old_sem.embeddings = np.vstack((
            old_sem.embeddings, new_sem.embeddings
        ))
        dt = time.time() - t0
        if dt < 60:
            print(f"Embedded {len(old_chunks)} chunks in {dt:.3f}s")
        else:
            print(
                f"Embedded {len(old_chunks)} chunks in "
                f"{dt // 60}min {dt % 60:.3f}s"
            )

        # save new data structures
        try:
            with open("data/processed/chunks.json", "w") as f:
                json.dump(old_chunks, f, indent=2)
            with open("data/processed/index.json", "w") as f:
                json.dump(old_index, f, indent=2)
            with open("data/processed/document_length.json", "w") as f:
                json.dump(old_lengths, f, indent=2)
            old_sem.save()
            with open("data/processed/metadata.json", "w") as f:
                json.dump(old_metadata, f, indent=2)
        except (OSError, json.JSONDecodeError) as e:
            os.chmod("data/processed/chunks.json", 700)
            os.remove("data/processed/chunks.json")
            os.chmod("data/processed/index.json", 700)
            os.remove("data/processed/index.json")
            os.chmod("data/processed/document_length.json", 700)
            os.remove("data/processed/document_length.json")
            os.chmod("data/processed/embeddings.npy", 700)
            os.remove("data/processed/embeddings.npy")
            os.chmod("data/processed/metadata.json", 700)
            os.remove("data/processed/metadata.json")
            print(e, file=sys.stderr)
            return
        return

    # chunk files
    """try:
        t0 = time.time()
        chunks = chunk_files(files, max_chunk_size)
        dt = time.time() - t0
    except OSError as e:
        print(e, file=sys.stderr)
        return"""
    t0 = time.time()
    chunks: List[Chunk] = []
    try:
        for fn in tqdm(files, desc="Chunking files", unit="f"):
            with open(fn) as f:
                source = f.read()
            if fn.endswith(".py"):
                units = get_python_units(source)
            else:
                units = get_markdown_units(source)
            chunks.extend(assemble_chunks(
                source, fn, units, len(chunks), max_chunk_size
            ))
    except OSError as e:
        print(e)
        return
    dt = time.time() - t0
    if dt < 60:
        print(
            f"Took {dt:.3f}s "
            f"to divide {len(files)} files in {len(chunks)} chunks"
        )
    else:
        print(
            f"Took {dt // 60}min {dt % 60:.3f}s "
            f"to divide {len(files)} files in {len(chunks)} chunks"
        )

    # save chunks metadata
    for c in chunks:
        filename = c.document
        file_metadata[filename]["chunks"].append(c.id)

    # index chunks
    t0 = time.time()
    index, doc_l = build_index(chunks)
    dt = time.time() - t0
    if dt < 60:
        print(f"Indexed {len(chunks)} chunks in {dt:.3f}s")
    else:
        print(f"Indexed {len(chunks)} chunks in {dt // 60}min {dt % 60:.3f}s")

    # semantic embeddings
    print("Generating semantic embeddings...")
    t0 = time.time()
    sem = SemanticSearch(chunks)
    sem.generate_embeddings()
    dt = time.time() - t0
    if dt < 60:
        print(f"Embedded {len(chunks):.0f} chunks in {dt:.3f}s")
    else:
        print(
            f"Embedded {len(chunks)} chunks in "
            f"{dt // 60}min {dt % 60:.3f}s"
        )

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
        sem.save()
        full_metadata: Dict[str, Any] = {
            "chunk_size": max_chunk_size, "files": file_metadata
        }
        with open("data/processed/metadata.json", "w") as f:
            json.dump(full_metadata, f, indent=2)
    except (OSError, json.JSONDecodeError) as e:
        os.chmod("data/processed/chunks.json", 700)
        os.remove("data/processed/chunks.json")
        os.chmod("data/processed/index.json", 700)
        os.remove("data/processed/index.json")
        os.chmod("data/processed/document_length.json", 700)
        os.remove("data/processed/document_length.json")
        os.chmod("data/processed/embeddings.npy", 700)
        os.remove("data/processed/embeddings.npy")
        os.chmod("data/processed/metadata.json", 700)
        os.remove("data/processed/metadata.json")
        print(e, file=sys.stderr)
        return


def _rrf(
    lex_rank: List[int],
    sem_rank: List[int],
    w: float = 0.1,
    k: float = 60
) -> List[Tuple[float, int]]:
    if w < 0 or w > 1:
        raise ValueError(f"invalid weight: {w}; must be in [0,1]")
    scores: Dict[int, float] = {}
    for rank, chunk_id in enumerate(sem_rank):
        scores[chunk_id] = scores.get(chunk_id, 0) + w / (k + rank + 1)
    for rank, chunk_id in enumerate(lex_rank):
        scores[chunk_id] = scores.get(chunk_id, 0) + (1 - w) / (k + rank + 1)
    return sorted(
        [(score, chunk_id) for chunk_id, score in scores.items()],
        reverse=True
    )


def search(query: str, k: int = 5) -> MinimalSearchResults | None:
    if k <= 0 or k > 50:
        raise SystemExit(f"invalid k value: {k}; 0 < k ≤ 50")
    question = UnansweredQuestion(question=query)
    results = MinimalSearchResults(
        question_id=question.question_id,
        question=question.question,
        retrieved_sources=[]
    )
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
        raise SystemExit(e)
    lex_scorer = BM25(chunks, index, dls)
    lex_scores = lex_scorer.sorted_scores(question.question, k)
    sem_scorer = SemanticSearch()
    sem_scorer.load()
    sem_scores = sem_scorer.search(question.question)
    lex_ranks: List[int] = [x for x in lex_scores.keys()]
    sem_ranks: List[int] = [int(y["chunk"]) for y in sem_scores]
    hybrid_ranks = _rrf(lex_ranks, sem_ranks)[:k]
    for _, i in hybrid_ranks:
        source = MinimalSource(
            file_path=chunks[str(i)]['file'],
            first_character_index=chunks[str(i)]['start_index'],
            last_character_index=chunks[str(i)]['end_index']
        )
        results.retrieved_sources.append(source)
    return results


def search_dataset(
    dataset_path: str,
    k: int,
    save_directory: str
):
    if not 0 < k <= 50:
        print(f"invalid k value: {k}; 0 < k ≤ 50", file=sys.stderr)
        return
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
        with open(dataset_path) as f:
            rag_questions_list = json.load(f)["rag_questions"]
        rag_questions = [UnansweredQuestion(
            question_id=q["question_id"],
            question=q["question"]
        ) for q in rag_questions_list]
    except OSError as e:
        print(e, file=sys.stderr)
        return
    try:
        with open(save_directory, "a") as f:
            pass
    except FileNotFoundError:
        pass
    except PermissionError as e:
        print(e, file=sys.stderr)
        return
    lex_searcher = BM25(chunks, index, dls)
    sem_searcher = SemanticSearch()
    sem_searcher.load()
    results = StudentSearchResults(search_results=[], k=k)
    rag_dataset = RagDataset(rag_questions=rag_questions)
    for question in tqdm(
        rag_dataset.rag_questions,
        desc="Searching sources",
        unit="q"
    ):
        lex_scores = lex_searcher.sorted_scores(question.question)
        sem_scores = sem_searcher.search(question.question)
        lex_ranks = [x for x in lex_scores.keys()]
        sem_ranks = [int(y["chunk"]) for y in sem_scores]
        hybrid_ranks = _rrf(lex_ranks, sem_ranks)[:k]
        sources: List[MinimalSource] = []
        for _, i in hybrid_ranks:
            sources.append(MinimalSource(
                file_path=chunks[str(i)]['file'],
                first_character_index=chunks[str(i)]['start_index'],
                last_character_index=chunks[str(i)]['end_index']
            ))
        results.search_results.append(MinimalSearchResults(
            question_id=question.question_id,
            question=question.question,
            retrieved_sources=sources
        ))
    try:
        os.makedirs("/".join(save_directory.split('/')[:-1]), exist_ok=True)
        with open(save_directory, 'w') as f:
            f.write(results.model_dump_json(indent=2))
    except OSError as e:
        print(e)
        return


def answer(query: str, k: int = 5) -> MinimalAnswer:
    if not 0 < k <= 50:
        print(f"invalid k value: {k}; 0 < k ≤ 50", file=sys.stderr)
        return
    print("Searching sources...")
    t0 = time.time()
    sources = search(query, k)
    dt = time.time() - t0
    if dt < 60:
        print(f"Search finished in {dt:.3f}s")
    else:
        print(f"Search finished in {int(dt // 60)}min {dt % 60:.3f}s")
    print("Loading model...")
    model, tokenizer = load_model()
    print("Loaded model.")
    print("Generating answer...")
    t0 = time.time()
    answer = generate_rag_answer(sources, k, model, tokenizer)
    dt = time.time() - t0
    if dt < 60:
        print(f"Generation finished in {dt:.3f}s")
    else:
        print(f"Generation finished in {int(dt // 60)}min {dt % 60:.3f}s")
    return answer


def answer_dataset(
    student_search_results_path: str,
    save_directory: str
):
    try:
        with open(save_directory) as f:
            assert f.writable()
    except FileNotFoundError:
        pass
    except AssertionError:
        print(f"file {save_directory} is not writable", file=sys.stderr)
        return
    except OSError as e:
        print(e, file=sys.stderr)
        return
    try:
        with open(student_search_results_path) as f:
            results = StudentSearchResults.model_validate_json(f.read())
    except (OSError, json.JSONDecodeError) as e:
        print(e, file=sys.stderr)
        return
    k = results.k
    if not 0 < k <= 50:
        print(f"invalid k value: {k}; 0 < k ≤ 50", file=sys.stderr)
        return
    print("Loading model...")
    model, tokenizer = load_model()
    print("Loaded model.")
    answered_results: List[MinimalAnswer] = []
    """for r in tqdm(
        results.search_results,
        desc="Answering",
        unit="q"
    ):"""
    for r in tqdm(
        results.search_results,
        desc="Answering questions",
        unit="q"
    ):
        try:
            answer = generate_rag_answer(r, k, model, tokenizer)
            answered_results.append(answer)
        except BaseException as e:
            print(r.question)
            print(e)
            return
        # print(f"\n{answer.question}\n{answer.answer}\n\n")
    final_results = StudentSearchResultsAndAnswer(
        search_results=answered_results, k=k
    )
    try:
        os.makedirs("/".join(save_directory.split('/')[:-1]), exist_ok=True)
        with open(save_directory, 'w') as f:
            f.write(final_results.model_dump_json(indent=2))
    except OSError as e:
        print(e)
        return


def evaluate(dataset_path: str, student_search_results_path: str):
    pass


def main() -> None:
    fire.Fire({
        "index": index,
        "search": search,
        "search_dataset": search_dataset,
        "answer": answer,
        "answer_dataset": answer_dataset,
        "evaluate": evaluate
    })


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (SystemExit, OSError) as e:
        print(e, file=sys.stderr)
    except FireExit:
        pass
