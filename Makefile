.PHONY: test lint check clean

test:
	uv run pytest tests/ -v

lint:
	uv run python -m py_compile src/auto_notes/*.py

check: lint test

clean:
	rm -rf workspace/ notes/ .pytest_cache
