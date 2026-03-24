.PHONY: run test build install

install:
	pip install -r requirements.txt

test:
	python -m pytest tests/ -v

run:
	python app/app.py

build:
	docker build -t self-healing-cicd .
