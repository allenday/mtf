.PHONY: format
format:
	pre-commit run black --all-files
	pre-commit run isort --all-files

.PHONY: check
check: format
	PYTHONPATH=src poetry run pylint src/ tests/
	poetry run mypy src/ tests/
	PYTHONPATH=src poetry run pytest --cov=mtf --cov-report=term-missing
	pre-commit run --all-files

.PHONY: commit
commit: check
ifndef COMMIT_MSG
	$(error COMMIT_MSG is not set. Please run again as 'COMMIT_MSG="your message" make commit')
endif
	@# Check if we're on main branch
	@if [ "$$(git rev-parse --abbrev-ref HEAD)" = "main" ]; then \
		echo "ERROR: Cannot commit directly to main branch"; \
		exit 1; \
	fi
	@# Check branch naming convention
	@BRANCH_NAME="$$(git rev-parse --abbrev-ref HEAD)"; \
	if ! echo "$$BRANCH_NAME" | grep -qE "^(feature|bugfix|hotfix|docs|chore|test|refactor|style|perf|ci|deps|security)/"; then \
		echo "ERROR: Branch name must start with one of: feature/, bugfix/, hotfix/, docs/, chore/, test/, refactor/, style/, perf/, ci/, deps/, security/"; \
		echo "Your branch name is: $$BRANCH_NAME"; \
		exit 1; \
	fi; \
	if echo "$$BRANCH_NAME" | grep -q "[A-Z]"; then \
		echo "ERROR: Branch name should not contain uppercase letters"; \
		echo "Your branch name is: $$BRANCH_NAME"; \
		exit 1; \
	fi; \
	if echo "$$BRANCH_NAME" | grep -q "[[:space:]]"; then \
		echo "ERROR: Branch name should not contain spaces"; \
		echo "Your branch name is: $$BRANCH_NAME"; \
		exit 1; \
	fi
	@# Run all checks
	@$(MAKE) check
	@# If we get here, all checks passed - do the commit
	git add .
	git commit -m "$(COMMIT_MSG)"

