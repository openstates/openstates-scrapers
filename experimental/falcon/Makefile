all: clean build

build:
	if [ -d build ]; then rm -rvf build; fi
	cp -r static build
	cp -r csv build
	#./bin/geneate-csv ./resources/states.json
	./bin/static-build ./resources/states.json falcon.html > build/index.html

clean:
	rm -rvf build
