.PHONY: install lint format test typecheck check clean

install:
	poetry install --sync

lint:
	ruff check src tests

format:
	ruff format src tests

typecheck:
	mypy src

pytest:
	pytest

check: lint typecheck pytest

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache var/tmp var/logs
