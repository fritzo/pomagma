all: architecture.pdf

architecture.pdf: architecture.dot FORCE
	dot architecture.dot -T pdf -o architecture.pdf
	dot architecture.dot -T png -o architecture.png

FORCE:
