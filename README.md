*This project has been created as part of the 42 curriculum by alcristo*

# RAG against the machine

Retrival Augmented Generation in vLLM

## Description

In this project, a small LLM has to answer a set of questions. One can train an AI to do that, but once the information it knows has changed, the model is obsolete, and it will need to be trained again. Such process is expensive, so it would be inefficient to keep an AI updated. However, there is a better way to do that: the AI gets access to an information source, takes the sources and answers.

The method described above is called *Retrieval Augmented Generation*, and it's used to enhance the answers made by an LLM. This project will make a full RAG pipeline, from preparing the sources to generating an answer from such sources.

### System Architecture

### Chunking strategy

An LLM can't just open a file, read it and try to guess whether the answer is in the file or not. It must get the most relevant lines regarding the answer from a set of many files that contain many more lines.

In order to get these relevant lines, the files must be divided in chunks. Such chunks must not have more than a certain size. This project forbids the generation of chunks greater than 2000 characters.

The chunking strategy depends on the file format. This project implemented chunking strategies for Python code (`.py` files) and Markdown (`.md` files).

After chunking, the lexical index is built and the semantic embeddings are generated. Finally, the following files are saved:

- The chunks, containing the file name, a context and the start and end character indices.
- The document lengths, with the number of words contained by each chunk.
- The semantic embeddings, in a `.npy` file.
- The lexical index: a Python dictionary whose keys are the words, and whose values are dictionaries with chunks and coincidences.
- File metadata, with the chunk size and file hashes with their chunks. Useful for incremental indexing.

### Retrieval method

When a search query is introduced, both lexical and semantic search methods are used to fuse them and get the $k$ chunks with the highest retrieval rank fusion (RRF) score.

### Performance analysis

Minimal `recall@5` must be above 50% for Python code and 80% for Markdown. This project achieves 79.8% for Python code and 84% for Markdown.

### Design decisions

### Challenges faced

## Instructions

### Example usage

## Resources

### AI usage

AI was used to generate several iterations of the chunking algorithm code, which was revised by the author, who added comments and additional context. AI was also used for debugging.