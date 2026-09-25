.PHONY: run test lint

run:
	uv run python -m cdf

test:
	PYTHONDONTWRITEBYTECODE=1 uv run pytest

lint:
	uv run ruff check .
