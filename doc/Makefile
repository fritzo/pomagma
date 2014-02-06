all: architecture.pdf editor.pdf

architecture.pdf: architecture.dot FORCE
	dot architecture.dot -T pdf -o architecture.pdf
	dot architecture.dot -T png -o architecture.png

editor.pdf: editor.dot FORCE
	dot editor.dot -T pdf -o editor.pdf
	dot editor.dot -T png -o editor.png

FORCE:
