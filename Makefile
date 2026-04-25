test:
	coverage erase
	mypy ibflex tests
	ruff check ibflex tests
	pytest --cov=ibflex --cov-report=term --cov-fail-under=85 tests/

lint:
	ruff check ibflex tests

format:
	ruff format ibflex tests

clean:
	find . -regex '.*\.pyc' -exec rm {} \;
	find . -regex '.*~' -exec rm {} \;
	rm -rf MANIFEST dist build *.egg-info .coverage .mypy_cache .ruff_cache .pytest_cache

install:
	pip install -e .[web,dev]

uninstall:
	pip uninstall -y ibflex2

.PHONY:	test lint format clean install uninstall
