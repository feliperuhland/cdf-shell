.PHONY: run test lint build build-constraints

run:
	uv run python -m cdf

test:
	PYTHONDONTWRITEBYTECODE=1 uv run pytest

lint:
	uv run ruff check .

# Build with the hash-pinned backend from build-constraints.txt (same as CI).
build:
	uv build --build-constraints build-constraints.txt --require-hashes

# Re-lock build-constraints.txt after changing build-constraints.in.
build-constraints:
	uv pip compile build-constraints.in --generate-hashes --universal \
		--python-version 3.11 --no-header -o build-constraints.txt
