install:
	pip install -r requirements.txt

test:
	pytest

run:
	python main.py

freeze:
	pip freeze > requirements.txt

clean:
	rm -rf __pycache__