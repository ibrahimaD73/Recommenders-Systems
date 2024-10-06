install:
	pip install --upgrade pip &&\
		pip install -r requirements.txt

test:
	python -m pytest tests/

format:
	black *.py

lint:
	pylint --disable=R,C app.py

run:
	python app.py

deploy:
	gcloud app deploy

all: install format lint test run