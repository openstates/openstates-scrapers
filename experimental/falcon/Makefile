all: clean build

build:
	if [ -d build ]; then rm -rvf build; fi
	cp -r static build
	if [ ! -d csv ]; then \
		mkdir csv; \
		./bin/geneate-csv ./resources/states.json; \
	else \
		echo "Skipping CSV generation"; \
	fi
	./bin/static-build ./resources/states.json falcon.html > build/index.html
	cp -r csv build

clean:
	rm -rvf build
