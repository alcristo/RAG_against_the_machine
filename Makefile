ARGS ?=

SOURCES = src

PYTHON = python3

CACHE = __pycache__ */__pycache__ .mypy_cache */.mypy_cache

PDB = PDB

RM = rm -rf

LINT = --group lint

export UV_CACHE_DIR=/home/$(USER)/goinfre/rag-cache
export UV_PROJECT_ENVIRONMENT=/home/$(USER)/goinfre/rag-venv
export HF_HOME=/sgoinfre/students/$(USER)/HF

install:
	@rm -f .venv
	@mkdir -p .venv
	@if [ ! -L .venv ]; then $(RM) .venv && ln -s $(UV_PROJECT_ENVIRONMENT) .venv; fi
	uv sync

help:
	@echo "make sync                                                                     - Install the dependencies"
	@echo "make index -max_chunk_size <int>                                              - Ingest data/raw/ and build the index under data/processed"
	@echo "make search <query> -k <int>                                                  - Return the top-k sources for a single query"
	@echo "make search_dataset -dataset_path <path> -k <int> -save_directory <dir>       - Run search over a whole dataset and write a StudentSearchResults JSON file"
	@echo "make answer  <query> -k <int>                                                 - Answer a single query using the retrieved context"
	@echo "make answer_dataset -student_search_results_path <path> -save_directory <dir> - Generate answers for a dataset, producing a StudentSearchResultsAndAnswer JSON file"
	@echo "make evaluate -student_search_results_path <path> -dataset_path <path>        - Report your own recall@k against a ground-truth dataset, for your own testing"
	@echo "make run                                                                      - Run any of the former commands"
	@echo "make debug                                                                    - Debug with PDB"
	@echo "make clean                                                                    - Remove cache"
	@echo "make fclean                                                                   - Remove cache and data/processed"
	@echo "make lint                                                                     - Check type hints"
	@echo "make lint-strict                                                              - Check strict type hints"

index: install
	uv run $(PYTHON) -m $(SOURCES) index $(ARGS)

search: install
	uv run $(PYTHON) -m $(SOURCES) search $(ARGS)

search_dataset: install
	uv run $(PYTHON) -m $(SOURCES) search_dataset $(ARGS)

answer: install
	uv run $(PYTHON) -m $(SOURCES) answer $(ARGS)

answer_dataset: install
	uv run $(PYTHON) -m $(SOURCES) answer_dataset $(ARGS)

evaluate: install
	uv run $(PYTHON) -m $(SOURCES) evaluate $(ARGS)

run: install
	uv run $(PYTHON) -m $(SOURCES) $(ARGS)

debug: install
	uv run $(PYTHON) -m $(PDB) $(SOURCES)

clean:
	@find . -path "*__pycache__" -exec rm -rf {} \;
	@find . -path ".mypy_cache" -exec rm -rf {} \;

lint: install
	uv run $(LINT) flake8 $(SOURCES)
	uv run $(LINT) mypy $(SOURCES) --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict: install
	uv run $(LINT) flake8 $(SOURCES)
	uv run $(LINT) mypy $(SOURCES) --strict

.PHONY: install index search search_dataset answer answer_dataset evaluate run debug clean lint lint-strict