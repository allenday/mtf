.PHONY: check
check:
	PYTHONPATH=src poetry run pylint src/ tests/
	poetry run mypy src/ tests/
	PYTHONPATH=src poetry run pytest --cov=mtf --cov-report=term-missing
	pre-commit run --all-files
