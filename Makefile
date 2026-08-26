.PHONY: dev test

dev:
	PYTHONPATH=src python -m prompt_eval_studio serve --reload

test:
	PYTHONPATH=src pytest
