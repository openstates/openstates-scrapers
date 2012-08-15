all: clean build

clean:
	rm -f templates.js index.json

build:
	python js.py > templates.js
	python build_index.py
