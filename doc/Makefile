all: architecture.pdf editor.pdf

architecture.pdf: architecture.dot FORCE
	dot architecture.dot -T pdf -o architecture.pdf
	dot architecture.dot -T png -o architecture.png

editor.pdf: editor.dot FORCE
	dot editor.dot -T pdf -o editor.pdf
	dot editor.dot -T png -o editor.png

node_modules/.bin/jsdoc:
	npm install jsdoc
jsdoc: node_modules/.bin/jsdoc FORCE
	node_modules/.bin/jsdoc -d jsdoc ../src/editor/static/

FORCE:
