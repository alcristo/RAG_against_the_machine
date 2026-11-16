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

run: install
	uv run $(PYTHON) -m $(SOURCES) $(ARGS)

debug: install
	uv run $(PYTHON) -m $(PDB) $(SOURCES)

clean:
	@$(RM) $(CACHE)

lint: install
	uv run $(LINT) flake8 $(SOURCES)
	uv run $(LINT) mypy $(SOURCES) --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict: install
	uv run $(LINT) flake8 $(SOURCES)
	uv run $(LINT) mypy $(SOURCES) --strict

.PHONY: install run debug clean lint lint-strict